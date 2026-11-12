# SPDX-License-Identifier: Apache-2.0
"""Prove lint/constant-check cleanup preserves the already simulated candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    result = {"status": "RUNNING", "scope": "COMPLETE_CANDIDATE_FUNCTIONAL_CLEANUP_EQUIVALENCE",
              "runner_sha256": digest(Path(__file__)), "variants": {}}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant in ("od128", "literal255"):
            old, new = args.before.resolve()/variant/"src", args.after.resolve()/variant/"src"
            before = {p.name: digest(p) for p in old.glob("*.v")}
            after = {p.name: digest(p) for p in new.glob("*.v")}
            assert before.keys() == after.keys()
            for name in ("m1_data_store.v", "m1_input_sync.v"):
                assert before[name] == after[name]
            # Exact character identity after removing whitespace: no ports,
            # expressions, literals, comments or connections can change here.
            assert re.sub(r"\s+", "", (old/"project.v").read_text()) == re.sub(r"\s+", "", (new/"project.v").read_text())
            store = (old/"m1_program_store.v").read_text()
            if variant == "literal255":
                prior = "(data_in >= 8'd1) && (data_in <= 8'd255)"
                assert store.count(prior) == 1
                store = store.replace(prior, "(data_in != 8'd0)")
            assert store == (new/"m1_program_store.v").read_text()
            path = out/variant
            path.mkdir()
            script = f"read_verilog {old/'m1_engine.v'}; rename m1_engine old_engine; "
            script += f"read_verilog {new/'m1_engine.v'}; rename m1_engine new_engine; "
            script += "proc; opt; equiv_make old_engine new_engine equivalence; hierarchy -top equivalence; "
            script += "equiv_simple; equiv_induct -seq 3; equiv_status -assert"
            (path/"engine.ys").write_text(script+"\n")
            with (path/"engine.log").open("w") as log:
                process = subprocess.run(["yosys", "-Q", "-s", str(path/"engine.ys")], cwd=ROOT,
                                         stdout=log, stderr=subprocess.STDOUT, timeout=180)
            assert process.returncode == 0, f"{variant} engine equivalence failed"
            log = (path/"engine.log").read_text()
            assert "Equivalence successfully proven!" in log
            result["variants"][variant] = dict(before=before, after=after, engine_equivalence="PASS",
                unchanged_data_and_sync=True, top_whitespace_only=True,
                store_change="8-bit constant ceiling removal" if variant == "literal255" else "NONE")
            save()
            print(variant, "engine equivalence PASS", flush=True)
        theorem = "module length_check(input [7:0] value, output equal);\n"
        theorem += "assign equal = ((value >= 8'd1) && (value <= 8'd255)) == (value != 8'd0);\nendmodule\n"
        (out/"length_check.v").write_text(theorem)
        script = f"read_verilog {out/'length_check.v'}; prep -top length_check; sat -verify -prove equal 1 -show-inputs"
        with (out/"length_check.log").open("w") as log:
            process = subprocess.run(["yosys", "-Q", "-p", script], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=30)
        assert process.returncode == 0
        assert "SUCCESS" in (out/"length_check.log").read_text()
        result.update(status="PASS_FUNCTIONALLY_EQUIVALENT_CLEANUP", length_predicate="PASS_ALL_256_VALUES",
                      limitation="No equivalence to G1 compact10 and no physical inference; only before/after cleanup of the G2 candidate")
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
