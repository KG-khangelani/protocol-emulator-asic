# SPDX-License-Identifier: Apache-2.0
"""Audit complete per-variant proofs, allowing separately rerun negative controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/i2c"))
from run_store_local_proof import properties, inspect_control


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def sections(path):
    return {name: body.strip().splitlines() for name, body in
            re.findall(r"\[(\w+)\]\n(.*?)(?=\n\[|\Z)", path.read_text(), re.S)}


def audit(positive, controls, variant, positive_bytes):
    capacity = 128 if variant == "od128" else 255
    pos = json.loads(positive_bytes)
    original = ROOT / "evidence/E0035-general-i2c/sources/current" / variant / "m1_program_store.v"
    assert pos["sources"][variant] == digest(original)
    source = original.read_text()
    full = source.replace("endmodule", properties(capacity) + "endmodule")
    model_dir = positive / (variant + "-model")
    model = read(model_dir / "model.json")
    assert (model_dir / "store.v").read_text() == full
    assert digest(model_dir / "store.v") == model["instrumented_sha256"]
    assert digest(model_dir / "prepared.il") == model["lowered_sha256"]
    assert model["run"]["returncode"] == 0 and not model["run"]["timed_out"]
    module = read(model_dir / "prepared.json")["modules"]["m1_program_store"]
    actual_assertions = {name: cell for name, cell in module["cells"].items()
                         if cell["type"] == "$assert" or cell["type"] == "$check" and
                         cell["parameters"]["FLAVOR"] == "assert"}
    assert set(actual_assertions) == set(model["assertions"])
    assert len(actual_assertions) == 5 * capacity + 12
    # Check the partition metadata against the actual lowered cells and source.
    lines = full.splitlines()
    boundary = next(i + 1 for i, line in enumerate(lines) if line == "    f_past_valid <= 1'b1;")
    for name, cell in actual_assertions.items():
        location = cell["attributes"]["src"]
        match = re.search(r":(\d+)\.\d+-(\d+)\.\d+$", location)
        assert match, location
        first, last = map(int, match.groups())
        indices = sorted({int(n) for n in re.findall(r"\bword(\d+)\b", "\n".join(lines[first-1:last]))})
        assert model["assertions"][name] == {"scope": "read" if first < boundary else "state",
                                            "words": indices, "src": location}
    assert not any(c["type"] == "$assume" or c["type"] == "$check" and
                   c["parameters"]["FLAVOR"] == "assume" for c in module["cells"].values())
    assert not any("init" in module["netnames"][f"word{i}"]["attributes"] for i in range(capacity))
    tasks = [t for t in pos["tasks"] if t["variant"] == variant and t["name"] in ("state", "read", "cover")]
    checked, coverage, proof_records = set(), {"state": [], "read": []}, []
    for task in tasks:
        directory = positive / task["directory"]
        assert task["accepted"] and task["status"] == "PASS" and task["returncode"] == 0 and not task["timed_out"]
        assert (directory / "proof/status").read_text().split()[0] == "PASS"
        assert digest(directory / "store.v") == task["input_sha256"] == model["instrumented_sha256"]
        config = sections(directory / "proof.sby")
        if task["name"] != "cover":
            assert config["options"] == ["mode prove", "depth " + ("1" if task["name"] == "read" else "2"), "expect pass"]
            assert config["engines"] == ["smtbmc z3"]
            selected = set(task["selected_assertions"])
            expected = {cell for cell, a in model["assertions"].items() if a["scope"] == task["name"] and
                        (not a["words"] or a["words"][0] in task["word_indices"])}
            assert selected == expected and selected
            script = config["script"]
            assert script[0] == "read_rtlil prepared.il" and script[-1] == "prep -top m1_program_store"
            removed = script[1:-1]
            assert len(removed) == len(set(removed))
            assert set(removed) == {"delete m1_program_store/c:" + cell for cell in set(model["assertions"]) - selected}
            assert digest(directory / "proof/src/prepared.il") == model["lowered_sha256"]
            assert task["induction"] and "successful proof by k-induction" in (directory / "run.log").read_text()
            checked.update(selected)
            coverage[task["name"]].extend(task["word_indices"])
        else:
            assert config["options"] == ["mode cover", "depth 10", "expect pass"]
            assert config["engines"] == ["smtbmc z3"]
            assert config["script"] == ["read -formal -sv -D REACHABLE store.v", "prep -top m1_program_store"]
            assert digest(directory / "proof/src/store.v") == task["input_sha256"]
            assert len(task["witnesses"]) == 3
            for name, expected in task["witnesses"].items():
                assert digest(directory / name) == expected
        proof_records.append({"directory": task["directory"], "name": task["name"],
                              "config_sha256": digest(directory / "proof.sby"), "log_sha256": digest(directory / "run.log")})
    assert sum(t["name"] == "cover" for t in tasks) == 1
    assert all(sorted(indices) == list(range(capacity)) for indices in coverage.values())
    assert checked == set(model["assertions"])
    negative = []
    if variant == "od128":
        control_result = read(controls / "result.json")
        assert control_result["sources"][variant] == digest(original)
        controls_selected = [t for t in control_result["tasks"] if t["variant"] == variant and t["name"] in ("alias", "lane")]
        assert sorted(t["name"] for t in controls_selected) == ["alias", "lane"]
        for task in controls_selected:
            directory = controls / task["directory"]
            assert task["status"] == "FAIL" and task["returncode"] == 0 and not task["timed_out"]
            assert (directory / "proof/status").read_text().split()[0] == "FAIL"
            rtl = source.replace("endmodule", properties(capacity, reachable_checks=True) + "endmodule")
            if task["name"] == "alias":
                assert rtl.count("{program_bank, byte_address}") == 1
                rtl = rtl.replace("{program_bank, byte_address}", "{1'b0, program_bank[2:0], byte_address}")
            else:
                before = "[8*byte_address[1:0] +: 8] <= data_in;"
                assert rtl.count(before) == capacity
                rtl = rtl.replace(before, "[8*(byte_address[1:0] ^ 2'b01) +: 8] <= data_in;")
            assert (directory / "store.v").read_text() == rtl
            assert digest(directory / "store.v") == task["input_sha256"]
            assert digest(directory / "proof/src/store.v") == task["input_sha256"]
            config = sections(directory / "proof.sby")
            assert config["options"] == ["mode bmc", "depth 6", "expect fail"]
            assert config["script"] == ["read -formal -sv -D REACHABLE store.v", "prep -top m1_program_store"]
            assert config["engines"] == ["smtbmc z3"]
            assert task["witnesses"]
            for name, expected in task["witnesses"].items():
                assert digest(directory / name) == expected
            witness = inspect_control(directory, capacity)
            assert witness["validated"] and witness["violations"]
            negative.append({"name": task["name"], "observations": witness, "witnesses": task["witnesses"]})
    return {"status": "PASS_COMPLETE_VARIANT_STORE_PROOF", "variant": variant, "capacity": capacity,
            "source_sha256": digest(original), "assertions": len(checked), "positive_task_count": len(tasks),
            "complete_read_and_transition_coverage": True, "positive_assumptions": 0,
            "actual_memory_initialization_assumptions": 0, "proofs": proof_records, "negative_controls": negative,
            "positive_checkpoint_sha256": hashlib.sha256(positive_bytes).hexdigest(),
            "control_result_sha256": digest(controls / "result.json") if variant == "od128" else None,
            "scope": "Memory-unit properties; whole-chip protocol and physical gates remain separate",
            "provenance": "Only successful positive tasks are reused; corrected reset-reachable controls are audited separately"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive", type=Path, required=True)
    parser.add_argument("--positive-snapshot", type=Path)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--variant", choices=("od128", "literal255"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "preserve earlier audits"
    positive_bytes = (args.positive_snapshot or args.positive / "result.json").read_bytes()
    result = audit(args.positive, args.controls, args.variant, positive_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = args.output.with_suffix(".positive.json")
    assert not snapshot.exists(), "preserve earlier snapshots"
    snapshot.write_bytes(positive_bytes)
    result["positive_checkpoint"] = snapshot.name
    args.output.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(result["status"], args.variant, result["assertions"], "assertions")


if __name__ == "__main__":
    main()
