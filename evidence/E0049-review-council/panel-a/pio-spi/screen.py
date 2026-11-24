# SPDX-License-Identifier: Apache-2.0
"""Compare real assembled SPI programs in the pinned PIO decoder with the repository's pin equations."""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from spi_program import resident_source, spi_source
from resident_sequence import rearm_sequence
from tools.spi_four_mode_oracle import assess, raw_at, timing


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def compile_programs(tool_dir, out, image):
    words, inventory = {}, {}
    for phase in (0, 1):
        kinds = ["exact", "late", "early", "mapped_exact", "mapped_early", "bypass_exact"]
        if phase == 0:
            kinds.append("resident")
        for kind in kinds:
            name = "resident-common" if kind == "resident" else f"phase{phase}-{kind}"
            source = out / (name + ".pio")
            assembly = resident_source()[0] if kind == "resident" else spi_source(phase, kind)
            source.write_text(assembly, encoding="ascii")
            if os.name == "nt":
                assembler = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
                             "--mount", f"type=bind,source={tool_dir},target=/tools,readonly",
                             "--mount", f"type=bind,source={out},target=/out", "-w", "/out", image, "/tools/pioasm"]
            else:
                assembler = [str(tool_dir / "pioasm")]
            result = subprocess.run([*assembler, "-o", "hex", source.name, name + ".hex"],
                                    cwd=out, capture_output=True, text=True, timeout=30)
            (out / (name + ".compile.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            result.check_returncode()
            encoded = [int(x, 16) for x in (out / (name + ".hex")).read_text("ascii").splitlines()]
            check(1 <= len(encoded) <= 32, "resident instruction capacity")
            packed = b"".join(w.to_bytes(2, "little") for w in encoded)
            words[phase, kind] = encoded
            if kind == "resident":
                words[1, kind] = encoded
            inventory[name] = {"words": len(encoded), "bytes": len(packed), "sha256_le": sha(packed)}
    return words, inventory


def cases():
    # Concrete inventory frozen in matrix.md and mapping-amendment.md.
    early = [1] * 8
    late = [96] * 8
    mixed = [1, 96, 16, 80, 24, 72, 32, 64]
    for mode in range(4):
        for order in (0, 1):
            for boundary, exact in (("decoder", "exact"), ("gpio", "mapped_exact")):
                for i, received in enumerate((0x69, *(1 << bit for bit in range(8)))):
                    tx = 0x96 if i == 0 else 0xff ^ received
                    yield boundary, mode, order, exact, "edge_only", tx, received, None, False, "pass"
                for response in (early, late, mixed):
                    yield boundary, mode, order, exact, "held", 0x96, 0x69, response, False, "pass"
                if boundary == "decoder":
                    for response in (early, late, mixed):
                        yield boundary, mode, order, "late", "held", 0x96, 0x69, response, False, "pass"
                    yield boundary, mode, order, "late", "edge_only", 0x96, 0x69, None, False, "byte"
                    yield boundary, mode, order, "early", "edge_only", 0x96, 0x69, None, False, "byte"
                    yield boundary, mode, order, "exact", "held", 0x96, 0x69, late, True, "polarity"
                else:
                    yield boundary, mode, order, "exact", "edge_only", 0x96, 0x69, None, False, "mapping"
                    yield boundary, mode, order, "mapped_early", "edge_only", 0x96, 0x69, None, False, "byte"
            for i, received in enumerate((0x69, *(1 << bit for bit in range(8)))):
                tx = 0x96 if i == 0 else 0xff ^ received
                yield "gpio_bypass", mode, order, "bypass_exact", "edge_only", tx, received, None, False, "pass"
            for response in (early, late, mixed):
                yield "gpio_bypass", mode, order, "bypass_exact", "held", 0x96, 0x69, response, False, "pass"
            yield "gpio_bypass_sync_control", mode, order, "bypass_exact", "edge_only", 0x96, 0x69, None, False, "byte"
            for boundary, candidate in (("gpio_peer", "mapped_exact"), ("gpio_peer_bypass", "bypass_exact")):
                for response in (early, late, mixed):
                    yield boundary, mode, order, candidate, "held", 0x96, 0x69, response, False, "pass"
            yield "gpio_peer", mode, order, "mapped_exact", "held", 0x96, 0x69, late, True, "peer_refusal"
            yield "gpio_peer", mode, order, "mapped_exact", "held", 0x96, 0x69, [104] * 8, False, "peer_late"
            for i, received in enumerate((0x69, *(1 << bit for bit in range(8)))):
                tx = 0x96 if i == 0 else 0xff ^ received
                yield "gpio_resident", mode, order, "resident", "edge_only", tx, received, None, False, "pass"
            for response in (early, late, mixed):
                yield "gpio_resident", mode, order, "resident", "held", 0x96, 0x69, response, False, "pass"
            yield "gpio_peer_resident", mode, order, "resident", "held", 0x96, 0x69, mixed, False, "pass"
            yield "gpio_resident", mode, order, "resident", "edge_only", 0x96, 0x69, None, False, "entry"


def evaluate(tool_dir, words, case, out, sequential):
    boundary, mode, order, kind, profile, tx, rx, response, wrong_polarity, expectation = case
    mapped = boundary != "decoder"
    peer = boundary.startswith("gpio_peer")
    bypass = boundary in ("gpio_bypass", "gpio_peer_bypass")
    primed = kind == "resident" or kind.startswith(("mapped_", "bypass_"))
    nominal_cs = 2 if mode & 1 else 3
    actual_cs = nominal_cs + int(mapped and not primed)
    schedule = timing(mode, actual_cs)
    last = schedule["halt"]
    raw = [] if peer else [1] + [raw_at(edge, schedule, rx, order, profile, response) for edge in range(1, last + 1)]
    message = {"cpol": mode >> 1, "order": order, "wrongPolarity": wrong_polarity,
               "tx": tx, "words": words[mode & 1, kind], "primed": primed, "finish": last,
               "inputStages": 1 if bypass else (3 if mapped else 2), "outputStages": int(mapped),
               "bypass": bypass, "manualPush": kind == "bypass_exact",
               "raw": "".join(map(str, raw)), "retainHost": mode == 0 and order == 0 and profile == "edge_only" and
               rx == 0x69 and (boundary, kind) in (("decoder", "exact"), ("gpio", "mapped_exact"), ("gpio_bypass", "bypass_exact"))}
    if kind == "resident":
        message["entry"] = resident_source()[1][(mode & 1) ^ int(expectation == "entry")]
    if peer:
        message["peer"] = {"mode": mode, "rx": rx, "delays": response}
    run = subprocess.run(["node", str(HERE / "pio_spi_trace.cjs"), str(tool_dir)],
                         input=json.dumps(message), text=True, capture_output=True, timeout=20)
    check(run.returncode == 0, "emulator exit " + str(run.returncode) + ": " + run.stderr[-1000:])
    measured = json.loads(run.stdout)
    if peer:
        raw = [int(c) for c in measured["targetRaw"]]
        check(len(raw) == last + 1, "target raw observation incomplete")
        target = measured["peerResult"]
        check((target["asserted"], target["released"]) == (schedule["cs"], schedule["release"]), "target CS framing")
        if expectation == "peer_refusal":
            check(target["refused"] and not target["samples"] and not target["launches"], "target accepted wrong idle")
        else:
            check(not target["refused"] and target["samples"] == schedule["sample"] and
                  target["launches"] == schedule["launch"] and target["decoded"] == tx,
                  f"target framing or MOSI byte disagrees: {target}")
            if expectation == "pass":
                expected_raw = [1] + [raw_at(n, schedule, rx, order, profile, response) for n in range(1, last + 1)]
                check(raw == expected_raw, "actual held target differs from the preregistered raw pin schedule")
    raw_rows = base64.b64decode(measured["publicRows"])
    check(len(raw_rows) == (last + 1) * 3, "incomplete public trace")
    result_byte = measured["receiveByte"]
    rows = []
    for edge in range(last + 1):
        output, enable, state = raw_rows[3 * edge:3 * edge + 3]
        valid = int(bool(state & 1))
        # The host popped only after the stability interval. This byte value is
        # backward-projected to the first observable RX-not-empty transition.
        rows.append({"edge": edge, "out": output, "oe": enable, "miso": raw[edge],
                     "rx_valid": valid, "rx": result_byte if valid else 0,
                     "state": "HALT" if state & 2 else "RUN"})
    capture_offset = {"exact": 2, "early": 1, "late": 24, "mapped_exact": 4, "mapped_early": 3,
                      "bypass_exact": 3, "resident": 4}[kind] - int(mapped)
    captures = [s + capture_offset for s in schedule["sample"]]
    errors = assess(rows, schedule, tx, rx, order, captures)
    kinds = sorted({e["kind"] for e in errors})
    first_valid = next((r["edge"] for r in rows if r["rx_valid"]), None)
    first_irq = next((r["edge"] for r in rows if r["state"] == "HALT"), None)
    check(measured["afterPopEmpty"] and measured["endStatus"] & 1, "FIFO did not drain or no final observed IRQ")
    if expectation != "entry":
        check(measured["stable"], "result changed after the expected terminal time")
        check(first_valid == captures[-1], "FIFO visibility disagrees with expected instruction offset")
    check(all(not (r["oe"] & 2) for r in rows), "MISO was ever driven")
    check(measured["setupCount"] == sum(measured["counts"].values()) - 3,
          "unexpected host service, expected one launch and two terminal reads")
    if expectation == "pass":
        check(not kinds and result_byte == rx, f"positive did not match: {kinds}, got {result_byte}")
    elif expectation == "byte":
        check(kinds == ["received_byte"] and result_byte == rx ^ 255, f"wrong sample control: {kinds}, got {result_byte}")
    elif expectation == "polarity":
        check("idle_before_cs" in kinds and "pins" in kinds and result_byte == rx,
              f"polarity control did not isolate wrong pins: {kinds}")
    elif expectation == "mapping":
        check("received_byte" in kinds and "terminal_timing" in kinds and result_byte == rx ^ 255,
              f"omitted mapping registers control did not discriminate: {kinds}, got {result_byte}")
    elif expectation == "peer_refusal":
        check({"idle_before_cs", "pins", "received_byte", "wire_miso"} <= set(kinds) and result_byte == 0xff,
              f"wrong-mode reactive target did not refuse: {kinds}, got {result_byte}")
    elif expectation == "peer_late":
        check(kinds == ["received_byte", "wire_miso"] and result_byte != rx,
              f"late reactive response did not corrupt only MISO: {kinds}, got {result_byte}")
    elif expectation == "entry":
        check("pins" in kinds and "valid_timing" in kinds and first_valid != captures[-1],
              f"wrong phase entry did not change physical and RX times: {kinds}")
    else:
        raise ValueError("unknown expected disposition")
    if primed and kind == "mapped_exact":
        check(first_valid == schedule["sample"][-1] + 3 and first_valid != schedule["sample"][-1] + 2,
              "missing strict G3 byte-availability timing rejection")
    if kind == "bypass_exact":
        check(first_valid == schedule["sample"][-1] + 2, "bypass program missed strict exact visibility")
    if "operations" in measured:
        (out / f"host-{boundary}.json").write_text(json.dumps(measured["operations"]) + "\n", encoding="utf-8")
    record = {"boundary": boundary, "mode": mode, "order": order, "kind": kind, "profile": profile,
              "tx": tx, "requested_rx": rx, "response_quarters": response, "control": expectation,
              "observed_rx": result_byte, "errors": kinds, "cs_assumed_and_scored": actual_cs,
              "fifo_valid_edge": first_valid, "completion_irq_edge": first_irq,
              "last_wire_sample": schedule["sample"][-1], "strict_vm_exact_valid_time": first_valid == schedule["sample"][-1] + 2,
              "cold_setup_ops": measured["setupCount"], "wire_fifo_irq_sha256": sha(raw_rows)}
    if peer:
        record["target"] = measured["peerResult"]
        record["miso_sha256"] = sha(bytes(raw))
        record["miso_at_samples"] = [raw[n] for n in schedule["sample"]]
    if kind == "resident":
        record["forced_entry"] = message["entry"]
        record["stable_from_requested_end"] = measured["stable"]
    return record, measured["counts"], raw_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    args = parser.parse_args()
    tool_dir, out = args.tools.resolve(), args.out.resolve()
    check(out.is_relative_to(ROOT / "build"), "output must stay under build")
    out.mkdir(parents=True, exist_ok=False)
    result = {"schema": "council-pio-spi-v1", "started_utc": utc(), "observations": [], "failures": [],
              "inputs_sha256": {p.name: sha(p.read_bytes()) for p in
                                [Path(__file__), HERE / "spi_program.py", HERE / "pio_spi_trace.cjs",
                                 HERE / "declaration.md", HERE / "matrix.md", HERE / "mapping-amendment.md",
                                 HERE / "bypass-declaration.md",
                                 HERE / "clock_peer.cjs", HERE / "peer-declaration.md", HERE / "resident-declaration.md",
                                 HERE / "resident_sequence.py",
                                 ROOT / "tools/spi_four_mode_oracle.py"]},
              "tools_sha256": sha((tool_dir / "tools.json").read_bytes()),
              "node_version": subprocess.check_output(["node", "--version"], text=True).strip()}
    words, result["images"] = compile_programs(tool_dir, out, args.image)
    host_counts = {}
    traces = bytearray()
    for index, case in enumerate(cases()):
        try:
            record, counts, rows = evaluate(tool_dir, words, case, out, index)
            result["observations"].append(record)
            host_counts[f"{record['boundary']}-{record['mode'] & 1}-{record['kind']}"] = counts
            traces.extend(rows)
        except (ValueError, subprocess.SubprocessError, KeyError) as exc:
            result["failures"].append({"case_index": index, "case": case, "error": str(exc)})
    result["host_counts"] = host_counts
    result["public_rows_sha256"] = sha(traces)
    result["input_case_count"] = index + 1
    try:
        result["single_sm_resident_sequence"] = rearm_sequence(tool_dir, words[0, "resident"])
    except (ValueError, subprocess.SubprocessError, KeyError) as exc:
        result["failures"].append({"case": "single_sm_resident_sequence", "error": str(exc)})
    result["ended_utc"] = utc()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out / "public-rows.bin.gz").write_bytes(gzip.compress(traces, compresslevel=9, mtime=0))
    print(f"{index+1} cases, {len(result['observations'])} met their recorded dispositions, {len(result['failures'])} unexpected")
    if result["failures"]:
        print(result["failures"][0])
    return int(bool(result["failures"]))


if __name__ == "__main__":
    sys.exit(main())
