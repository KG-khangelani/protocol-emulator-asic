# SPDX-License-Identifier: Apache-2.0
"""Replay the RP2350B transactions and exercise the local reporting command with clearly synthetic fixture labels."""
from datetime import datetime
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.local_breakout.prepare import firmware
from experiments.local_breakout.run import observations
from experiments.local_breakout.sensor_reference import remote as bench, score
from experiments.remote_i2c.check import need
from experiments.remote_i2c.remote import IMAGE_SHA, NAME
from tools.production_sram import sha, verify

SOURCE = ROOT / "experiments/local_breakout/sensor_reference"
ORDERS = {"first": ("forward", bench.CASES), "faults": ("faults", bench.FAULTS), "crossover": ("crossover", bench.CROSSOVER)}


def rejected(message, func, *args):
    try:
        func(*args)
    except ValueError as exc:
        need(str(exc) == message, "unexpected rejection: " + str(exc))
        return
    raise ValueError("accepted altered observation: " + message)


def terminal(folder):
    raw = gzip.decompress((HERE / folder / "terminal.bin.gz").read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04\x04>"), "clean bench completion")
    records = []
    partial = None
    for line in raw[2:-3].splitlines():
        if line.startswith(b"SENSORREF_PARTIAL "):
            need(partial is None, "only one partial broadcast per case")
            partial = json.loads(line.split(b" ", 1)[1])
        elif line.startswith(b"I2CLAB "):
            records.append((json.loads(line[7:]), partial))
            partial = None
    need(partial is None and len(records) == 8, "two session endpoints and six trials")
    header = records[0][0]
    cleanup = records[-1][0]
    need(header["event"] == "start" and header["host"] == "TinyTapeout RP2350B Core with RP2350"
         and header["micropython"] == "1.30.0-preview" and header["system_hz"] == 125000000
         and header["peer_clock_hz"] == 1000000 and cleanup["event"] == "finish" and cleanup["restored_bank"]
         and cleanup["restored_hz"] == header["initial_hz"] and cleanup["host_uio_oe"] == 0, "board session boundaries")
    return records[1:-1]


def trial(row, partial):
    case = row["name"]
    need(row["event"] == "trace" and (partial is not None) == (case == "late-power"), "partial waveform identity")
    result = {"case": case, "peer_slots": row["received"], "error": row["error"]}
    if case == "empty":
        need(row["error"] == "ValueError('expected exactly one sensor', 0)" and not row["result"]
             and not row["peer_samples"] and row["received"] == row["planned"] == 0, "physical no-presence control")
        return result
    script = bench.script(case)
    raw = bytes.fromhex(row["peer_samples"])
    need(raw == script["levels"] and len(raw) == row["received"] == row["planned"],
         "all physical master, search-direction and peer bits: " + case)
    if case in ("bad-crc", "flat-scratch"):
        need(row["error"] == "ValueError('invalid scratchpad or CRC', b'" + script["scratchpad"] + "')"
             and not row["result"], "addressed scratchpad fault")
    elif case == "late-power":
        need(row["error"] == "ValueError('identity or power result changed',)" and not row["result"]
             and partial["before"]["rom"] == partial["after"]["rom"] == script["rom"]
             and partial["before"]["power"] == partial["power"] == 0 and partial["after"]["power"] == 1,
             "reference changed after the acquired broadcast")
        rejected("addressed, broadcast and observed power agree", score.measurement, partial)
        result["partial_wire"] = score.wire(partial)
        need(result["partial_wire"]["wire_power"] == 0, "retained partial zero")
    else:
        full = row["result"]
        need(not row["error"] and full["fixture"] == "scripted-peer" and full["system_hz"] == 125000000
             and (full["master_gpio"], full["sensor_gpio"]) == (27, 19), "physical scripted-peer acquisition")
        decoded = score.measurement(full)
        need(decoded["rom"] == script["rom"] and decoded["scratchpad_before"] == decoded["scratchpad_after"]
             == script["scratchpad"], "returned peer identity")
        result["measurement"] = decoded
    return result


def replay():
    results = {}
    for folder, (_, order) in ORDERS.items():
        captures = terminal(folder)
        need([row["name"] for row, _ in captures] == list(order), "physical case order")
        results[folder] = [trial(row, partial) for row, partial in captures]
    return results


def model_fpga(mode, rom, log):
    # Only for testing the command interface. The ROM labels here are supplied to E0063 header-model waveforms.
    packed, expected = firmware("onewire")
    image = bytes(packed[i+5] for i in range(0, len(packed), 6) if packed[i+3] & 4 and packed[i+1] < 0xa0)
    loader, changes, end = observations(log, packed, expected, False)
    bit = int(mode == "external")
    rows = [dict(event="identity", mode=mode, host="Raspberry Pi Pico with RP2040", rom=rom, reference_bit=bit),
            dict(event="cold", bytes=image.hex(), registers=loader["registers"]), dict(event="pins", changes=changes),
            dict(event="finish", samples=15000, system_hz=125000000, sample_hz=5000000, clock_divisor=10,
                 status=end[0], confirmed_rom=rom, confirmed_bit=bit, cleanup=True)]
    return "".join("PICO1W " + json.dumps(row) + "\n" for row in rows)


def exercise_reporting():
    captured = {row["name"]: row["result"] for row, _ in terminal("crossover") if row["result"]}
    measured = {name: score.measurement(row) for name, row in captured.items()}
    normal = score.pair(measured["ext"], measured["par"])
    swapped = score.pair(measured["swapped-high"], measured["swapped-low"])
    cross = score.crossover(normal, swapped)
    rejected("two distinct sensor ROMs", score.pair, measured["ext"], measured["swapped-low"])
    rejected("declared external and parasite VDD wiring", score.pair, measured["swapped-high"], measured["silent"])
    rejected("same two ROMs with the rails swapped", score.crossover, normal, normal)
    # Turn the first transmitted zero into a one in the actual sensor-end samples, preserving the rest of the record.
    sample = captured["ext"]
    damaged = bytearray.fromhex(sample["dq_lsb_first"])
    bits = [(byte >> i) & 1 for byte in damaged for i in range(8)]
    start = [i for i in range(1, len(bits)) if bits[i-1] and not bits[i]][2]
    end = bits.index(1, start)
    for i in range(start + 14, end):
        damaged[i//8] |= 1 << (i % 8)
    rejected("broadcast command on sensor DQ", score.measurement, dict(sample, dq_lsb_first=damaged.hex()))
    header_logs = json.loads(gzip.decompress((ROOT / "evidence/E0063-local-breakout/header-logs.json.gz").read_bytes()))["drain"]
    scratch = ROOT / "build"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix="synthetic-sensor-cli-") as temp:
        path = Path(temp)
        for name, item in captured.items():
            # Exercise the local parser only. These temporary records are never retained as real devices.
            local = dict(item, fixture="local-pico", host="Raspberry Pi Pico with RP2040", master_gpio=19, sensor_gpio=18)
            (path / name).write_text("SENSORREF " + json.dumps(local) + "\n", encoding="utf8")
        for mode in ("external", "parasite"):
            (path / mode).write_text(model_fpga(mode, normal[mode]["rom"], header_logs[mode]), encoding="utf8")
        report = json.loads(subprocess.check_output([sys.executable, "-B", str(SOURCE / "score.py"), "ext", "par",
                            "--swapped", "swapped-high", "swapped-low", "--fpga", "external", "parasite"], cwd=path))
        need(report["pico"] == cross and report["fpga"]["parasite"]["bit"] == 0 and report["fpga"]["external"]["bit"] == 1,
             "complete command interface against scripted and modeled fixtures")
        wrong = dict(report["fpga"]["external"], rom=normal["parasite"]["rom"])
        rejected("FPGA sensor, power, command and slot count: external", score.compare_fpga, normal, wrong, report["fpga"]["parasite"])
        (path / "remote").write_text("SENSORREF " + json.dumps(sample), encoding="utf8")
        rejected("local Pico and declared sensor-end connection", score.local, path / "remote")
        (path / "incomplete").write_text("SENSORREF_PARTIAL {}\n", encoding="utf8")
        rejected("local sensor acquisition failed", score.local, path / "incomplete")


def audit():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, key in ((ROOT, "inputs"), (HERE, "files")):
        for name, expected in manifest[key].items():
            need(sha((base / name).read_bytes()) == expected, "retained identity: " + name)
    profile = verify(ROOT)
    need(len(profile["files_sha256"]) == 20 and profile["profile_sha256"] == manifest["profile_sha256"]
         and sha((ROOT / "evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) == IMAGE_SHA, "qualified identities")
    checks = json.loads((HERE / "checks.json").read_bytes())
    compiled = checks["stock_compile"]
    need(compiled["compilations"] == 2 and compiled["source_sha256"] == sha((SOURCE / "pico.py").read_bytes())
         and compiled["first_sha256"] == compiled["second_sha256"] == sha(gzip.decompress((HERE / "stock-pico.mpy.gz").read_bytes())),
         "original Pico compilation reproduced")
    for name in ("check", "doctor"):
        need(checks[name]["status"] == "PASS" and checks[name]["log_sha256"] ==
             sha(gzip.decompress((HERE / (name + ".log.gz")).read_bytes())), "workbench receipt: " + name)
    first_source = subprocess.check_output(["git", "show", manifest["first_source_commit"] + ":" +
                                           (SOURCE / "pico.py").relative_to(ROOT).as_posix()], cwd=ROOT).decode("utf8")
    end = None
    for folder, (order, _) in ORDERS.items():
        location = HERE / folder
        receipt = json.loads((location / "result.json").read_bytes())
        code = gzip.decompress((location / "job.py.gz").read_bytes())
        need(code == bench.payload(order, first_source if folder == "first" else None) and sha(code) == receipt["code_sha256"],
             "executed physical job: " + order)
        start = datetime.fromisoformat(receipt["started_utc"])
        stop = datetime.fromisoformat(receipt["ended_utc"])
        need(start < stop and (end is None or end < start), "separate physical sessions")
        end = stop
        need(receipt["status"] == "CAPTURED" and receipt["traces"] == 6 and receipt["order"] == order and
             receipt["board"] == "fpga-4" and receipt["identity_sha256"] == manifest["board_identity_sha256"] and
             receipt["clients_before"] == 0 and receipt["image_sha256"] == IMAGE_SHA and
             receipt["profile_sha256"] == profile["profile_sha256"] and receipt["enable"]["enabled"] == NAME and
             receipt["restore"]["enabled"] == receipt["restore_target"] == receipt["after"] == "tt_um_factory_test",
             "board admission, identity and restoration")
    result = replay()
    need(result == json.loads((HERE / "measurements.json").read_bytes()), "all retained results came from the terminal samples")
    exercise_reporting()
    print("PASS: 18 physical fixture trials, three exact board jobs, both ROMs in both programmed modes, "
          "retained late failure, local reporting including modeled FPGA joins, 20 qualified inputs")


if __name__ == "__main__":
    audit()
