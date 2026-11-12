# SPDX-License-Identifier: Apache-2.0
"""Require specific public counterexamples from three actual source mutations."""
import argparse
import json
import os
from pathlib import Path
import random
import subprocess
import time
import xml.etree.ElementTree as ET

from shared_read import generate, MANIFEST, ROOT, digest

MUTATIONS = {
    "high-bank-alias": ("load_mode ? {1'b0, bank_address[8:2]} : pc", "load_mode ? {2'b0, bank_address[7:2]} : pc"),
    "fetch-uses-loader": ("load_mode ? {1'b0, bank_address[8:2]} : pc", "{1'b0, bank_address[8:2]}"),
    "missing-length": ("        if (load_length)\n            data_out = program_length;\n", ""),
}


def expected_record(control):
    rng = random.Random(20261112)
    words = [rng.getrandbits(32) for _ in range(128)]
    words[:3] = [0x00FFFFA5, 0x00FFFF5A, 0x80000000]
    writes = [[n, lane, 0xC0 | (n % 8) * 4 | lane, (word >> (8 * lane)) & 255]
              for n, word in enumerate(words) for lane in range(4)]
    reads = [[n, lane, (words[n % 64 if control == "high-bank-alias" else n] >> (8 * lane)) & 255, 255]
             for n in range(128) for lane in range(4)]
    trace = ([[n + 1, 0, 0xA5, 255] for n in range(6)] if control == "fetch-uses-loader"
             else [[1, 0, 0xA5, 255], [2, 0, 0x5A, 255]] + [[2, 2, 0x5A, 255]] * 4)
    return {"seed": 20261112, "words": words, "writes": writes, "reads": reads,
            "length": [0xA5 if control == "missing-length" else 128, 255], "ready": True, "trace": trace}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    sources, manifest = generate()
    assert manifest == json.loads(MANIFEST.read_bytes())
    result = {"status": "RUNNING", "sources": manifest["od128"]["source_sha256"], "stages": [],
              "scope": "Public loading, every stored byte, length and six execution edges; three deliberate RTL faults"}

    def save():
        (out / "result.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())

    save()
    try:
        for control in ("baseline", *MUTATIONS):
            src = out / control / "src"
            src.mkdir(parents=True)
            variant = dict(sources)
            if control != "baseline":
                original, replacement = MUTATIONS[control]
                text = variant["m1_program_store.v"].decode()
                assert text.count(original) == 1
                variant["m1_program_store.v"] = text.replace(original, replacement).encode()
            hashes = {name: digest(raw) for name, raw in variant.items()}
            for name, raw in variant.items():
                (src / name).write_bytes(raw)
            assert (hashes == result["sources"]) == (control == "baseline")
            expected = expected_record(control)
            assert (expected == expected_record("baseline")) == (control == "baseline")
            for simulator in ("icarus", "verilator"):
                stage = out / control / simulator
                stage.mkdir()
                env = dict(os.environ, GENERAL_IO="yes", SHARED_READ_RECORD=str(stage / "observations.json"),
                           COCOTB_RANDOM_SEED="20261112")
                for key in ("GATES", "G1_PHYSICAL", "G2_PHYSICAL", "MAKEFLAGS", "COCOTB_TESTCASE", "COCOTB_TEST_FILTER"):
                    env.pop(key, None)
                command = ["make", "-C", "test", "SIM=" + simulator, "SRC_DIR=" + str(src),
                           "SIM_BUILD=" + str(stage / "sim"), "COCOTB_RESULTS_FILE=" + str(stage / "results.xml"),
                           "COCOTB_TEST_MODULES=test_shared_read_controls", "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
                start = time.monotonic()
                with (stage / "run.log").open("w") as log:
                    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                assert proc.returncode == 0, "simulation execution failed; not a valid negative control"
                cases = ET.parse(stage / "results.xml").getroot().findall(".//testcase")
                assert len(cases) == 1 and cases[0].attrib["name"] == "public_shared_read_witness"
                assert cases[0].attrib["classname"] == "test_shared_read_controls" and not list(cases[0])
                assert ("Running on Icarus Verilog" if simulator == "icarus" else "Running on Verilator") in (stage / "run.log").read_text()
                actual = json.loads((stage / "observations.json").read_bytes())
                assert actual == expected, "missing or different public counterexample: " + control
                result["stages"].append({"control": control, "simulator": simulator, "command": command,
                    "seconds": round(time.monotonic() - start, 3), "source_sha256": hashes,
                    "observations_sha256": digest((stage / "observations.json").read_bytes()),
                    "baseline_accepted": control == "baseline", "expected_mutant_rejection": control != "baseline"})
                save()
        result["status"] = "PASS_PUBLIC_SHARED_READ_MUTATION_CONTROLS"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()
    print(result["status"], flush=True)


if __name__ == "__main__":
    main()
