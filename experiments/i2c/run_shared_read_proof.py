# SPDX-License-Identifier: Apache-2.0
"""Complete-chip temporal equivalence and an independently initialized reset base."""
import argparse
import json
from pathlib import Path
import sys

from shared_read import MANIFEST, PARENT, ROOT, digest

sys.path.insert(0, str(ROOT / "experiments/spi_phase"))
from run_program_sensitivity import execute

TOP = "tt_um_khangelani_protocol_emulator"


def read(path):
    return json.loads(path.read_bytes())


def state_matches(models):
    states, ports, all_names = {}, {}, set()
    for label, module in models.items():
        qbits = {bit for cell in module["cells"].values() if "dff" in cell["type"].lower()
                 for bit in cell["connections"]["Q"] if isinstance(bit, int)}
        assert len(qbits) == 4278
        assert not any("latch" in c["type"].lower() or c["type"] in ("$assume", "$anyseq", "$anyconst")
                       for c in module["cells"].values())
        names = {n: w["bits"] for n, w in module["netnames"].items() if not n.startswith("$")}
        states[label] = {n: bits for n, bits in names.items()
                         if any(b in qbits for b in bits) and all(not isinstance(b, int) or b in qbits for b in bits)}
        ports[label] = {n: (p["direction"], len(p["bits"])) for n, p in module["ports"].items()}
        all_names |= set(names)
    common = set(states["gold"]) & set(states["gate"])
    for label, module in models.items():
        qbits = {b for c in module["cells"].values() if "dff" in c["type"].lower()
                 for b in c["connections"]["Q"] if isinstance(b, int)}
        assert qbits <= {b for name in common for b in states[label][name]}
    assert ports["gold"] == ports["gate"] == {
        "ui_in": ("input", 8), "uo_out": ("output", 8), "uio_in": ("input", 8),
        "uio_out": ("output", 8), "uio_oe": ("output", 8), "ena": ("input", 1),
        "clk": ("input", 1), "rst_n": ("input", 1)}
    return sorted(common), sorted(all_names - common - set(ports["gold"]))


def check_temporal(before, after, state_names):
    comparisons = {n: c for n, c in before["cells"].items() if c["type"] == "$equiv"}
    output_bits = {b for p in before["ports"].values() if p["direction"] == "output" for b in p["bits"]}
    assert len(output_bits) == 24 and len(comparisons) == 4572
    assert output_bits <= {b for c in comparisons.values() for b in c["connections"]["Y"]}
    pairs = {(c["connections"]["A"][0], c["connections"]["B"][0]) for c in comparisons.values()}
    for name in state_names:
        gold, gate = (before["netnames"][name + suffix]["bits"] for suffix in ("_gold", "_gate"))
        assert len(gold) == len(gate)
        assert all((a, b) in pairs or (b, a) in pairs for a, b in zip(gold, gate)), name
    assert all(after["cells"][n]["connections"]["A"] == after["cells"][n]["connections"]["B"] for n in comparisons)
    return len(comparisons)


def check_reset(model, state_names, comparison_bits):
    assertions = [c for c in model["cells"].values() if c["type"] == "$assert"]
    comparisons = [c for c in model["cells"].values() if c["type"] == "$eqx"]
    assert {tuple(c["connections"]["Y"]) for c in comparisons} == {tuple(c["connections"]["A"]) for c in assertions}
    assert all(c["connections"]["EN"] == ["1"] for c in assertions)
    assert not any(c["type"] == "$assume" for c in model["cells"].values())
    pairs = {(tuple(c["connections"]["A"]), tuple(c["connections"]["B"])) for c in comparisons}
    targets = state_names + [n for n, p in model["ports"].items() if p["direction"] == "output"]
    for name in targets:
        gold, gate = (tuple(model["netnames"][name + suffix]["bits"]) for suffix in ("_gold", "_gate"))
        assert (gold, gate) in pairs or (gate, gold) in pairs, name
    bits = sum(int(c["parameters"]["A_WIDTH"], 2) for c in comparisons)
    assert bits == comparison_bits and len(assertions) == 217
    return {"vector_assertions": len(assertions), "compared_bits_including_aliases": bits}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    expected = {"gold": read(PARENT / "sources/source-manifest.json")["od128"]["source_sha256"],
                "gate": read(MANIFEST)["od128"]["source_sha256"]}
    dirs = {"gold": PARENT / "sources/od128", "gate": args.variants.resolve() / "od128/src"}
    result = {"status": "RUNNING", "sources": expected, "stages": {},
              "scope": "Complete real chips; all actual state and public outputs; digital synchronous model after one sampled reset"}

    def save():
        (out / "result.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())

    def run(label, script, limit):
        path = out / (label + ".ys")
        path.write_text(script + "\n")
        stage = execute(["yosys", "-Q", "-s", str(path)], out / (label + ".log"), limit)
        result["stages"][label] = stage
        save()
        assert stage["returncode"] == 0 and not stage["timed_out"], label

    save()
    try:
        models = {}
        for label, src in dirs.items():
            assert {n: digest((src / n).read_bytes()) for n in expected[label]} == expected[label]
            script = "read_verilog " + " ".join(str(src / n) for n in expected[label])
            script += f'; hierarchy -check -top {TOP}; proc; flatten; opt; check -assert; rename {TOP} {label}; '
            script += f'write_rtlil {out / (label + ".il")}; write_json {out / (label + ".json")}'
            run(label, script, 60)
            models[label] = read(out / (label + ".json"))["modules"][label]
        state_names, excluded = state_matches(models)
        (out / "blacklist.txt").write_text("\n".join(excluded) + "\n")
        result.update(actual_state_bits_per_chip=4278, common_state_names=state_names,
                      excluded_combinational_names=excluded)
        inputs = f'read_rtlil {out / "gold.il"} {out / "gate.il"}; '
        script = inputs + f'equiv_make -blacklist {out / "blacklist.txt"} gold gate equivalence; hierarchy -top equivalence; '
        script += f'write_json {out / "before.json"}; equiv_simple; equiv_induct -seq 1; equiv_status -assert; write_json {out / "after.json"}'
        run("temporal", script, 300)
        assert "Equivalence successfully proven!" in (out / "temporal.log").read_text()
        count = check_temporal(read(out / "before.json")["modules"]["equivalence"],
                               read(out / "after.json")["modules"]["equivalence"], state_names)
        result.update(public_output_bits=24, proven_bit_comparisons_including_aliases=count, temporal_maximum_step=1)
        script = inputs + f'equiv_make -make_assert -blacklist {out / "blacklist.txt"} gold gate equivalence; '
        script += f'hierarchy -top equivalence; dffunmap; opt_clean; write_json {out / "reset.json"}; '
        script += 'sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports'
        run("reset", script, 90)
        assert "SAT proof finished - no model found: SUCCESS!" in (out / "reset.log").read_text()
        result["reset_base"] = check_reset(read(out / "reset.json")["modules"]["equivalence"], state_names, count)
        for label, src in dirs.items():
            assert {n: digest((src / n).read_bytes()) for n in expected[label]} == expected[label]
        result["model_sha256"] = {n: digest((out / n).read_bytes()) for n in (
            "gold.il", "gate.il", "gold.json", "gate.json", "before.json", "after.json", "reset.json", "blacklist.txt")}
        result["status"] = "PASS_RESET_REACHABLE_COMPLETE_CHIP_EQUIVALENCE"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()
    print(result["status"], flush=True)


if __name__ == "__main__":
    main()
