# SPDX-License-Identifier: Apache-2.0
"""Test the isolated burst-disabled RTL with the established public oracles."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from map_variant import OLD, NEW, ROOT, check, sha, stamp, verify, write_json
from screen import case_list, inspect, plan

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"powered-netlist"))
from run import G4, archive_member, build, stage_fixture


def simulate(cmd, out, env=None):
    with out.open("wb") as log:
        proc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    check(proc.returncode == 0, "simulator failed: " + str(out))


def uart_tests(out, candidate, models):
    tb = (HERE/"uart_tb.sv").read_bytes()
    marker = b'$display("MISMATCH %s'
    check(tb.count(marker) == 1, "UART diagnostic insertion")
    tb = tb.replace(marker, b'$display("FAULT_PROBE %0d %0d %0d %0d",n,status,raw,valid);\n            '+marker)
    (out/"uart_tb.sv").write_bytes(tb)
    src = sorted(candidate.glob("*.v"))
    simulate(["iverilog","-g2012","-DFUNCTIONAL","-DSYNTHESIS","-s","uart_tb","-o",str(out/"uart.vvp"),
              str(out/"uart_tb.sv"),*map(str,src),*map(str,sorted(models.glob("*.v")))], out/"compile.log")
    result = {}
    for direction in ("tx","rx"):
        rx = direction == "rx"
        for mode in ("manual","released"):
            source_path = HERE/("manual_"+direction+".asm") if mode=="manual" else ROOT/"programs/od128-sram-v1"/("uart_"+direction+".asm")
            for period in (4,434):
                key = f"{direction}-{mode}-{period}"
                pp, cp = out/(key+".plan"), out/(key+".cases")
                image = plan(source_path.read_text().replace(".const PERIOD 434",f".const PERIOD {period}"), pp)
                rows = case_list(period,rx,mode=="released")
                cp.write_text("".join(" ".join(map(str,row))+"\n" for row in rows))
                path = out/(key+".log")
                simulate(["vvp",str(out/"uart.vvp"),f"+plan={pp}",f"+cases={cp}",f"+steps={image['load_steps']}",
                          f"+period={period}",f"+rx={int(rx)}",f"+manual={int(mode=='manual')}"],path)
                log = path.read_text()
                if mode == "manual":
                    image.update(inspect(log, rows, period, rx, True, False))
                else:
                    probe = [list(map(int,line.split()[1:])) for line in log.splitlines() if line.startswith("FAULT_PROBE ")]
                    check(len(probe) == 1, "released burst escaped candidate fault")
                    # TX bursts at PC4 and RX at PC5. No valid raw byte can be committed at that first edge.
                    check(probe[0][1:] == ([0xE5,0,0] if rx else [0xE4,0,0]), "unexpected fault signature")
                    image["fault_at_edge_status_raw_valid"] = probe[0]
                result[key] = image
    return result


def other_g3(out, candidate, models):
    fixture = stage_fixture(out)
    build(out/"examples")
    env = dict(os.environ, COUNCIL_ROOT=str(ROOT), G2_CURRENT="yes", G2_SRAM="yes", GENERAL_IO="yes",
               SRAM_MODEL_DIR=str(models), G3_PROGRAM_BUILD=str(out/"examples"), G3_PROGRAM_RECORDS=str(out/"records"),
               COCOTB_RANDOM_SEED="20261124", PYTHONHASHSEED="0",
               PYTHONPATH=os.pathsep.join(map(str,(fixture, ROOT/"test", ROOT))),
               COCOTB_TEST_FILTER="^council_powered_g3[.]assembled_[lsi]")
    command = ["make","-C",str(fixture),"SIM=icarus","SRC_DIR="+str(candidate),"SIM_BUILD="+str(out/"sim"),
               "COCOTB_TEST_MODULES=council_powered_g3","COCOTB_RESULTS_FILE="+str(out/"results.xml"),
               "FST=","COCOTB_PLUSARGS=+NO_DUMP"]
    simulate(command,out/"g3.log",env)
    tests = ET.parse(out/"results.xml").findall(".//testcase")
    ran = {t.get("name") for t in tests if not list(t)}
    check(ran == {"assembled_loader_controls","assembled_spi_examples","assembled_i2c_examples"},
          "candidate G3 selection or failure")
    new = list(map(json.loads,(out/"records/records.jsonl").read_bytes().splitlines()))
    ref = archive_member(G4/"program-tools",14094030144,"icarus/records/records.jsonl")
    old = [r for r in map(json.loads,ref.splitlines()) if r["group"] in ("loader","spi","i2c")]
    key = lambda r: r["name"]
    check(len(new) == 50 and sorted(new,key=key) == sorted(old,key=key), "candidate G3 records differ")
    return {"groups": sorted(ran), "cases": len(new), "expected_rejections": sum(not x["expected_acceptance"] for x in new),
            "observations": sum(x["observations"] for x in new)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared",type=Path)
    parser.add_argument("out",type=Path)
    args = parser.parse_args()
    out, candidate = args.out.resolve(), args.prepared.resolve()/"ablation"
    check(out.is_relative_to(ROOT/"build") and candidate.is_relative_to(ROOT/"build"), "use build paths")
    out.mkdir(parents=True,exist_ok=False)
    guard = verify(ROOT)
    for name in read_inputs(candidate):
        expected = (ROOT/"src"/name).read_bytes()
        if name == "m1_engine.v":
            expected = expected.replace(OLD,NEW)
        check((candidate/name).read_bytes() == expected, "candidate scope "+name)
    models = out/"models"
    models.mkdir()
    for n,expected in guard["model_sha256"].items():
        raw = gzip.decompress((ROOT/"evidence/E0042-sram-prefetch-screen/feasibility/verilog"/(n+".gz")).read_bytes())
        check(sha(raw) == expected,"SRAM identity")
        (models/n).write_bytes(raw)
    result = {"started_utc":stamp(),"candidate_sha256":sha((candidate/"m1_engine.v").read_bytes())}
    try:
        result["uart"] = uart_tests(out,candidate,models)
        result["non_uart_g3"] = other_g3(out,candidate,models)
        result["status"] = "pass"
    except Exception as error:
        result.update(status="incomplete",error=str(error))
        raise
    finally:
        result["ended_utc"] = stamp()
        write_json(out/"result.json",result)
        print(result["status"],out)


def read_inputs(candidate):
    expected = json.loads((candidate.parent/"inputs.json").read_bytes())["ablation"]
    check({p.name for p in candidate.iterdir() if p.suffix in (".vh",".v")} == set(expected), "copied source list")
    return expected


if __name__ == "__main__":
    main()
