# SPDX-License-Identifier: Apache-2.0
"""Reproduce the architecture panel screens from the checkout and a new build directory."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def cmd_result(command, cwd, log):
    proc = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=600)
    log.write_bytes(proc.stdout)
    print(proc.stdout.decode("utf-8", errors="replace").strip(), flush=True)
    proc.check_returncode()


def compare(actual, reference, fields=None):
    if fields is None:
        fields = reference.keys()
    missing = [key for key in fields if actual.get(key) != reference[key]]
    if missing:
        raise ValueError("different retained field(s): " + ", ".join(missing))
    return list(fields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    parser.add_argument("--sources", action="store_true", help="refetch the pinned primary source texts")
    parser.add_argument("--pio-tools", type=Path, help="reuse previously extracted pinned PIO tools")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "build") or not (ROOT / "tools/production-profile.json").is_file():
        raise ValueError("run from the repository root with an output directory under build/")
    out.mkdir(parents=True, exist_ok=False)
    started = stamp()
    python = [sys.executable, "-I", "-B"]
    image = subprocess.check_output(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"],
                                    text=True).strip()
    for group, script in (("uart", "check_uart_period.py"), ("spi", "check_spi_sampling.py")):
        cmd_result([*python, str(HERE / group / script), "--root", str(ROOT),
                    "--out", str(out / group), "--image", image], ROOT, out / (group + ".log"))

    # The fixed runner calls generic Yosys and the zero-delay chair fixture inside
    # the already available image. Only the fresh output directory is writable.
    mapped_out = "/repo/" + out.relative_to(ROOT).as_posix()
    mapped_src = "/repo/" + (HERE / "fixed/check_fixed.py").relative_to(ROOT).as_posix()
    cmd_result(["docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
                "--mount", f"type=bind,source={ROOT},target=/repo,readonly",
                "--mount", f"type=bind,source={out},target={mapped_out}", "-w", "/repo", image,
                "python3", "-B", mapped_src, mapped_out + "/fixed"], ROOT, out / "fixed.log")
    if args.pio_tools:
        pio_tools = args.pio_tools.resolve()
    else:
        pio_tools = out / "pio-tools"
        cmd_result([*python, str(HERE / "pio/fetch_pio_tools.py"), str(pio_tools)], ROOT, out / "pio-tools.log")
    cmd_result([*python, str(HERE / "pio/check_pio.py"), str(pio_tools), str(out / "pio"),
                "--image", image], ROOT, out / "pio.log")
    extra = []
    if args.sources:
        cmd_result([*python, str(HERE / "sources/read_sources.py"), str(out / "source-record.json")],
                   ROOT, out / "sources.log")
        compare(read_json(out / "source-record.json"), read_json(HERE / "sources/source-record.json"))
        extra.append("pinned source fingerprints, PIO counts and I2C host accounting")

    checked = {}
    baseline_environments = {}
    for group in ("uart", "spi"):
        actual = read_json(out / group / "results.json")
        reference = read_json(HERE / group / "results.json.gz")
        checked[group] = compare(actual, reference, [key for key in reference if key not in {"image_id", "simulator"}])
        baseline_environments[group] = {"same_image": actual["image_id"] == reference["image_id"],
                                        "original_simulator": reference["simulator"],
                                        "new_simulator": actual["simulator"]}
    checked["fixed"] = compare(read_json(out / "fixed/result.json"), read_json(HERE / "fixed/results.json.gz"),
                               ("cases", "unmet", "host", "fixed_generic_stat", "generic_synthesis_command",
                                "fixed_attempt_inputs_sha256"))
    checked["pio"] = compare(read_json(out / "pio/result.json"), read_json(HERE / "pio/results.json.gz"),
                             ("cases", "unmet", "images", "input_sha256", "public_mmio_operation_counts",
                              "corrupt_write", "assembler_archive", "emulator_archive"))
    compare(read_json(pio_tools / "tools.json"), read_json(HERE / "pio/tool-identities.json.gz"))
    if read_json(out / "pio/host-operations.json") != read_json(HERE / "pio/host-operations.json.gz"):
        raise ValueError("PIO public host transcript differs")
    for name in ("normal.hex", "short-reset.hex"):
        if (out / "pio" / name).read_bytes() != (HERE / "pio" / name).read_bytes():
            raise ValueError("PIO assembled words differ: " + name)
    record = {"start_utc": started, "end_utc": stamp(), "docker_image_id": image,
              "checked": checked, "pio_tool_members_checked": True,
              "pio_cold_host_operations_checked": True, "pio_hex_images_checked": 2,
              "pio_dependency_fetch": "existing" if args.pio_tools else "fresh",
              "extra": extra, "environment_comparison": baseline_environments,
              "spi_raw_sha256": hashlib.sha256((out / "spi/observed.txt").read_bytes()).hexdigest()}
    (out / "replay.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("All four screens reproduced their retained controls and case records.", flush=True)


if __name__ == "__main__":
    main()
