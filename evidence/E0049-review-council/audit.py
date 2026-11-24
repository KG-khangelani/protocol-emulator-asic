# SPDX-License-Identifier: Apache-2.0
"""Recompute headline observations and check the committed council manifests and links."""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.production_sram import verify


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def read(path):
    return json.loads(raw(path))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_rows(data):
    return [json.loads(line) for line in data.splitlines()]


def by_name(rows):
    result = {r["name"]: r for r in rows}
    require(len(result) == len(rows), "duplicate case name")
    return result


def manifest_checks():
    names, expected = [], []
    for target in sorted(HERE.rglob("FILES.sha256")):
        for line in target.read_text("utf-8").splitlines():
            sha, name = line.split("  ", 1)
            path = (target.parent / name).resolve()
            require(path.is_relative_to(target.parent), "manifest path escapes its directory")
            names.append("HEAD:" + path.relative_to(ROOT).as_posix())
            expected.append(sha)
    require(names, "missing manifests")
    process = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch"],
                             input=("\n".join(names) + "\n").encode(), capture_output=True, check=True)
    stream = io.BytesIO(process.stdout)
    for name, sha in zip(names, expected):
        header = stream.readline().split()
        require(len(header) == 3 and header[1] == b"blob", "missing committed file " + name)
        data = stream.read(int(header[2]))
        require(digest(data) == sha and stream.read(1) == b"\n", "manifest mismatch " + name)
    require(stream.read() == b"", "extra Git objects")
    return len(names)


def link_checks():
    pages = [*HERE.rglob("*.md"), *(ROOT / "docs/research/council-2026-11-24").glob("*.md")]
    pages += list((ROOT / "docs/reports").glob("2026-11-24-technical-review-council.md"))
    pages += list((ROOT / "docs/decisions").glob("0051-*.md"))
    checked = 0
    for page in pages:
        prose = re.sub(r"(?ms)^ *```.*?^ *```[^\n]*", "", page.read_text("utf-8"))
        for ref in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", prose):
            url = urlsplit(ref.strip("<>"))
            if url.scheme or not url.path:
                continue
            path = (page.parent / unquote(url.path)).resolve()
            require(path.is_relative_to(ROOT) and path.exists(), f"broken local link in {page}: {ref}")
            checked += 1
    return checked


def interface_boundaries():
    original = read(HERE / "onewire/rise/original-results.json.gz")
    counts = Counter((r["image"], r["judgment"]) for r in original["in_envelope"])
    require(counts == {("original", "accepted"): 24, ("original", "missed-presence"): 4,
                       ("original", "missing-sensed-slot"): 4, ("retimed", "accepted"): 24,
                       ("retimed", "missing-sensed-slot"): 8}, "original and retimed remote receiver")
    wider = read(HERE / "onewire/rise/recovery-results.json.gz")
    receiver = wider["in_envelope"]
    require(len(receiver) == 32 and all(r["sensed_slots"] == 17 and r["sampled_writes"] == 16
            and r["received_lsb_first_words_hex"] == "b4cc" and r["judgment"] == "accepted"
            for r in receiver), "wider slots at the remote receiver")
    require({(r["sensed_slots"], r["judgment"]) for r in wider["stress"]} ==
            {(0, "missed-presence"), (9, "missing-sensed-slot")} and len(wider["stress"]) == 2,
            "two distinct wider-slot stress failures")

    selectors = read(HERE / "panel-c/records/selector-orders.json")["sampled"]
    for representation in ("rtl", "g4_netlist"):
        released = selectors[representation]["modes"]["released"]
        orders = released["number_of_orders_by_count_of_read_dwells"]
        require(sum(orders.values()) == 720 and orders["0"] == 360 and
                released["safe_bit7_first_tails"] == 120, "selector order " + representation)

    uart = read(HERE / "panel-a/uart/results.json.gz")
    exact = uart["bounds"]["100"]["max_all_phase_H_plus_L"]
    fast = uart["bounds"]["102"]["max_all_phase_H_plus_L"]
    require((exact, fast) == (4340, 4254) and uart["old_bound_wrong_first_copies"] == 8,
            "UART host-service boundary")
    return {"wider_onewire_accepted": len(receiver), "wider_onewire_stress_rejected": len(wider["stress"]),
            "selector_orders_per_model": sum(orders.values()), "uart_fast_service_clocks": fast}


