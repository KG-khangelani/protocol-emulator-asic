# SPDX-License-Identifier: Apache-2.0
"""Repeat the frozen SPI comparisons and check observations against the retained records."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
DECLARATIONS = ("declaration.md", "matrix.md", "mapping-amendment.md", "bypass-declaration.md", "peer-declaration.md")
COMPARED_FIELDS = ("images", "host_counts", "public_rows_sha256", "input_case_count", "observations",
                   "single_sm_resident_sequence")


def compressed_json(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def failures(record):
    result = []
    for failure in record["failures"]:
        if "SM stalled or delay outside range" in failure["error"]:
            error = "SM stalled or delay outside range"
        else:
            error = failure["error"]
        result.append({"index": failure.get("case_index"), "case": failure["case"], "error_class": error})
    return result


def utc():
    return datetime.now(timezone.utc).isoformat()


def run_one(stage, source, tools, out, image):
    expected = compressed_json(HERE / "records" / f"stage-{stage}.json.gz")
    command = [sys.executable, "-I", "-B", str(source / "screen.py"), str(tools), str(out), "--image", image]
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=420)
    expected_code = int(bool(expected["failures"]))
    if run.returncode != expected_code:
        raise ValueError(f"stage {stage} returned {run.returncode}, expected {expected_code}: {run.stdout[-900:]} {run.stderr[-500:]}")
    measured = json.loads((out / "result.json").read_text("utf-8"))
    for field in COMPARED_FIELDS:
        if measured.get(field) != expected.get(field):
            raise ValueError(f"stage {stage} differs in {field}")
    if failures(measured) != expected["failures"]:
        raise ValueError(f"stage {stage} did not reproduce its original failure classes")
    digest = hashlib.sha256(gzip.decompress((out / "public-rows.bin.gz").read_bytes())).hexdigest()
    if digest != measured["public_rows_sha256"]:
        raise ValueError(f"stage {stage} public row file differs from the manifest")
    return {"stage": stage, "cases": measured["input_case_count"], "met_disposition": len(measured["observations"]),
            "historical_unexpected": len(measured["failures"]), "eight_frame_sequence": len(measured.get("single_sm_resident_sequence", [])),
            "raw_public_rows_sha256": digest, "measured_start_utc": measured["started_utc"], "measured_end_utc": measured["ended_utc"],
            "node": measured["node_version"], "input_file_hashes_match_on_host": measured["inputs_sha256"] == expected["inputs_sha256"],
            "tools_json_hash_matches_on_host": measured["tools_sha256"] == expected["tools_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="fresh output under this checkout's build directory")
    parser.add_argument("--tools", type=Path, help="existing hash-verified PIO tools, otherwise fetched into the output")
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    parser.add_argument("--history", action="store_true", help="also run stages 1-3, including the 104 failing manual-push trials")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "build"):
        raise ValueError("output must be in this checkout's build directory")
    out.mkdir(parents=True, exist_ok=False)
    report = {"started_utc": utc(), "stages": []}
    tools = args.tools.resolve() if args.tools else out / "pio-tools"
    if args.tools is None:
        fetch = ROOT / "evidence/E0049-review-council/panel-a/pio/fetch_pio_tools.py"
        subprocess.run([sys.executable, "-I", "-B", str(fetch), str(tools)], cwd=ROOT, check=True, timeout=140)
    if args.history:
        source_versions = compressed_json(HERE / "records" / "earlier-source.json.gz")
        for stage in ("01", "02", "03"):
            destination = out / ("source-" + stage)
            destination.mkdir()
            for name, contents in source_versions[stage].items():
                if name not in ("screen.py", "spi_program.py", "pio_spi_trace.cjs", "clock_peer.cjs"):
                    raise ValueError("unsupported source member")
                (destination / name).write_bytes(contents.encode("utf-8"))
            for name in DECLARATIONS:
                shutil.copyfile(HERE / name, destination / name)
            report["stages"].append(run_one(stage, destination, tools, out / ("stage-" + stage), args.image))
    report["stages"].append(run_one("04", HERE, tools, out / "stage-04", args.image))
    probe = subprocess.run(["node", str(HERE / "conditional_push_probe.cjs"), str(tools)],
                           text=True, capture_output=True, check=True, timeout=15)
    probe_observed = json.loads(probe.stdout)
    probe_expected = json.loads((HERE / "records/push-probe.json").read_text("utf-8"))
    if probe_observed["observations"] != probe_expected["observations"]:
        raise ValueError("independent manual-PUSH public FIFO probe differs")
    report["normative_probe_observed_levels"] = [row["observed"] for row in probe_observed["observations"]]
    report["finished_utc"] = utc()
    (out / "replay.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
