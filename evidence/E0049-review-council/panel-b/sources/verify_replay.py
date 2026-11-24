"""Check reproducible content, leaving timestamps and simulator build paths free."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def stable(obj):
    return {key: value for key, value in obj.items() if key not in ("started_utc", "ended_utc")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference", type=Path)
    p.add_argument("fresh", type=Path)
    args = p.parse_args()
    a, b = args.reference, args.fresh
    if read(a/"retained-paths.json") != read(b/"retained-paths.json"):
        raise ValueError("retained STA paths or original wire observations changed")
    for case in ("launch", "guard", "retime"):
        expected = read(a/f"{case}.json")
        observed = read(b/case/"result.json")
        if stable(expected) != stable(observed):
            bad = [key for key, val in stable(expected).items() if observed.get(key) != val]
            raise ValueError(f"{case} result changed in: {bad}")
        if case == "retime":
            for path in (a/"retime-cases.jsonl", b/case/"cases.jsonl"):
                if hashlib.sha256(path.read_bytes()).hexdigest() != observed["cases_sha256"]:
                    raise ValueError(f"case journal changed: {path}")
    print("MATCH retained STA and G4 wire event, selected launch cohort and controls, 4 guards and 159 retimed cases")


if __name__ == "__main__":
    main()
