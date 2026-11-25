# SPDX-License-Identifier: Apache-2.0
"""Re-score retained public pins, paired bus timings, loader images and execution receipts."""
from collections import Counter
import gzip
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import PANEL, SOURCE, cases, digest, encoded, reference
from tools.assembler import assemble, load_plan, program_bytes
from tools.i2c_oracle import CLEANUP, DEADLINE, OUTCOMES, assess
from tools.production_sram import verify


def require(condition, description):
    if not condition:
        raise ValueError(description)


def firmware():
    original = SOURCE.read_text(encoding="utf-8")
    low = "SET mask=0x01 value=0x00 oe=0x01"
    dwell = "WAIT cycles=260"
    stripped = [line.strip() for line in original.splitlines()]
    require(stripped.count(low) == stripped.count(dwell) == 12, "firmware guard sites")
    images = {0: assemble(original)}
    for clocks in (8, 24, 170, 171):
        lines = []
        for line in original.splitlines():
            if line.strip() == dwell:
                line = f"    WAIT cycles={260 - clocks}"
            lines.append(line)
            if line.strip() == low:
                lines.append(f"    WAIT cycles={clocks - 1}")
        images[clocks] = assemble("\n".join(lines) + "\n")
    return images


def recorded_outcomes(records, traces):
    historic = reference()
    earlier = json.loads((PANEL / "results/retime.json").read_bytes())
    images = firmware()
    expected = list(cases())
    require(len(records) == len(traces) == len(expected) == 347, "case inventory")
    matched = {}
    outcomes = Counter()
    cleanup = Counter()
    controls = {}
    anchored = set()
    loader_lengths = {}
    for record, entry, schedule in zip(records, traces, expected, strict=True):
        name, clocks, intent, stretches, prior = schedule
        label, rows = entry
        require(name == label == record["name"] and record["expectation_matched"], name + " identity")
        require((record["clocks"], record["address"], record["tx"], record["rx"], record["nack"],
                 record["timeout_release"]) == (clocks, intent.address, intent.tx, intent.rx, intent.nack,
                                                intent.timeout_release), name + " request")
        require(record["stretches"] == {str(k): v for k, v in stretches.items()}, name + " stretch")
        trace_sha = digest(encoded(rows))
        require(trace_sha == record["trace_sha256"], name + " raw trace")
        if prior:
            require(trace_sha == historic[prior]["trace_sha256"], name + " E0049 reference")
            anchored.add(prior)
        if name == "plain-0":
            require(trace_sha == earlier["reference_trace_sha256"], "G4 reference")
        image = images[clocks]
        raw = program_bytes(image)
        if clocks:
            require(digest(raw) == earlier["images"][str(clocks)]["binary_sha256"], name + " image")
        key = clocks, intent.address, intent.tx
        if key not in loader_lengths:
            payloads = {"TX0": intent.address << 1, "TX1": intent.tx}
            loader_lengths[key] = len(load_plan(image, payloads=payloads)["steps"])
        require(record["readback_sha256"] == digest(raw) and record["readback_bytes"] == len(raw)
                and record["loader_steps"] == loader_lengths[key], name + " powered loader")
        verdict = assess(rows, intent)
        errors = sorted({e["kind"] for e in verdict["errors"]})
        require(errors == record["oracle_errors"] == (["data_valid_delay"] if clocks == 171 else []),
                name + " independent oracle")
        require(verdict["outcome"] == record["expected_outcome"] == intent.outcome and
                record["terminal_marker"] == ((rows[-1]["out"] >> 2) & 7) == OUTCOMES[intent.outcome],
                name + " terminal outcome")
        outcomes[(clocks, intent.outcome)] += 1
        require(verdict["releases"] == record["releases"] and verdict["halt"] == record["halt_tick"],
                name + " release count or duration")
        if intent.timeout_release:
            releases = [b["t"] for a, b in zip(rows, rows[1:]) if a["oe"] & 1 and not b["oe"] & 1]
            slack = verdict["halt"] - releases[intent.timeout_release - 1] - DEADLINE
            require(0 <= slack <= CLEANUP and slack == record["timeout_cleanup_ticks"], name + " deadline")
            cleanup[slack * 5] += 1
        edges = [(r["t"], r["bus"] & 1) for p, r in zip(rows, rows[1:]) if (p["bus"] ^ r["bus"]) & 1]
        boundaries = [(e["kind"], e["t"]) for e in verdict["events"] if e["kind"] != "BIT"]
        if clocks in (0, 24):
            pair = "plain" if name.startswith("plain-") else name.split("-", 1)[1]
            matched.setdefault(pair, {})[clocks] = (edges, boundaries, verdict["halt"])
        if name.startswith("plain-"):
            fall = None
            changes = []
            for p, r in zip(rows, rows[1:]):
                if p["bus"] & 1 and not r["bus"] & 1:
                    fall = r["t"]
                if not ((p["bus"] | r["bus"]) & 1) and (r["bus"] ^ p["bus"]) & 2:
                    if (p["oe"] ^ r["oe"]) & 2 and not (p["target_oe"] ^ r["target_oe"]) & 2:
                        changes.append(5 * (r["t"] - fall))
            low_changes = record["timing"]["ideal_low_changes"]["controller"]
            require([len(changes), min(changes), max(changes)] ==
                    [low_changes["count"], low_changes["min_ns"], low_changes["max_ns"]], name + " SDA timing")
            require(rows[-1]["rx"] == intent.rx and rows[-1]["rx_valid"] == 1, name + " delivered byte")
            controls[str(clocks)] = [min(changes), max(changes)]
    require(anchored == set(historic) and len(matched) == 172, "historical or paired inventory")
    differences = {"scl_edges": [], "boundaries": [], "halt": []}
    for name, pair in matched.items():
        for field, baseline, guard in zip(differences, pair[0], pair[24], strict=True):
            if baseline != guard:
                differences[field].append(name)
    return {"pairs": len(matched), "paired_differences": differences, "council_traces": len(anchored),
            "cases_per_backend": len(records), "cleanup_ns": {str(ns): count for ns, count in sorted(cleanup.items())},
            "controller_sda_change_ns": controls, "outcomes": {f"{k}/{o}": n for (k, o), n in sorted(outcomes.items())}}


