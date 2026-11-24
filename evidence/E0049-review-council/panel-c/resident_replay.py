"""Build the two DUTs and run the trusted-session combined I2C study."""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from selector_orders import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES, checked, execute, memory_file, sha


G4 = "5bdc0e6b6449a829a5da1f8f9a8060257e974843"
PDK_COMMIT = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"


def released(repo, path):
    return execute(["git", "-C", repo, "-c", f"safe.directory={repo}", "cat-file", "blob", f"{G4}:{path}"], repo)


def prepare_fixture(repo, inputs, result):
    sources = {"tools/assembler.py":"assembler.py", "tools/i2c_oracle.py":"i2c_oracle.py",
               "experiments/i2c/target.py":"target.py", "programs/od128-sram-v1/i2c_write_read.asm":"i2c_write_read.asm",
               "programs/od128-sram-v1/examples.json":"examples.json"}
    hashes = {}
    for path, name in sources.items():
        raw = released(repo, path)
        (inputs / name).write_bytes(raw)
        hashes[path] = sha(raw)
    original_name = "experiments/i2c/public_bus.py"
    raw = released(repo, original_name)
    hashes[original_name] = sha(raw)
    transport = raw.decode()
    # Preserve the original target, event scheduler and independent oracle. Route the
    # two existing drive points onto distinct pad drivers and check the sensed wires.
    substitutions = [
        ("    dut.uio_in.value = bus", "    dut.peer_pulls.value = 0\n    await Timer(1, unit='ps')\n"
         "    assert int(dut.pads.value) & 3 == bus"),
        ("            dut.uio_in.value = resolved", "            dut.peer_pulls.value = target_oe\n"
         "            await Timer(1, unit='ps')\n            assert int(dut.pads.value) & 3 == resolved"),
        ("    dut.ena.value = 1","    assert int(dut.ena.value) == 1"),
        ("        dut.ena.value = 0","        assert int(dut.ena.value) == 1"),
    ]
    for old, new in substitutions:
        if transport.count(old) != 1:
            raise ValueError(f"public-bus adaptation mismatch at {old!r}")
        transport = transport.replace(old,new)
    (inputs / "fixture_transport.py").write_text(transport)
    result["released_fixture_sha256"] = hashes
    result["adapted_transport_sha256"] = sha((inputs / "fixture_transport.py").read_bytes())
    shutil.copyfile(SCRIPTS / "resident_case.py", inputs / "resident_case.py")
    result["case_sha256"] = sha((inputs / "resident_case.py").read_bytes())


def cocotb_config(option, *values):
    return subprocess.check_output(["cocotb-config", option, *values], text=True).strip()


