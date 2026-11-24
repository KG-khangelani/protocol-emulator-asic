# SPDX-License-Identifier: Apache-2.0
"""Stream the two original G4 archive sets and the G5 CI artifact against their indexes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path.cwd().resolve()
G4 = ROOT / "evidence/E0047-g4-submission-candidate"
G5 = ROOT / "evidence/E0048-waveform-replay/ci-66743b6"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def file_digest(stream):
    h = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        h.update(block)
    return h.hexdigest()


def inspect(directory, g5=False):
    metadata = read(directory / "artifacts.json")["artifacts"]
    index = read(directory / "zip-files.json")
    kept = sorted(directory.glob("*.zip"))
    check(len(kept) == (1 if g5 else 6), "archive-set count")
    records = []
    for path in kept:
        item = next(a for a in metadata if a["id"] == int(path.stem))
        with path.open("rb") as stream:
            digest = file_digest(stream)
        check(item["size_in_bytes"] == path.stat().st_size and item["digest"] == "sha256:" + digest,
              "ZIP source identity " + path.name)
        expected = index if g5 else index[item["name"]]
        with zipfile.ZipFile(path) as archive:
            members = [entry for entry in archive.infolist() if not entry.is_dir()]
            check(len(members) == len(expected) and {m.filename for m in members} == set(expected),
                  "unexpected, missing or duplicate members " + path.name)
            size = 0
            for entry in members:
                ref = expected[entry.filename]
                if g5:
                    check(ref["bytes"] == entry.file_size, entry.filename)
                    ref = ref["sha256"]
                with archive.open(entry) as member:
                    check(file_digest(member) == ref, entry.filename)
                size += entry.file_size
        records.append({"id": item["id"], "name": item["name"], "zip_sha256": digest,
                        "checked_members": len(members), "uncompressed_bytes": size})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    out = parser.parse_args().out.resolve()
    check(out.is_relative_to(ROOT / "build") and not out.exists(), "new file under build required")
    start = datetime.now(timezone.utc).isoformat()
    runs = {str(r): inspect(G4 / f"ci-{r}") for r in (43543626249, 43543629839)}
    runs["g5"] = inspect(G5, g5=True)
    entries = [record for records in runs.values() for record in records]
    result = {"started_utc": start, "ended_utc": datetime.now(timezone.utc).isoformat(),
              "runs": runs, "archives": len(entries), "checked_member_instances": sum(i["checked_members"] for i in entries),
              "uncompressed_bytes": sum(e["uncompressed_bytes"] for e in entries)}
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["archives"], "archives,", result["checked_member_instances"], "member instances")


if __name__ == "__main__":
    main()