def observations():
    powered = HERE / "powered-netlist"
    rows = by_name(json_rows(raw(powered / "records.jsonl.gz")))
    archived = ROOT / "evidence/E0047-g4-submission-candidate/program-tools/14094030144.zip"
    with zipfile.ZipFile(archived) as source:
        original = by_name(json_rows(source.read("icarus/records/records.jsonl")))
    require(rows == original and len(rows) == 55, "powered G3 outcomes")
    require(sum(not r["expected_acceptance"] for r in rows.values()) == 15, "G3 rejection count")
    require(sum(r["observations"] for r in rows.values()) == 54522, "G3 observations")

    matrix = raw(powered / "i2c-matrix/cases.jsonl.gz")
    matrix_report = read(powered / "i2c-matrix/result.json")
    require(digest(matrix) == matrix_report["retained_records_sha256"] ==
            "bf9c4b00f4195a7a30dd8e2eb88a5d572b51186df55f4216e7290ca549a6307e", "G4 I2C case bytes")
    i2c = json_rows(matrix)
    require(len(i2c) == 1160 and Counter(r["outcome"] for r in i2c) ==
            {"OK": 1000, "NACK": 6, "TIMEOUT": 154}, "I2C dispositions")
    combined = read(powered / "i2c-matrix/write_read-96.json.gz")
    first_halt = next(r["t"] for r in combined["trace"] if r["state"] == "HALT")
    require(first_halt == 80584 and not combined["record"]["stretches"], "combined transaction timing")

    traces = []
    for sim in ("icarus-netlist", "verilator-rtl"):
        result = read(powered / "cross-release" / sim / "result.json")
        require(result["status"] == "pass", "G5 replay " + sim)
        cases = result["g5"]["compared"]
        require(len(cases) == 20 and sum(not r["accepted"] for r in cases) == 4, "applicable G5 cases")
        require(sum(r["runtime_rows"] for r in cases) == 1262 and
                sum(r["loader_edges"] for r in cases) == 3472, "G5 observation scope")
        traces.append(sorted(cases, key=lambda row: row["name"]))
    require(traces[0] == traces[1], "G5 cross-representation difference")

    uart = HERE / "uart-ablation"
    mapped = read(uart / "mapped.json")["results"]
    for name, result in mapped.items():
        module, = read(uart / f"{name}-stat.json.gz")["modules"].values()
        require(abs(module["area"] - result["total_um2"]) < 0.001, "area total " + name)
        require(abs(module["sequential_area"] - 17293.0464) < 0.001, "sequential area " + name)
    delta = mapped["reference"]["total_um2"] - mapped["ablation"]["total_um2"]
    require(abs(delta - 2130.03) < 0.001, "mapped difference")
    candidate = by_name(json_rows(raw(uart / "candidate-g3.jsonl.gz")))
    require(candidate == {n: r for n, r in original.items() if r["group"] in ("loader", "spi", "i2c")}
            and len(candidate) == 50, "non-UART ablation cases")

    storage = read(HERE / "storage-screen/result.json")
    sizes = list(storage["images"].values())
    require(len(sizes) == 15 and sum(r["original_bytes"] for r in sizes) == 1324 and
            sum(r["dictionary_bytes"] for r in sizes) == 922 and
            sum(r["change_bytes"] < 0 for r in sizes) == 6, "storage denominators")
    pio = read(HERE / "panel-a/pio-spi/records/stage-04.json.gz")
    require(not pio["failures"] and len(pio["single_sm_resident_sequence"]) == 8, "PIO sequence")
    require(len(pio["observations"]) == 536 and sum(bool(c["errors"]) for c in pio["observations"]) == 72,
            "PIO recorded dispositions")
    require(digest(raw(HERE / "panel-a/pio-spi/records/final-public-rows.bin.gz")) ==
            pio["public_rows_sha256"], "PIO pin and FIFO trace")
    phases = read(HERE / "panel-a/pio-target/records/phase.json.gz")
    samples = [dict(zip(phases["columns"], row, strict=True)) for row in phases["rows"]]
    require(len(samples) == 480 and all(not s["errors"] for s in samples), "partial PIO target grid")
    require(max(s["cold_abort_ns"] for s in samples) == 160 and
            sum(s["cold_abort_ns"] == s["post_reselect_abort_ns"] == 160 for s in samples) == 4,
            "worst digital target boundary")
    require(read(HERE / "panel-c/spi-target/records/fresh-replay.json")["miso_abort_ns"] == 1563,
            "SPI target abort counterexample")
    return {"G3_cases": len(rows), "I2C_cases": len(i2c), "G5_cases_each": len(traces[0]),
            "combined_i2c_first_halt_ns": first_halt * 5, "nominal_mapped_delta_um2": round(delta, 2),
            "pio_single_launches": len(pio["observations"]), "single_bit_target_phase_cases": len(samples),
            "dictionary_images": len(sizes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    guard = verify(ROOT)
    require(len(guard["files_sha256"]) == 20, "qualified input count")
    result = {"production_inputs": len(guard["files_sha256"]), "observations": observations(),
              "interface_boundaries": interface_boundaries(),
              "committed_manifest_entries": manifest_checks(), "local_markdown_links": link_checks()}
    formatted = json.dumps(result, indent=2) + "\n"
    if args.output:
        out = args.output.resolve()
        require(out.is_relative_to(ROOT / "build") and not out.exists(), "new build file required")
        out.write_bytes(formatted.encode())
    print(formatted, end="")


if __name__ == "__main__":
    main()
