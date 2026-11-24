"""Execute the v0.1.1 standalone README plus a source-error control."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from powered_host_screen import BUNDLE_SHA, E0048


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root, temp = out/"bundle", out/"temp"
    root.mkdir()
    temp.mkdir()
    blob = args.repo/E0048
    record = {"status":"INCOMPLETE", "started_utc":datetime.now(timezone.utc).isoformat(),
              "bundle_sha256":hashlib.sha256(blob.read_bytes()).hexdigest(), "python":sys.version,
              "host":platform.platform(), "commands":[], "artifacts":{}}
    env = {k:v for k,v in os.environ.items() if k not in ("PYTHONPATH","PYTHONHOME")}
    env.update(PYTHONNOUSERSITE="1",PYTHONDONTWRITEBYTECODE="1",TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))

    def run(argv):
        before = time.perf_counter()
        process = subprocess.run([sys.executable, *argv],cwd=root,env=env,capture_output=True,timeout=90)
        record["commands"].append({"argv":["python",*argv],
                                   "machine_seconds":round(time.perf_counter()-before,4),
                                   "returncode":process.returncode,
                                   "output":(process.stdout+process.stderr).decode(errors="replace").strip()})
        return process.returncode

    try:
        if record["bundle_sha256"] != BUNDLE_SHA or blob.stat().st_size > 1024**2:
            raise ValueError("wrong release or bundle cap exceeded")
        with ZipFile(blob) as source:
            if sum(z.file_size for z in source.infolist()) > 1024**2:
                raise ValueError("expanded cap exceeded")
            for entry in source.infolist():
                name = PurePosixPath(entry.filename)
                if name.is_absolute() or ".." in name.parts or "\\" in entry.filename or ":" in entry.filename:
                    raise ValueError("unexpected path")
                member = root.joinpath(*name.parts)
                member.parent.mkdir(parents=True,exist_ok=True)
                member.write_bytes(source.read(entry))
            for label, output in [("control","my-control"),("timing_fault","my-fault")]:
                if run(["tools/assembler.py",f"experiments/waveform_replay/{label}.asm",
                        "--out",f"build/{output}"]):
                    raise ValueError("documented assembler command failed")
                for artifact in ["program.bin","program.json","program.lst","load-plan.json"]:
                    raw = (root/f"build/{output}/{artifact}").read_bytes()
                    if raw != source.read(f"compiled/{label}/{artifact}"):
                        raise ValueError(f"changed {label}/{artifact}")
                    record["artifacts"][f"{label}/{artifact}"] = hashlib.sha256(raw).hexdigest()
        if run(["-m","unittest","discover","-s","test","-p","test_waveform_replay_oracle.py"]):
            raise ValueError("documented checker command failed")
        (root/"bad.asm").write_bytes(b"# deliberate control\n" + (root/"experiments/waveform_replay/control.asm").read_bytes())
        if not run(["tools/assembler.py","bad.asm","--out","build/bad"]) or (root/"build/bad").exists():
            raise ValueError("malformed program failed to reject cleanly")
        record["status"] = "PASS_STANDALONE_README"
    except Exception as exc:
        record["failure"] = str(exc)
        raise
    finally:
        record["ended_utc"] = datetime.now(timezone.utc).isoformat()
        (out/"results.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(record["status"], len(record["artifacts"]))


if __name__ == "__main__":
    main()