def evaluate(args,result):
    repo, libs, out = args.repo.resolve(), args.pdk_libs.resolve(), args.out.resolve()
    inputs = out / "fixture"
    inputs.mkdir()
    prepare_fixture(repo, inputs, result)
    bench = SCRIPTS / "resident_tb.v"
    result["bench_sha256"] = sha(bench.read_bytes())
    result["runner_sha256"] = sha(Path(__file__).read_bytes())
    result["simulator"] = execute(["iverilog", "-V"], out).decode().splitlines()[0]
    result["cocotb"] = cocotb_config("--version")
    result["python"] = sys.version
    result["pdk_commit"] = PDK_COMMIT
    result["library_sha256"] = PDK_FILES
    for name, expected in PDK_FILES.items():
        checked((libs / name).read_bytes(), expected, name)
    archive = repo / ARCHIVE
    checked(archive.read_bytes(), ARCHIVE_SHA, ARCHIVE)
    lock = json.loads(released(repo, "tools/production-profile.json"))
    result["qualified_archive_sha256"] = ARCHIVE_SHA
    result["submitted_netlist_sha256"] = NETLIST_SHA
    result["dut_results"] = {}
    with ZipFile(archive) as source, ExitStack() as stack:
        def ram(name, raw):
            return stack.enter_context(memory_file(name, raw))
        rtl, models = [], []
        for name, expected in lock["files_sha256"].items():
            if name.startswith("src/") and name.endswith(".v"):
                rtl.append(ram(name.rsplit("/",1)[1],checked(source.read(name),expected,name)))
        for name, expected in lock["model_sha256"].items():
            path = f"evidence/E0042-sram-prefetch-screen/feasibility/verilog/{name}.gz"
            models.append(ram(name,checked(gzip.decompress(released(repo,path)),expected,name)))
        if len(rtl) != 5 or len(models) != 2:
            raise ValueError("incorrect source set")
        netlist = ram("chip.v",checked(source.read("tt_submission/tt_um_khangelani_protocol_emulator.v"),
                                     NETLIST_SHA,"G4 netlist"))
        implementations = {"rtl": rtl + models, "g4_netlist": [netlist,*models,*(libs / name for name in PDK_FILES)]}
        observed = []
        for name, verilog in implementations.items():
            stage = out / name
            stage.mkdir()
            env = dict(os.environ, COCOTB_TOPLEVEL="resident_tb", COCOTB_TEST_MODULES="resident_case",
                       TOPLEVEL_LANG="verilog", PYGPI_PYTHON_BIN=cocotb_config("--python-bin"),
                       LIBPYTHON_LOC=cocotb_config("--libpython"), COCOTB_RANDOM_SEED="20261124",
                       COCOTB_RESULTS_FILE=str(stage / "junit.xml"), RESIDENT_OUTPUT=str(stage),
                       RESIDENT_CONDITION=args.condition, PYTHONDONTWRITEBYTECODE="1")
            with memory_file("warm.vvp") as compiled:
                execute(["iverilog","-g2012","-DFUNCTIONAL","-DSYNTHESIS","-DSIM","-s","resident_tb",
                         "-o",compiled,bench,*verilog],out)
                process = subprocess.run(["vvp","-M",cocotb_config("--lib-dir"),
                                          "-m",cocotb_config("--lib-name","vpi","icarus"),compiled],
                                         cwd=inputs, env=env, capture_output=True,timeout=600)
                (stage / "run.log").write_bytes(process.stdout + process.stderr)
                if process.returncode:
                    raise RuntimeError(f"{name} vvp failed; see retained run.log")
                tests = ET.parse(stage / "junit.xml").findall(".//testcase")
                if len(tests) != 1 or any(t.find("failure") is not None or t.find("error") is not None for t in tests):
                    raise ValueError(f"{name} cocotb test failed; see retained run.log")
                observation = json.loads((stage / "observations.json").read_bytes())
                status = "PASS_VALID_GATED_DIAGNOSTIC" if args.condition == "valid-gated" else "PASS_WARM_COMBINED_I2C"
                if observation["status"] != status:
                    raise ValueError(f"incomplete {name} record")
                observed.append(observation)
                result["dut_results"][name] = sha((stage / "observations.json").read_bytes())
        if observed[0] != observed[1]:
            raise ValueError("RTL and G4 netlist transaction/guard observations differ")
    result["status"] = "PASS_VALID_GATED_DIAGNOSTIC" if args.condition == "valid-gated" else "PASS_RESIDENT_REARM_SCREEN"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path, required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--pdk-libs",type=Path,required=True)
    parser.add_argument("--image-id",required=True)
    parser.add_argument("--condition", choices=["strict","valid-gated"], default="strict")
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    result = {"status":"INCOMPLETE","started_utc":datetime.now(timezone.utc).isoformat(),
              "actual_invoker_image":args.image_id,"source_g4":G4,"condition":args.condition}
    start = time.monotonic()
    try:
        evaluate(args,result)
    except Exception as error:
        result["failure"] = str(error)
        raise
    finally:
        result["ended_utc"] = datetime.now(timezone.utc).isoformat()
        result["runtime_seconds"] = round(time.monotonic() - start,3)
        (args.out / "result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"], result["runtime_seconds"])


if __name__ == "__main__":
    main()
