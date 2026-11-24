"""Re-score the retained pin traces, or compare a fresh execution to them."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "experiments/spi_target"))
from requester import REPLIES, Trace, matrix, score, validate_stimulus


def require(ok, message):
    if not ok:
        raise ValueError(message)


def record(name):
    return json.loads(gzip.decompress((HERE / (name + ".json.gz")).read_bytes()))


def group(name, case):
    frame = case["frames"][0]
    if frame["mode"] == "normal":
        return "valid" if frame["command"] in REPLIES else "invalid"
    return "valid" if frame["mode"] == "uneven" else frame["mode"]


def bounds(values):
    return [min(values), max(values)] if values else None


def summarize(cases, traces):
    require(cases.keys() == traces.keys(), "incomplete case inventory")
    metrics = {}
    for name, case in cases.items():
        result = score(case, traces[name])
        category = group(name, case)
        rows = metrics.setdefault(category, [])
        rows.append((name, result))
    summary = {}
    for category, rows in metrics.items():
        results = [r for _, r in rows]
        errors = Counter(check for r in results for check in {e["check"] for e in r["errors"]})
        releases = [ns for r in results for ns in r["abort_ns"] if ns is not None]
        normal = [ns for r in results for ns in r["normal_release_ns"] if ns is not None]
        setups = [r["min_setup_ns"] for r in results if r["min_setup_ns"] is not None]
        holds = [r["min_hold_ns"] for r in results if r["min_hold_ns"] is not None]
        first = next(((n, r["errors"][0]) for n, r in rows if r["errors"]), None)
        summary[category] = dict(total=len(rows), passed=sum(not r["errors"] for r in results),
                                 completed_correct_reply_bytes=sum(len(r["replies"]) for r in results),
                                 abort_observed=len(releases), abort_by_160ns=sum(ns <= 160 for ns in releases),
                                 observed_abort_range_ns=bounds(releases), normal_release_range_ns=bounds(normal),
                                 minimum_setup_ns=min(setups, default=None), minimum_hold_ns=min(holds, default=None),
                                 failures_per_check=dict(sorted(errors.items())), first_failure=first)
    return summary


def altered_window(rows, lo, hi, transform):
    original = Trace(rows, max(hi, rows[-1][0]) + 1)
    output = []
    for t in sorted(set(original.times + [lo, hi])):
        fields = original.at(t)[1:]
        output.append([t, *(transform(*fields) if lo <= t < hi else fields)])
    return output


def controls(cases, revised, original):
    def reject(name, source, label, lo, hi, edit):
        altered = altered_window(source[name], lo, hi, edit)
        require(label in {e["check"] for e in score(cases[name], altered)["errors"]}, "missed control " + label)
    command = cases["opcode-a5"]["frames"][0]
    edge = command["rises"][-1]
    reject("opcode-a5", revised, "reply_bit", edge - 20, edge + 41,
           lambda oe, m, k, h: (oe, 1 - m, k, h))
    reject("opcode-a5", revised, "prefix_drive", command["select"] + 50, command["select"] + 80,
           lambda oe, m, k, h: (oe | 8, 0, k, h))
    name = "reselect-a5-250-7-0-1"
    abort, fresh = cases[name]["frames"]
    origin = abort["abort"]
    reject(name, revised, "abort_release", origin, origin + 161, lambda oe, m, k, h: (oe | 8, 1, k, h))
    edge = fresh["rises"][8]
    reject(name, revised, "reply_bit", edge - 65, edge + 50, lambda oe, m, k, h: (oe | 8, 1, k, h))
    case = cases["missing_reply"]
    reject("missing_reply", original, "terminal_result", case["frames"][0]["lost_clock"], case["finish"],
           lambda oe, m, k, h: (oe, m, 1 if h else k, h))
    shifted = deepcopy(cases[name])
    event = next(v for v in shifted["events"] if v[0] == origin + 80)
    event[0] += 1
    try:
        validate_stimulus(shifted)
    except ValueError as exc:
        require("fresh frame" in str(exc), "wrong requester control")
    else:
        raise ValueError("accepted late clock return")


def audit(fresh=None):
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for name, wanted in manifest["source_sha256"].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == wanted, "source digest " + name)
    for name, wanted in manifest["retained_sha256"].items():
        require(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == wanted, "retained digest " + name)
    replay = json.loads((HERE / "clean-replay.json").read_bytes())["matched_uncompressed_sha256"]
    require(set(replay) == {"cases.json", "images.json", "original.json", "revised.json", "pio.json",
                            "original-gate.json", "revised-gate.json", "pio-host.json", "target.hex", "revised.asm"},
            "fresh execution receipt inventory")
    for name, wanted in replay.items():
        data = (gzip.decompress((HERE / (name + ".gz")).read_bytes()) if name.endswith(".json")
                else (HERE / name).read_bytes())
        require(hashlib.sha256(data).hexdigest() == wanted, "fresh execution receipt " + name)
    profile = json.loads((ROOT / "tools/production-profile.json").read_bytes())
    for name, wanted in profile["files_sha256"].items():
        for tag in ("v0.1.0", "v0.1.1"):
            require(hashlib.sha256(subprocess.check_output(["git", "show", f"{tag}:{name}"], cwd=ROOT)).hexdigest()
                    == wanted, tag + ": " + name)
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == wanted, "physical input " + name)
    require(len(profile["files_sha256"]) == 20, "physical profile file count")
    for slug, access in json.loads((HERE / "probe-access.json").read_bytes()).items():
        path = HERE.parent / "E0054-separate-oscillators" / access["prior_e0054"] / "result.json.gz"
        prior = json.loads(gzip.decompress(path.read_bytes()))
        require(access["board_identity_sha256"] == prior["board_identity_sha256"] and access["present"]
                and access["reachable"] and access["kind"] == "fpga", "board identity " + slug)
    cases = record("cases")
    require(cases == json.loads(json.dumps(dict(matrix()))) and len(cases) == 736, "stimulus changed")
    names = ("original", "revised", "pio", "original-gate", "revised-gate", "pio-host", "images")
    observed = {name: record(name) for name in names}
    if fresh:
        for name, expected in {"cases": cases, **observed}.items():
            require(json.loads((fresh / (name + ".json")).read_bytes()) == expected, "replay differs: " + name)
        for name in ("target.hex", "revised.asm"):
            require((fresh / name).read_bytes() == (HERE / name).read_bytes(), "assembled or generated image " + name)
    summary = {name: summarize(cases, observed[name]) for name in ("original", "revised", "pio")}
    for key in ("original", "revised"):
        gate = observed[key + "-gate"]
        require(len(gate) == 15 and all(rows == observed[key][name] for name, rows in gate.items()),
                key + " selected G4 netlist and RTL traces differ")
    historic = score(cases["hold-a5-0-1"], observed["original"]["hold-a5-0-1"])
    require(historic["abort_ns"] == [1563], "historical stalled-high control")
    require(len(observed["pio-host"]) == 123 and observed["pio-host"][-1] == ["w", 0x50200000, 1],
            "PIO cold MMIO or launch")
    controls(cases, observed["revised"], observed["original"])
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", type=Path, help="compare the full regenerated run with the archive")
    args = parser.parse_args()
    actual = audit(args.fresh)
    expected = json.loads((HERE / "summary.json").read_bytes())
    require(json.loads(json.dumps(actual)) == expected, "reviewed scoreboard differs")
    print("PASS: 736 schedules on three programs, 30 matching G4 netlist traces, six rejected controls, 20 release inputs")
