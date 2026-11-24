"""Fetch the three hash-pinned functional Verilog files needed by the council screens."""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


sys.path.insert(0, str(Path(__file__).resolve().parent))
from selector_orders import PDK_FILES, checked


REVISION = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"
BASE = f"https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{REVISION}/ihp-sg13cmos5l/libs.ref/"
MAX_TOTAL = 4 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new directory for a tiny libs.ref tree")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"choose a new directory: {args.out}")
    files, record = {}, []
    remaining = MAX_TOTAL
    for name, expected in PDK_FILES.items():
        url = BASE + name
        with urlopen(Request(url, headers={"User-Agent":"council-qualification"}), timeout=60) as response:
            raw = response.read(remaining + 1)
        if len(raw) > remaining:
            raise ValueError(f"pinned files exceed {MAX_TOTAL} bytes")
        files[name] = checked(raw, expected, name)
        record.append({"name":name, "bytes":len(raw), "sha256":expected, "url":url})
        remaining -= len(raw)
    args.out.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        dest = args.out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    manifest = {"revision":REVISION, "total_bytes":MAX_TOTAL-remaining, "files":record}
    (args.out / "download.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(files)} PDK models, {manifest['total_bytes']} bytes")


if __name__ == "__main__":
    main()
