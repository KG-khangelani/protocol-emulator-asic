# SPDX-License-Identifier: Apache-2.0
"""Replay the bias and clock-control captures and compare the no-pull trials to E0057."""
from datetime import datetime
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_spi import remote
from experiments.remote_spi.branch_bias import clock_score
from experiments.remote_spi.branch_bias import score as bias_score
from experiments.remote_spi.branch_bias.run import payload, schedules
from experiments.remote_spi.check import assess, need, records
from tools.production_sram import verify


def historical_reference(current):
    board = ROOT / "evidence/E0057-remote-spi/board-4"
    older = {}
    for suite in ("held", "matrix", "fine"):
        rows = records(gzip.decompress((board / suite / "terminal.bin.gz").read_bytes()))
        older[suite] = {r["name"]: r for r in rows if r["event"] == "trace"}
    reference = {}
    for name, (desc, _) in schedules().items():
        op, mode = name.split("-")
        if mode == "held":
            suite, key = "held", f"held-{op}-0-1-32"
        elif mode == "pause":
            suite, key = "matrix", f"pause-{op}-0-1"
        else:
            suite, key = "fine", f"fine-{op}-250-7-0-1-32-{mode}"
        baseline = assess((key,) + desc[1:], older[suite][key])
        fields = ("status", "errors", "abort_ns", "timeout_ns", "handoff_ns", "release_to_fresh_lower_ns",
                  "quiet_after_release", "quiet_through_fresh_prefix", "reply", "valid_fresh_byte",
                  "min_setup_lower_ns", "min_hold_lower_ns")
        subset = {k: baseline[k] for k in fields if k in baseline}
        need(not subset["errors"], "historical baseline failed: " + key)
        for order in ("forward", "reverse"):
            same = next(t for t in current[order] if t["name"] == name and t["bias"] == [0, 0])
            need(all(v == same["receivers"]["gp28"][k] for k, v in subset.items()), "historical replay: " + key)
        reference[name] = {"suite": suite, "case": key, "metrics": subset}
    return reference


def replay():
    measured = {s: bias_score.score(HERE / s / "terminal.bin.gz") for s in ("forward", "reverse")}
    measured["clock"] = clock_score.score(HERE / "clock/terminal.bin.gz")
    measured["baseline"] = historical_reference(measured)
    return measured


def rejected(message, function, *args):
    try:
        function(*args)
    except ValueError as exc:
        need(str(exc) == message, "wrong rejection: " + str(exc))
        return
    raise ValueError("accepted damaged observation: " + message)


def negative_controls():
    _, rows = bias_score.session(HERE / "clock/terminal.bin.gz", ("clock-control",))
    index = next(i for i, row in enumerate(rows) if row["event"] == "trace")
    row, pieces = rows[index], rows[:index]
    bad_pads = [list(p) for p in row["pads"]]
    bad_pads[0][3] |= 1 << 13
    rejected("physical input function, bias and disabled driver", bias_score.check_pads, dict(row, pads=bad_pads))
    rejected("all raw DMA halfwords", clock_score.extract, row, pieces[:-1])
    rejected("witnessed running or parked clock", clock_score.extract, dict(row, parked=True), pieces)
    raw = clock_score.extract(row, pieces)
    # Flip only GPIO20 in the sample immediately preceding the observed abort.
    offset = 2 * (raw["abort"] - 1)
    changed = list(pieces)
    fragment = next(i for i, p in enumerate(pieces) if p["offset"] <= offset < p["offset"] + len(p["data"]) // 2)
    data = bytearray.fromhex(pieces[fragment]["data"])
    data[offset - pieces[fragment]["offset"]] ^= 1
    changed[fragment] = dict(pieces[fragment], data=data.hex())
    rejected("opposite known driven levels sampled on both inputs", clock_score.extract, row, changed)
    _, rows = bias_score.session(HERE / "forward/terminal.bin.gz", ("forward",))
    packed = next(r for r in rows if r["event"] == "trace" and r["packed"])
    encoded = bytearray.fromhex(packed["data"])
    encoded[3:5] = bytes(2)
    rejected("eight-input change journal", bias_score.decoded, dict(packed, data=encoded.hex()), [])


def audit():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, section in ((ROOT, "inputs"), (HERE, "files")):
        for name, expected in manifest[section].items():
            data = (base / name).read_bytes()
            if section == "inputs" and name.endswith(".md"):
                data = data.replace(b"\r\n", b"\n")  # Git's committed line endings for the cited documents.
            need(remote.sha(data) == expected, "retained hash: " + name)
    profile = verify(ROOT)
    bitstream = ROOT / "evidence/E0057-remote-spi/fabricfox-spi.bin"
    need(len(profile["files_sha256"]) == 20 and remote.sha(bitstream.read_bytes()) == remote.IMAGE_SHA,
         "production and FPGA identities")
    end = None
    for folder, order, count in (("forward", "forward", 50), ("reverse", "reverse", 50), ("clock", "clock-control", 8)):
        where = HERE / folder
        receipt = json.loads((where / "result.json").read_bytes())
        job = gzip.decompress((where / "job.py.gz").read_bytes())
        need(job == payload(order) and remote.sha(job) == receipt["job_sha256"], "executed board job: " + order)
        start = datetime.fromisoformat(receipt["started_utc"])
        stop = datetime.fromisoformat(receipt["ended_utc"])
        need(start < stop and (end is None or end < start), "separate ordered sessions")
        end = stop
        need(receipt["board"] == "fpga-4" and receipt["board_identity_sha256"] == manifest["board_identity_sha256"]
             and receipt["order"] == order and receipt["traces"] == count and receipt["status"] == "CAPTURED"
             and receipt["clients_before"] == 0 and receipt["image_sha256"] == remote.IMAGE_SHA
             and receipt["program_sha256"] == remote.PROGRAM_SHA and receipt["profile_sha256"] == profile["profile_sha256"]
             and receipt["enable"]["enabled"] == remote.NAME and receipt["restore"]["enabled"] == receipt["after"]
             == receipt["restore_target"] == "tt_um_factory_test", "physical receipt and restoration: " + order)
        header, _ = bias_score.session(where / "terminal.bin.gz", (order,))
        need(header["micropython"] == "1.30.0-preview" and "RP2350B" in header["host"], "physical sampler identity")
    measured = replay()
    need(measured == json.loads(gzip.decompress((HERE / "measurements.json.gz").read_bytes())), "raw replay matched archive")
    primary = measured["forward"] + measured["reverse"]
    need(len(primary) == 100 and sum(t["sample_count"] for t in primary) == 692080, "complete bias sweep")
    opposed = [t for t in primary if t["relation"] == "opposed" and t["origin_to_fresh_ns"] is not None]
    need(len(opposed) == 24 and all(r["bias_observation"]["at_fresh_select"] == t["commanded_bit"]
         for t in opposed for r in t["receivers"].values()), "reported levels at reselection")
    need(all(not r["errors"] and r["bias_observation"]["four_driven_samples_correct"] for t in primary
         for r in t["receivers"].values()), "fresh traffic and driven references on both inputs")
    for t in measured["clock"]:
        middle = t["windows"]["during"]
        need(middle["clock_edges"] == middle["gp28_edges"] == (0 if t["parked"] else 200)
             and t["windows"]["after"]["gp28_edges"] == 200, "observed clock-control result")
    negative_controls()
    print("PASS: 100 branch-bias trials, 8 raw clock controls, 10 historical matched schedules, "
          "5 rejected corruptions, 3 rebuilt board jobs, 20 qualified production inputs")


if __name__ == "__main__":
    audit()
