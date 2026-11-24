# SPDX-License-Identifier: Apache-2.0
"""Reassemble both target attempts and repeat the abort/reselect phase falsifier."""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()


def unpack(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", type=Path, help="PIO tool directory from the council's verified extractor")
    parser.add_argument("out", type=Path)
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    args = parser.parse_args()
    out, tools = args.out.resolve(), args.tools.resolve()
    if not out.is_relative_to(ROOT / "build"):
        raise ValueError("output must stay under build")
    out.mkdir(parents=True, exist_ok=False)
    start = datetime.now(timezone.utc).isoformat()
    historical = unpack(HERE/"records/earlier-source.json.gz")
    report = {"started_utc": start, "attempts": []}
    for number in ("01", "02"):
        src, dest = out/("source-"+number), out/("attempt-"+number)
        src.mkdir()
        for name in ("declaration.md", "recovery.md", "screen.py", "echo.pio", "target_trace.cjs"):
            if name in historical[number]:
                (src/name).write_bytes(historical[number][name].encode())
            else:
                shutil.copyfile(HERE/name, src/name)
        run = subprocess.run([sys.executable, "-I", "-B", str(src/"screen.py"), str(tools), str(dest),
                              "--image", args.image], capture_output=True, text=True, timeout=150)
        if run.returncode != int(number == "01"):
            raise ValueError(f"attempt {number} exit {run.returncode}: {run.stdout[-500:]} {run.stderr[-500:]}")
        path = dest/"result.json"
        observed = json.loads(path.read_bytes())
        expected = unpack(HERE/"records"/("attempt-"+number+".json.gz"))
        for field in ("sources", "images", "observations", "failures", "one_host_transcript", "case_counts"):
            if observed[field] != expected[field]:
                raise ValueError(f"attempt {number} differs in {field}")
        report["attempts"].append({"attempt": number, "cases": len(observed["observations"]),
                                   "expected_historical_failures": len(observed["failures"]),
                                   "start_utc": observed["started_utc"], "end_utc": observed["ended_utc"]})
        # Only compress the newly created raw replay record after these checks.
        (dest/"result.json.gz").write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        path.unlink()
    phase_out = out/"phase"
    subprocess.run([sys.executable,"-I","-B",str(HERE/"phase_stress.py"),str(tools),
                    str(out/"attempt-02/candidate.hex"),str(phase_out)],check=True,timeout=60)
    phase = json.loads((phase_out/"phase.json").read_bytes())
    reference = unpack(HERE/"records/phase.json.gz")
    for field in ("image_sha256_le", "rows", "columns", "case_dispositions", "counterexample"):
        if phase[field] != reference[field]:
            raise ValueError("phase boundary differs in " + field)
    report["phase_cases"] = phase["case_dispositions"]
    report["phase_start_utc"] = phase["start_utc"]
    report["phase_end_utc"] = phase["end_utc"]
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (out/"replay.json").write_text(json.dumps(report,indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
