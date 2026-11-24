# SPDX-License-Identifier: Apache-2.0
"""Analyze the E0018/19 two-frame UART sampling and service contracts."""
import argparse
import gzip
import hashlib
import json
import math
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


P = 434
RATES = range(98, 103)
QUALIFIED = "evidence/E0042-sram-prefetch-screen"
GROUP = "programs/od128-sram-v1/examples.json"
FIELDS = ("rate_percent", "phase_quarters", "capture1", "capture2", "halt",
          "old_first_copy", "safe_first_copy", "one_edge_weaker_copy", "old_terminal_copy")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_bounds(rate):
    period = Fraction(100 * P, rate)
    # Raw sample t_k = ceil(s) + (k+1/2)P. Delta = ceil(s)-s is in [0,1).
    left = min((k + Fraction(1, 2)) * P - k * period for k in range(10))
    right = min((k + 1) * period - (k + Fraction(1, 2)) * P - 1 for k in range(10))
    min_gap, max_gap = math.floor(10 * period), math.ceil(10 * period)
    rearm = 19 * P // 2 + 1
    check(left >= 0 and right >= 0, "cell sample bounds failed")
    check(rearm <= min_gap and max_gap <= rearm + 2 * P, "re-arm window missed")
    return {
        "transmitter_period_core_clocks": str(period),
        "earliest_sample_margin_clocks": str(left),
        "latest_sample_margin_infimum_clocks": str(right),
        "raw_capture_gap_min": min_gap,
        "raw_capture_gap_max": max_gap,
        "next_start_wait_dispatch_from_previous_detection": rearm,
        "max_all_phase_H_plus_L": min_gap,
    }


def expected(rate, phase, record):
    period = Fraction(100 * P, rate)
    start = 4 + Fraction(phase, 4)
    detect1 = math.ceil(start) + 2
    detect2 = math.ceil(start + 10 * period) + 2
    first = detect1 + 17 * P // 2
    second = detect2 + 17 * P // 2
    gap = second - first
    min_gap = record["raw_capture_gap_min"]
    # A negative poll one edge before C1 gives d=H-1, then L=2 more edges.
    def observed_copy(service_sum):
        return 0x55 if service_sum - 1 < gap else 0xaa
    return dict(zip(FIELDS, (rate, phase, first, second, detect2 + 19 * P // 2 + 1,
                             observed_copy(4340), observed_copy(min_gap),
                             observed_copy(min_gap + 1), 0xaa), strict=True))


def prepare(root, out):
    profile = json.loads((root / "tools/production-profile.json").read_bytes())
    candidate = json.loads((root / QUALIFIED / "candidate.json").read_bytes())
    for name, h in candidate["source_sha256"].items():
        check(digest((root / "src" / name).read_bytes()) == h, f"RTL mismatch {name}")
    for name, h in profile["model_sha256"].items():
        path = root / QUALIFIED / "feasibility/verilog" / (name + ".gz")
        data = gzip.decompress(path.read_bytes())
        check(digest(data) == h, f"SRAM model mismatch {name}")
        (out / name).write_bytes(data)
    catalog = json.loads((root / GROUP).read_bytes())
    program = next(p for p in catalog["examples"] if p["name"] == "uart_rx")
    binary = b"".join(int(w, 16).to_bytes(4, "little") for w in program["expected_words"])
    check(len(binary) == 32 and digest(binary) == program["binary_sha256"], "RX image mismatch")
    (out / "program.hex").write_text("".join(f"{b:02x}\n" for b in binary), encoding="ascii")
    tb = Path(__file__).with_name("uart_period_tb.sv")
    shutil.copyfile(tb, out / tb.name)
    return {
        "rtl_sha256": candidate["source_sha256"], "model_sha256": profile["model_sha256"],
        "program_sha256": digest(binary), "bench_sha256": digest(tb.read_bytes()),
        "calculation_sha256": digest(Path(__file__).read_bytes()),
    }


def simulate(root, out, image_name, prepared):
    def run_logged(label, command):
        done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=150, check=False)
        (out / (label + ".log")).write_bytes(done.stdout)
        check(done.returncode == 0, f"{label} failed; see {label}.log")
        return done.stdout.decode("utf-8", errors="replace")

    identity = run_logged("inspect", ["docker", "image", "inspect", image_name,
                                      "--format", "{{.Id}}"]).strip()
    prefix = ["docker", "run", "--pull=never", "--rm", "--read-only", "--network", "none",
              "--env", "TMPDIR=/work", "--mount", f"type=bind,source={root},target=/repo,readonly",
              "--mount", f"type=bind,source={out},target=/work", "--workdir", "/work", identity]
    version = run_logged("tool-version", [*prefix, "iverilog", "-V"]).splitlines()[0]
    sources = ["/repo/src/" + name for name in prepared["rtl_sha256"]]
    run_logged("build", [*prefix, "iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS",
                         "-s", "uart_period_tb", "-o", "uart.vvp", "uart_period_tb.sv",
                         *sources, *prepared["model_sha256"]])
    raw = run_logged("run", [*prefix, "vvp", "uart.vvp"])
    results = []
    for line in raw.splitlines():
        if line.startswith("RESULT "):
            results.append(dict(zip(FIELDS, map(int, line.split()[1:]), strict=True)))
    return identity, version, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True,
                        help="a new isolated output directory")
    parser.add_argument("--image", help="optional local Docker image with Icarus")
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    bounds = {rate: exact_bounds(rate) for rate in RATES}
    predictions = [expected(rate, phase, bounds[rate]) for rate in RATES for phase in range(4)]
    baseline = next(row for row in predictions if row["rate_percent"] == 100
                    and row["phase_quarters"] == 1)
    check([baseline[k] for k in ("capture1", "capture2", "halt")] == [3696, 8036, 8471],
          "nominal E0019 table mismatch")
    check(all(r["safe_first_copy"] == 0x55 for r in predictions), "proposed bound failed")
    check(any(r["one_edge_weaker_copy"] == 0xaa for r in predictions), "missing tightness witness")
    check(any(r["rate_percent"] > 100 and r["old_first_copy"] == 0xaa for r in predictions),
          "faster transmitter did not expose old deadline")
    summary = {"scope": "constant-rate ideal 8N1 TX and continuous receiver enable",
               "receiver_period_clocks": P, "bounds": bounds, "predictions": predictions}
    if args.image:
        prepared = prepare(root, out)
        identity, version, observed = simulate(root, out, args.image, prepared)
        (out / "observations.json").write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
        check(observed == predictions, "RTL and predicted cases differ; retained observations.json")
        summary.update(inputs=prepared, image_id=identity, simulator=version,
                       observed_cases=len(observed),
                       old_bound_wrong_first_copies=sum(r["old_first_copy"] == 0xaa for r in observed))
    (out / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Five exact rate calculations and {len(predictions)} case predictions passed.")
    if args.image:
        print(f"{len(observed)} public RTL cases matched predictions using {version}.")
        print(f"The old bound read byte two in place of byte one in {summary['old_bound_wrong_first_copies']} cases.")


if __name__ == "__main__":
    main()