def main():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, section in ((HERE, "files_sha256"), (ROOT, "inputs_sha256")):
        for name, expected in manifest[section].items():
            require(digest((base / name).read_bytes()) == expected, section + " " + name)
    profile = verify(ROOT)
    paths = [*profile["files_sha256"], "info.yaml", "tools/production-profile.json"]
    for tag in ("v0.1.0", "v0.1.1"):
        subprocess.run(["git", "diff", "--quiet", tag, "--", *paths], cwd=ROOT, check=True)
    earlier = json.loads((PANEL / "results/retime.json").read_bytes())["witness"]
    witness = ROOT / "evidence/E0047-g4-submission-candidate/ci-43543626249" / f"{earlier['archive_id']}.zip"
    require(digest(witness.read_bytes()) == earlier["archive_sha256"], "G4 public witness archive")
    with ZipFile(witness) as archive:
        raw = archive.read(earlier["member"])
        require(digest(raw) == earlier["member_sha256"], "G4 public witness member")
        release = json.loads(raw)
    trace_file = HERE / "traces.jsonl.gz"
    case_bytes = gzip.decompress((HERE / "cases.jsonl.gz").read_bytes())
    records = [json.loads(row) for row in case_bytes.splitlines()]
    with gzip.open(trace_file, "rb") as stream:
        traces = [json.loads(row) for row in stream]
    require(traces[0][1] == release["trace"] and firmware()[0]["words"] == release["words"], "G4 released case")
    sys.path.insert(0, str(ROOT / "evidence/E0049-review-council/panel-c"))
    from selector_orders import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES
    require(digest((ROOT / ARCHIVE).read_bytes()) == ARCHIVE_SHA, "G4 submission archive")
    with ZipFile(ROOT / ARCHIVE) as archive:
        require(digest(archive.read("tt_submission/tt_um_khangelani_protocol_emulator.v")) == NETLIST_SHA,
                "submitted functional netlist")
    for backend in ("icarus", "verilator", "netlist"):
        receipt = json.loads((HERE / backend / "result.json").read_bytes())
        require(receipt["status"] == "PASS" and receipt["backend"] == backend and not receipt["smoke"]
                and receipt["cases"] == len(records) and receipt["profile_sha256"] == profile["profile_sha256"],
                backend + " completion")
        require(receipt["case_log_sha256"] == digest(case_bytes) and
                receipt["traces_sha256"] == digest(trace_file.read_bytes()), backend + " canonical output")
        if backend == "netlist":
            require(receipt["netlist_sha256"] == NETLIST_SHA and receipt["cell_models"] == PDK_FILES,
                    "netlist and three pinned PDK models")
        test = ET.parse(HERE / backend / "results.xml").findall(".//testcase")
        require(len(test) == 1 and test[0].get("name") == "compare_guards" and not list(test[0]), backend + " xUnit")
    result = recorded_outcomes(records, traces)
    require(encoded(result) == encoded(manifest["measurements"]), "retained measurements")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
