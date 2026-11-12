# SPDX-License-Identifier: Apache-2.0
"""Prove new general instructions on exact generated engines; retain controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"experiments/spi_phase"))
from run_program_sensitivity import vcd_frames


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_control(name, task):
    observations = []
    for witness in (task/"proof/engine_0").glob("trace*.vcd"):
        normalized = task/("parsed-"+witness.name)
        source = witness.read_text()
        changed = source.replace("$scope module m1_engine $end", "$scope module public_spi $end")
        assert changed != source
        normalized.write_text(changed)
        rows = [r for r in vcd_frames(normalized) if r["time"] % 10 == 0]
        for a, b in zip(rows, rows[1:]):
            if name == "keeps_loop" and a.get("f_branch") and a.get("loop_active") and b.get("loop_active"):
                assert b["pc"] == a["f_destination"] and b["state"] == 0
                observations.append(dict(edge=a["time"], destination=a["f_destination"],
                                         observed_pc=b["pc"], observed_loop_active=b["loop_active"]))
            if name == "actively_drives_high" and a.get("f_serial") and a.get("instruction", 0) & 1:
                mask = a["f_tx_mask"]
                if b.get("gpio_value", 0) & b.get("gpio_oe", 0) & mask:
                    observations.append(dict(edge=a["time"], tx_mask=mask,
                                             observed_value=b["gpio_value"], observed_oe=b["gpio_oe"]))
    return {"validated": bool(observations), "observations": observations}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new build directory required")
    out.mkdir(parents=True)
    properties = ROOT/"experiments/i2c/general_properties.vh"
    result = {"status": "RUNNING", "scope": "GENERAL_INSTRUCTION_SAFETY_NOT_PROTOCOL_OR_PHYSICAL",
              "properties_sha256": digest(properties), "runner_sha256": digest(Path(__file__)),
              "witness_parser_sha256": digest(ROOT/"experiments/spi_phase/run_program_sensitivity.py"),
              "assumptions": ["first sampled edge reset; other inputs arbitrary", "digital sampled_inputs, no analog CDC claim"],
              "sources": {}, "tasks": []}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant in ("od128", "literal255"):
            path = args.variants/variant/"src/m1_engine.v"
            source = path.read_text()
            result["sources"][variant] = digest(path)
            appendix = "\n"+properties.read_text()+"\n"
            modified = source.replace("endmodule", appendix+"endmodule")
            assert modified.replace(appendix, "") == source
            cases = [("instruction", "prove", "PASS", modified), ("covers", "cover", "PASS", modified)]
            if variant == "od128":
                wrong = modified.replace("            loop_active <= 1'b0;", "            loop_active <= loop_active;", 1)
                assert wrong != modified
                cases.append(("keeps_loop", "bmc", "FAIL", wrong))
                wrong = modified.replace("(selected_shift_tx_bit && !serial_open_drain) ? shift_tx_mask : 8'd0",
                                         "selected_shift_tx_bit ? shift_tx_mask : 8'd0")
                wrong = wrong.replace("(!serial_open_drain || !selected_shift_tx_bit) ? shift_tx_mask : 8'd0",
                                      "shift_tx_mask")
                assert wrong != modified
                cases.append(("actively_drives_high", "bmc", "FAIL", wrong))
            for name, mode, expected, rtl in cases:
                task = out/(variant+"-"+name)
                task.mkdir()
                (task/"engine.v").write_text(rtl)
                depth = 12 if mode != "cover" else 30
                flags = "-D SERIAL_OPTIONS" if variant == "od128" else ""
                config = f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n"
                config += f"read -formal -sv {flags} engine.v\nprep -top m1_engine\n\n[files]\n{task/'engine.v'}\n"
                (task/"proof.sby").write_text(config)
                start = time.monotonic()
                timed_out = False
                with (task/"run.log").open("w") as log:
                    try:
                        proc = subprocess.run(["sby", "-f", "-d", str(task/"proof"), str(task/"proof.sby")],
                            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                        code = proc.returncode
                    except subprocess.TimeoutExpired:
                        code, timed_out = 124, True
                raw = (task/"proof/status").read_text().strip() if (task/"proof/status").exists() else "MISSING"
                match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw)
                status = match[1] if match else "MISSING"
                log = (task/"run.log").read_text()
                witnesses = {p.relative_to(task).as_posix(): digest(p) for p in (task/"proof/engine_0").glob("trace*.vcd")}
                induction = "successful proof by k-induction" in log
                accepted = code == 0 and status == expected and not timed_out
                if mode == "prove":
                    accepted &= induction
                if mode in ("bmc", "cover"):
                    accepted &= bool(witnesses)
                control = inspect_control(name, task) if mode == "bmc" and status == "FAIL" else None
                if mode == "bmc":
                    accepted &= bool(control and control["validated"])
                row = dict(variant=variant, name=name, mode=mode, expected=expected,
                           status=status, returncode=code, timed_out=timed_out, accepted=accepted,
                           induction=induction, seconds=round(time.monotonic()-start, 3),
                           witnesses=witnesses, control=control, input_sha256=digest(task/"engine.v"))
                result["tasks"].append(row)
                save()
                print(variant, name, status, "ACCEPTED" if accepted else "NOT_QUALIFIED", flush=True)
        assert digest(properties) == result["properties_sha256"], "source drift"
        result["status"] = "PASS_SCOPED_INSTRUCTION_PROOFS" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
