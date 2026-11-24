# SPDX-License-Identifier: Apache-2.0
"""Prepare a one-line experimental engine copy; map both complete project tops."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT / "tools"))
from production_sram import verify

TOP = "tt_um_khangelani_protocol_emulator"
MACRO = "RM_IHPSG13_1P_256x32_c2_bm_bist"
OLD = b"wire [15:0] instruction_shift_period = instruction[20:5];"
NEW = b"wire [15:0] instruction_shift_period = 16'd0;"


def check(value, msg):
    if not value:
        raise ValueError(msg)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def prepare(out):
    verify(ROOT)
    profile = json.loads((ROOT / "tools/production-profile.json").read_bytes())
    out.mkdir(parents=True, exist_ok=False)
    record = {}
    for variant in ("reference", "ablation"):
        directory = out / variant
        directory.mkdir()
        inputs = {}
        for name, digest in profile["files_sha256"].items():
            if not name.endswith((".v", ".vh")):
                continue
            raw = (ROOT / name).read_bytes()
            check(sha(raw) == digest, name)
            if name == "src/m1_engine.v" and variant == "ablation":
                check(raw.count(OLD) == 1, "decoded period declaration")
                raw = raw.replace(OLD, NEW)
            filename = Path(name).name
            (directory / filename).write_bytes(raw)
            inputs[filename] = sha(raw)
        record[variant] = inputs
    check([n for n in record["reference"] if record["reference"][n] != record["ablation"][n]] ==
          ["m1_engine.v"], "candidate change scope")
    write_json(out/"inputs.json", record)


def cells(path):
    text = path.read_text()
    headers = list(re.finditer(r'(?m)^\s*cell\s*\(\s*"?([\w]+)"?\s*\)\s*\{', text))
    table = {}
    for i, match in enumerate(headers):
        end = headers[i+1].start() if i+1 < len(headers) else len(text)
        body = text[match.end():end]
        area = re.search(r'(?m)^\s*area\s*:\s*([\d.]+)\s*;', body)
        seq = re.search(r'(?m)^\s*(?:ff|ff_bank|latch)\s*\(', body)
        if area:
            table[match.group(1)] = (float(area.group(1)), bool(seq))
    return table


def map_both(out):
    inputs = json.loads((out/"inputs.json").read_bytes())
    prior = json.loads((ROOT/"evidence/E0042-sram-prefetch-screen/mapped/verification.json").read_bytes())
    libs = [Path(p) for p in prior["libraries"] if p.endswith(("stdcell_typ_1p20V_25C.lib",
                                                              MACRO+"_typ_1p20V_25C.lib"))]
    check(len(libs) == 2, "nominal library pair")
    std = next(p for p in libs if "stdcell" in p.name)
    macro = next(p for p in libs if MACRO in p.name)
    for p in libs:
        check(sha(p.read_bytes()) == prior["libraries"][str(p)]["sha256"], "library identity")
    table = cells(std) | cells(macro)
    check(MACRO in table and len(table) > 50, "Liberty cell area table")
    record = {"started_utc": stamp(), "scope": "matched nominal cell mapping; no placement or routing",
              "reference_libraries": {p.name: sha(p.read_bytes()) for p in libs},
              "yosys": subprocess.check_output(["yosys", "-V"], text=True).strip(), "results": {}}
    try:
        for name, expected in inputs.items():
            d = out / name
            check(all(sha((d/n).read_bytes()) == h for n,h in expected.items()), "copied sources")
            stats = d / "stat.json"
            commands = [f"read_verilog -lib {d / (MACRO+'.vh')}",
                        "read_verilog -sv -DSYNTHESIS " + " ".join(str(d/n) for n in expected if n.endswith(".v")),
                        f"hierarchy -check -top {TOP}", f"synth -flatten -noabc -top {TOP}", "check -assert",
                        f"dfflibmap -liberty {std}", f"abc -liberty {std}", "clean",
                        f"tee -o {stats} stat -json -top {TOP} -liberty {std} -liberty {macro}"]
            path = d / "map.ys"
            recipe = "\n".join(commands) + "\n"
            if stats.exists():
                check(path.read_text() == recipe and "End of script." in (d/"map.log").read_text(),
                      "incomplete or different mapping recipe")
            else:
                path.write_text(recipe)
                with (d/"map.log").open("wb") as log:
                    proc = subprocess.run(["yosys", "-Q", "-s", str(path)], stdout=log,
                                          stderr=subprocess.STDOUT, timeout=180)
                check(proc.returncode == 0, name + " Yosys mapping")
            stat = json.loads(stats.read_bytes())["modules"]["\\"+TOP]
            counts = {n.lstrip("\\"): count for n,count in stat["num_cells_by_type"].items()}
            # Yosys flatten emits portless scope records to preserve source attributes.
            metadata = counts.pop("$scopeinfo", 0)
            unknown = set(counts) - set(table)
            check(not unknown and counts.get(MACRO) == 1, f"{name} unaccounted cells {unknown} / SRAM")
            std_area = sum(table[k][0]*c for k,c in counts.items() if k != MACRO)
            record["results"][name] = {"cell_counts": counts, "scope_attributes": metadata,
                                       "std_cells": sum(counts.values())-1,
                                       "sequential_cells": sum(c for k,c in counts.items() if k != MACRO and table[k][1]),
                                       "std_cell_area_um2": round(std_area,4), "macro_area_um2": table[MACRO][0],
                                       "total_um2": round(std_area+table[MACRO][0],4),
                                       "source_hashes": expected}
        ref, alt = [record["results"][key] for key in ("reference", "ablation")]
        record["savings_percent"] = {k: round(100*(1-alt[k]/ref[k]),6)
                                     for k in ("std_cell_area_um2","total_um2")}
        record["status"] = "matched"
    except Exception as exc:
        record.update(status="incomplete", error=str(exc))
        raise
    finally:
        record["ended_utc"] = stamp()
        write_json(out/"mapped.json", record)
        print(record["status"], record.get("savings_percent", {}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare","map"))
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    output = args.out.resolve()
    check(output.is_relative_to(ROOT/"build"), "use a new workspace build directory")
    (prepare if args.action == "prepare" else map_both)(output)
