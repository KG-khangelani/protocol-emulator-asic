"""Turn the M0 VCD waveform into a small, evidence-bounded learning table."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VCD = ROOT / "build" / "m0-learning.vcd"
SIGNALS = ("clk", "rst_n", "ena", "uo_out", "uio_out", "uio_oe")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def parse_timescale(lines: list[str]) -> tuple[int, str]:
    for index, line in enumerate(lines):
        if line.strip().startswith("$timescale"):
            block = line.strip()
            cursor = index + 1
            while "$end" not in block and cursor < len(lines):
                block += " " + lines[cursor].strip()
                cursor += 1
            match = re.search(r"\$timescale\s+(\d+)\s*(fs|ps|ns|us|ms|s)\s+\$end", block)
            require(match is not None, "could not parse VCD timescale")
            return int(match.group(1)), match.group(2)
    raise SystemExit("FAIL: VCD has no timescale")


def ticks_to_ns(ticks: int, timescale: tuple[int, str]) -> float:
    multiplier, unit = timescale
    unit_in_ns = {
        "fs": 1e-6,
        "ps": 1e-3,
        "ns": 1.0,
        "us": 1e3,
        "ms": 1e6,
        "s": 1e9,
    }[unit]
    return ticks * multiplier * unit_in_ns


def parse_vcd(path: Path) -> tuple[list[dict], tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    timescale = parse_timescale(lines)
    scope: list[str] = []
    signal_ids: dict[str, str] = {}
    enddefinitions = 0

    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        tokens = line.split()
        if line.startswith("$scope"):
            scope.append(tokens[2])
        elif line.startswith("$upscope"):
            require(bool(scope), "unbalanced VCD scope")
            scope.pop()
        elif line.startswith("$var") and scope == ["tb"]:
            require(len(tokens) >= 6, "malformed VCD variable declaration")
            identifier = tokens[3]
            reference = tokens[4]
            if reference in SIGNALS:
                signal_ids[reference] = identifier
        elif line.startswith("$enddefinitions"):
            enddefinitions = index + 1
            break

    require(enddefinitions > 0, "VCD definitions do not terminate")
    require(set(signal_ids) == set(SIGNALS), f"missing top-level VCD signals: {set(SIGNALS) - set(signal_ids)}")
    id_to_signal = {identifier: signal for signal, identifier in signal_ids.items()}
    values: dict[str, str] = {}
    snapshots: list[dict] = []
    current_time: int | None = None
    changes: list[tuple[str, str]] = []

    def finish_group() -> None:
        if current_time is None:
            return
        old_clk = values.get("clk")
        for identifier, value in changes:
            signal = id_to_signal.get(identifier)
            if signal is not None:
                values[signal] = value.lower()
        if old_clk == "0" and values.get("clk") == "1":
            snapshots.append({"ticks": current_time, **values})

    for raw_line in lines[enddefinitions:]:
        line = raw_line.strip()
        if not line or line.startswith("$"):
            continue
        if line.startswith("#"):
            finish_group()
            current_time = int(line[1:])
            changes = []
        elif line[0].lower() == "b":
            value, identifier = line[1:].split(maxsplit=1)
            changes.append((identifier, value))
        elif line[0].lower() in "01xz":
            changes.append((line[1:], line[0]))
    finish_group()

    require(bool(snapshots), "VCD contains no rising clock edges")
    return snapshots, timescale


def binary_value(snapshot: dict, signal: str) -> int | None:
    value = snapshot.get(signal, "x")
    if any(bit in value for bit in "xz"):
        return None
    return int(value, 2)


def validate_transitions(snapshots: list[dict]) -> None:
    previous: int | None = None
    for edge, snapshot in enumerate(snapshots, start=1):
        output = binary_value(snapshot, "uo_out")
        output_enable = binary_value(snapshot, "uio_oe")
        unused_output = binary_value(snapshot, "uio_out")
        require(output is not None, f"unknown output at rising edge {edge}")
        require(output_enable == 0, f"bidirectional output-enable changed at rising edge {edge}")
        require(unused_output == 0, f"unused bidirectional output changed at rising edge {edge}")
        reset_n = snapshot["rst_n"]
        enable = snapshot["ena"]
        if reset_n == "0":
            expected = 0
        elif previous is not None and enable == "1":
            expected = (previous + 1) & 0xFF
        elif previous is not None and enable == "0":
            expected = previous
        else:
            raise SystemExit(f"FAIL: unknown control value at rising edge {edge}")
        require(
            output == expected,
            f"counter transition mismatch at rising edge {edge}: expected {expected:#04x}, got {output:#04x}",
        )
        previous = output


def validate_rejects_corruption(snapshots: list[dict]) -> None:
    mutated = [dict(snapshot) for snapshot in snapshots]
    target = next(
        index
        for index, snapshot in enumerate(mutated)
        if snapshot["rst_n"] == "1" and snapshot["ena"] == "1"
    )
    original = binary_value(mutated[target], "uo_out")
    require(original is not None, "mutation target has unknown output")
    mutated[target]["uo_out"] = f"{(original + 7) & 0xFF:b}"
    try:
        validate_transitions(mutated)
    except SystemExit as error:
        require("counter transition mismatch" in str(error), "corrupted waveform failed for the wrong reason")
        return
    raise SystemExit("FAIL: transition checker accepted an intentionally corrupted waveform")


def select_learning_events(snapshots: list[dict]) -> list[tuple[str, dict, int | None, int, str]]:
    selected: list[tuple[str, dict, int | None, int, str]] = []
    previous: int | None = None
    count_examples = 0
    have_reset = False
    have_wrap = False
    have_hold = False
    have_resume = False
    have_reset_priority = False

    for snapshot in snapshots:
        output = binary_value(snapshot, "uo_out")
        require(output is not None, "learning event has unknown output")
        reset_n = snapshot["rst_n"]
        enable = snapshot["ena"]
        if not have_reset and reset_n == "0" and output == 0:
            selected.append(("reset", snapshot, previous, output, "reset forces 00"))
            have_reset = True
        elif reset_n == "1" and enable == "1" and previous is not None and output == ((previous + 1) & 0xFF):
            if count_examples < 3:
                count_examples += 1
                selected.append((f"count {count_examples}", snapshot, previous, output, "enabled edge adds one"))
            elif not have_wrap and previous == 0xFF and output == 0:
                selected.append(("wrap", snapshot, previous, output, "8-bit FF rolls to 00"))
                have_wrap = True
            elif have_hold and not have_resume:
                selected.append(("resume", snapshot, previous, output, "enable resumes counting"))
                have_resume = True
        elif reset_n == "1" and enable == "0" and previous is not None and output == previous and not have_hold:
            selected.append(("hold", snapshot, previous, output, "disabled edge preserves state"))
            have_hold = True
        if (
            not have_reset_priority
            and reset_n == "0"
            and enable == "1"
            and previous not in (None, 0)
            and output == 0
        ):
            selected.append(("reset wins", snapshot, previous, output, "reset overrides enable"))
            have_reset_priority = True
        previous = output

    require(have_reset, "no reset edge found")
    require(count_examples == 3, "fewer than three count examples found")
    require(have_wrap, "no FF-to-00 wrap edge found")
    require(have_hold, "no disabled hold edge found")
    require(have_resume, "no post-hold resume edge found")
    require(have_reset_priority, "no reset-priority edge with enable high found")
    return selected


def format_hex(value: int | None) -> str:
    return "--" if value is None else f"{value:02X}"


def print_walkthrough(path: Path, snapshots: list[dict], timescale: tuple[int, str]) -> None:
    events = select_learning_events(snapshots)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print("M0 WAVEFORM WALKTHROUGH - read clock edges, not just a PASS label")
    print("=" * 67)
    print(f"Waveform: {path.relative_to(ROOT)}")
    print(f"SHA-256: {digest}")
    print(f"Rising edges checked against the M0 transition table: {len(snapshots)}")
    print("Falsification check: PASS - an intentionally corrupted count edge was rejected.")
    print("\nAt each row, inputs are the values sampled on that rising clock edge.")
    print(f"{'event':12} {'time (ns)':>10} {'rst_n':>5} {'ena':>4} {'before':>7} {'after':>6}  meaning")
    print("-" * 78)
    for name, snapshot, before, after, meaning in events:
        time_ns = ticks_to_ns(snapshot["ticks"], timescale)
        print(
            f"{name:12} {time_ns:10.3f} {snapshot['rst_n']:>5} {snapshot['ena']:>4} "
            f"{format_hex(before):>7} {format_hex(after):>6}  {meaning}"
        )
    print("\nHow to read one row:")
    print("  'hold' has rst_n=1 and ena=0, so the value after the edge equals the value before it.")
    print("  'reset wins' has rst_n=0 and ena=1, so reset still forces 00 because reset has priority.")
    print("\nWhat this establishes:")
    print("  The retained Icarus waveform matches the M0 reset/count/wrap/hold rules at every rising edge.")
    print("What this does NOT establish:")
    print("  It is the same finite simulation presented readably, not a new formal or physical proof.")
    print("\nTEACH-BACK PRACTICE")
    print("Choose one row and say: which inputs were sampled, whether the output changed, and why.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vcd", nargs="?", type=Path, default=DEFAULT_VCD)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="validate all rising-edge transitions without printing the lesson",
    )
    args = parser.parse_args()
    path = args.vcd.resolve()
    require(path.is_file(), f"waveform not found: {path}")
    snapshots, timescale = parse_vcd(path)
    validate_transitions(snapshots)
    validate_rejects_corruption(snapshots)
    select_learning_events(snapshots)
    if args.verify:
        print(f"PASS: {len(snapshots)} M0 rising edges match; required events exist; a corrupted edge is rejected.")
        print("LIMIT: parsing a simulation waveform is not formal, physical, analog, or silicon evidence.")
    else:
        print_walkthrough(path, snapshots, timescale)


if __name__ == "__main__":
    main()
