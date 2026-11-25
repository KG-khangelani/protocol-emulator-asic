"""Reassemble both firmware images and score their archived public-pin observations."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "experiments/spi_target/watchdog"
sys.path[:0] = [str(WORK), str(WORK.parent), str(ROOT)]
from controls import MUTATIONS
from requester import REPLIES
from stress import assess, edge_ties, extra_cases
from verify import baseline
from run import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES
from tools.assembler import assemble, load_plan, program_bytes
from tools.production_sram import verify


def check(ok, why):
    if not ok:
        raise ValueError(why)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(revision, path):
    return subprocess.check_output(["git", "show", revision + ":" + path], cwd=ROOT)


def measure(cases, traces):
    check(cases.keys() == traces.keys(), "case coverage")
    groups = defaultdict(list)
    widths = defaultdict(Counter)
    for name, case in cases.items():
        result = assess(name, case, traces[name])
        check(not result["errors"], f"{name}: {result['errors']}")
        frame = case["frames"][0]
        family = frame["mode"]
        if name.startswith(("edge-", "varied-", "boundary-")):
            family = name.split("-")[0]
        elif family == "normal":
            family = "valid" if frame["command"] in REPLIES else "invalid"
        elif family == "uneven":
            family = "valid"
        groups[family].append(result)
        if family == "boundary":
            widths[str(case["stretch"]["width"])][result["boundary_outcome"]] += 1

    def span(items):
        return [min(items), max(items)] if items else None

    metrics = {}
    for family, records in groups.items():
        releases = [n for r in records for n in r["abort_ns"] if n is not None]
        finishes = [n for r in records for n in r["normal_release_ns"] if n is not None]
        metrics[family] = dict(cases=len(records), correct_completed_replies=sum(len(r["replies"]) for r in records),
                               abort_ns=span(releases), normal_release_ns=span(finishes),
                               timeout_ns=span([r["timeout_ns"] for r in records if "timeout_ns" in r]),
                               min_setup_ns=min((r["min_setup_ns"] for r in records if r["min_setup_ns"] is not None),
                                                default=None),
                               min_hold_ns=min((r["min_hold_ns"] for r in records if r["min_hold_ns"] is not None),
                                               default=None))
    return {"groups": metrics, "watchdog_by_half_cycle_ns": dict(widths)}


def check_program(source, binary):
    image = assemble(source)
    check(program_bytes(image) == binary, "recorded program differs from assembly")
    words = list(struct.unpack(f"<{len(binary) // 4}I", binary))
    check(len(words) <= 128, "program exceeds capacity")
    waits = [pc for pc, word in enumerate(words) if word == 0x62000020]
    check(len(waits) == 18, "expected two counted waits in each of nine reply blocks")
    for pc in waits:
        cs_check, sck_check = words[pc + 1:pc + 3]
        check(cs_check == 0xD1000000, "loop must branch to released entry on CS")
        check(sck_check >> 27 == 0x18 and sck_check & 0x0100FFFF == 0x01000000,
              "loop must branch on synchronized SCK")
    response = words[image["labels"]["reply_a"]:]
    pin_reads = [(w >> 27) & 7 for w in response if w >> 30 == 3]
    check(set(pin_reads) == {0, 2, 3} and pin_reads.count(3) == 3, "unexpected reply input or missing self-read")
    return image


def check_controls(original, cases, raw):
    check(raw.keys() == MUTATIONS.keys(), "mutation inventory")
    for name, (old, new, count, trial, reason) in MUTATIONS.items():
        record = raw[name]
        check(original.count(old) == count, name + " source match")
        changed = assemble(original.replace(old, new))
        check(changed["binary_sha256"] == record["image_sha256"], name + " changed image")
        errors = assess(trial, cases[trial], record["pins"])["errors"]
        check(record["trial"] == trial and record["required_rejection"] == reason and errors == record["errors"]
              and reason in {e["check"] for e in errors}, name + " rejection")


def check_edge_offsets(trials, stress):
    for name, case in trials.items():
        prefix, phase, _ = name.rsplit("-", 2)
        offset = int(phase) - 19
        # In the parent sweep CS changes at 10 + 20*n ns, on a rising core edge.
        nominal = stress[prefix + "-19-1"]
        check(nominal["frames"][0]["abort"] % 20 == 10, name + " nominal clock edge")
        shifted = [[t + offset if t else 0, v] for t, v in nominal["events"]]
        check(case["events"] == shifted and case["finish"] == nominal["finish"] + offset,
              name + " shifted stimulus")


def check_recovery_windows(cases, traces, groups):
    """Check the two acceptance gates directly from constant-state pin intervals."""
    releases, timeouts = [], []
    for name, case in cases.items():
        first = case["frames"][0]
        rows = traces[name]
        if first["mode"] == "pause":
            halted = [row for row in rows if row[4]]
            check(halted and all(row[1:] == [0x30, 0, 3, 1] for row in rows if row[0] >= halted[0][0]),
                  name + " stable, released timeout")
            delay = halted[0][0] - first["lost_clock"]
            check(0 <= delay <= 2000, name + " selected-clock deadline")
            timeouts.append(delay)
        elif first["mode"] == "reselect":
            abort, fresh = first["abort"], case["frames"][1]
            spans = list(zip(rows, [row[0] for row in rows[1:]] + [case["finish"] + 1]))
            check(any(row[0] <= abort - 1 < end and row[1] & 8 for row, end in spans), name + " active abort")
            release = next(row[0] for row in rows if row[0] >= abort and row[1] & 8 == 0)
            check(release <= fresh["select"] == abort + 160, name + " handoff deadline")
            check(all(row[1] & 8 == 0 for row, end in spans if row[0] < fresh["falls"][7] and end > release),
                  name + " quiet handoff and fresh command")
            expected = {0xA4: 0x3C, 0xA5: 0xA7}[fresh["command"]]
            check(fresh["command"] == first["command"] ^ 1 and len(fresh["rises"][8:]) == 8, name + " fresh byte")
            for bit, rise in enumerate(fresh["rises"][8:]):
                level = (expected >> (7 - bit)) & 1
                check(all(row[1] & 8 and row[2] == level for row, end in spans
                          if row[0] < rise + 40 and end > rise - 60), name + " driven sample window")
            releases.append(release - abort)
    check(len(releases) == 384 and [min(releases), max(releases)] == groups["reselect"]["abort_ns"],
          "abort interval cross-check")
    check(len(timeouts) == 32 and [min(timeouts), max(timeouts)] == groups["pause"]["timeout_ns"],
          "timeout interval cross-check")


def audit(compare=None, suite="baseline"):
    provenance = read(HERE / "manifest.json")
    for name, expected in provenance["source_sha256"].items():
        check(sha((ROOT / name).read_bytes()) == expected, "source " + name)
    for name, expected in provenance["retained_sha256"].items():
        check(sha((HERE / name).read_bytes()) == expected, "archive " + name)
    production = verify(ROOT)
    check(production["profile_sha256"] == provenance["production_profile_sha256"], "physical profile")
    for tag in ("v0.1.0", "v0.1.1"):
        for name, expected in production["files_sha256"].items():
            check(sha(blob(tag, name)) == expected, tag + " physical input " + name)
    check(blob("v0.1.0", "tools/assembler.py") == (ROOT / "tools/assembler.py").read_bytes(), "release assembler")
    check(provenance["netlist_archive"] == ARCHIVE and
          sha((ROOT / ARCHIVE).read_bytes()) == provenance["netlist_archive_sha256"] == ARCHIVE_SHA and
          provenance["pdk_sha256"] == PDK_FILES, "gate inputs")
    with ZipFile(ROOT / ARCHIVE) as archive:
        netlist = archive.read("tt_submission/tt_um_khangelani_protocol_emulator.v")
    check(sha(netlist) == provenance["netlist_sha256"] == NETLIST_SHA, "submitted netlist")
    cases = {"baseline": baseline(), "stress": read(HERE / "stress-cases.json.gz"),
             "ties": json.loads(json.dumps(dict(edge_ties())))}
    check(json.loads(json.dumps(dict(extra_cases()))) == cases["stress"] and
          (len(cases["baseline"]), len(cases["stress"])) == (736, 1952), "requester schedules")
    check(len(cases["ties"]) == 42, "phase-neighbor schedules")
    check_edge_offsets(cases["ties"], cases["stress"])
    runs = read(HERE / "runs.json")
    expected_summary = read(HERE / "measurements.json")
    scored = {}
    traces_by_run = defaultdict(dict)
    path = "experiments/spi_target/watchdog/target.asm"
    for variant, spec in provenance["firmware"].items():
        source = blob(spec["revision"], path).decode()
        binary = (HERE / spec["binary"]).read_bytes()
        image = check_program(source, binary)
        check(image["binary_sha256"] == spec["binary_sha256"] and len(image["words"]) == spec["words"], variant)
        check(image["warnings"] == spec["assembler_warnings"], variant + " assembler diagnostics")
        steps = load_plan(image)["steps"]
        actions = dict(Counter(s["action"] for s in steps))
        check(actions["write_byte"] == actions["read_byte_after_edge"] == len(binary), "full program readback")
        if variant == "selected":
            check((ROOT / path).read_bytes() == source.encode(), "active firmware")
            check_controls(source, cases["baseline"], read(HERE / "controls.json.gz"))
        for run in (r for r in runs if r["variant"] == variant):
            dataset, backend, report = run["suite"], run["report"]["backend"], run["report"]
            stored = HERE / run["pins"]
            receipt = report["image"]
            check(receipt["words"] == spec["words"] and receipt["bytes"] == len(binary) and
                  receipt["clocked_load_steps"] == len(steps) and receipt["step_counts"] == actions and
                  receipt["payloads"] == image["payloads"], "cold-load receipt")
            check(report["failures"] == 0 and report["case_count"] == len(cases[dataset]) and
                  report["image"]["binary_sha256"] == spec["binary_sha256"] and report["source_sha256"] == sha(source.encode())
                  and report["assembler_sha256"] == sha((ROOT / "tools/assembler.py").read_bytes())
                  and report["production_profile_sha256"] == production["profile_sha256"], "run receipt " + run["pins"])
            key = (dataset, sha(stored.read_bytes()))
            if key not in scored:
                traces = read(stored)
                scored[key] = measure(cases[dataset], traces)
                if dataset == "baseline":
                    check_recovery_windows(cases[dataset], traces, scored[key]["groups"])
            check(scored[key] == expected_summary[variant][dataset][backend], "pin metrics " + run["pins"])
            entries = traces_by_run[(variant, dataset)]
            check(backend not in entries, "duplicate trial receipt")
            entries[backend] = stored
    for (variant, dataset), backends in traces_by_run.items():
        expected = {"production-rtl", "submitted-netlist"}
        if variant == "selected":
            expected.add("verilator-rtl")
        check(set(backends) == expected, "missing backend " + variant + "/" + dataset)
        rtl = read(backends["production-rtl"])
        for backend, stored in backends.items():
            if backend == "production-rtl":
                continue
            other = read(stored)
            different = [name for name, pins in rtl.items() if pins != other[name]]
            check(different == provenance["trace_differences"].get(f"{variant}/{dataset}/{backend}", []),
                  "cross-backend pin comparison")
            if dataset == "ties":
                check(all(name.endswith("-19-1") for name in different), "different trace away from a clock tie")
    expected = {("initial", s) for s in ("baseline", "stress")} | {("selected", s) for s in cases}
    check(set(traces_by_run) == expected and len(runs) == 13, "complete trial matrix")
    initial = expected_summary["initial"]["stress"]["production-rtl"]["groups"]["edge"]
    check(initial["abort_ns"][1] == 160, "original zero-margin observation")
    for measurements in expected_summary["selected"]["stress"].values():
        check(measurements["groups"]["edge"]["abort_ns"][1] <= 140, "D58 selection margin")
    historical = ROOT / "evidence/E0055-spi-target-comparison"
    baseline_groups = expected_summary["selected"]["baseline"]["production-rtl"]["groups"]
    for name, failure in (("original", "reselect-a4-250-1-0-0 handoff deadline"),
                          ("revised", "pause-a4-0-0 stable, released timeout")):
        try:
            check_recovery_windows(cases["baseline"], read(historical / (name + ".json.gz")), baseline_groups)
        except ValueError as error:
            check(str(error) == failure, "unexpected historical failure " + name)
        else:
            raise ValueError("historical counterexample passed " + name)
    if compare:
        if (compare / "controls.json.gz").is_file():
            check(read(compare / "controls.json.gz") == read(HERE / "controls.json.gz"), "fresh mutation run")
        else:
            result = read(compare / "result.json")
            source = next(r for r in runs if r["variant"] == "selected" and r["suite"] == suite and
                          r["report"]["backend"] == result["backend"])
            for field in ("case_count", "failures", "image", "source_sha256", "assembler_sha256", "production_profile_sha256"):
                check(result[field] == source["report"][field], "fresh " + field)
            check(read(compare / "pins.json.gz") == read(HERE / source["pins"]), "fresh pin traces")
    print("PASS: both firmware images, 736 baseline, 1,952 stress and 42 phase-neighbor schedules, "
          "six firmware mutations and both release profiles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", type=Path, help="compare a freshly executed selected-firmware run")
    parser.add_argument("--suite", choices=("baseline", "stress", "ties"), default="baseline")
    args = parser.parse_args()
    audit(args.compare, args.suite)
