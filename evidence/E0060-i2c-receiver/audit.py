# SPDX-License-Identifier: Apache-2.0
"""Reconstruct all paired receiver traces and the role-swap conclusion from the raw board responses."""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.receiver.score import LINK, LINK_SDA, SCL_OE, analyze, need, score
from experiments.remote_i2c.remote import IMAGE_SHA
from tools.production_sram import verify

SESSIONS = ("native10", "pulls10", "native8", "pin27-before", "pin19", "pin27-after",
            "full19-first", "full27", "full19-repeat")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def limits(cases, pin, field):
    ranges = [c[pin][field] for c in cases if c[pin][field]["n"]]
    return [min(r["min"] for r in ranges), max(r["max"] for r in ranges)] if ranges else []


def summarize(base):
    rows = {}
    for name in SESSIONS:
        folder = base / name
        rec = json.loads((folder / "result.json").read_bytes())
        raw_code = gzip.decompress((folder / "job.py.gz").read_bytes())
        need(hashlib.sha256(raw_code).hexdigest() == rec["code_sha256"], name + " uploaded job")
        settings = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(raw_code).body if isinstance(n, ast.Assign)}
        need(rec["status"] == "CAPTURED" and rec["board"] == "fpga-4" and rec["clients_before"] == 0
             and rec["image_sha256"] == IMAGE_SHA and rec["traces"] == 6
             and rec["after"] in ("tt_um_factory_test", "idle_display"), name + " board completion")
        run = score(folder / "terminal.bin.gz")
        meta, cases = run["start"], list(run["cases"].values())
        need(settings["EXTRA_PULL"] == rec["linked_pulls"] == meta["linked_pulls"]
             and settings["SAMPLE_HZ"] == rec["sample_hz"] == meta["sample_hz"]
             and len(settings["PLANS"]) == 4 and len(settings["TRIALS"]) == 6, name + " workload and capture settings")
        active = meta.get("target_scl", 27)
        two_sda = meta.get("both_sda", False)
        need(meta.get("target_sda", 26) == active - 1 and settings.get("TARGET_SCL", 27) == active
             and settings.get("BOTH_SDA", False) == two_sda and active == (19 if name in ("pin19","full19-first","full19-repeat") else 27),
             name + " active pins")
        positives = [c for c in cases if c["address"] == 0x2e]
        row = dict(hz=meta["sample_hz"], active_scl=active, both_sda=two_sda, extra_pulls=meta["linked_pulls"],
                   reads=len(positives), address_nacks=len(cases)-len(positives),
                   command_count_passes=sum(c["commands_match"] for c in cases),
                   total_disagreement_samples=sum(sum(c["input_disagreement_samples"].values()) for c in cases))
        for pin in ("gpio19", "gpio27"):
            short = Counter()
            for c in cases:
                short.update(c[pin]["short_counts"])
            edges = [c[pin]["edges"] for c in positives]
            other = [c[pin]["edges"] for c in cases if c["address"] != 0x2e]
            result = dict(raw_pass=sum(c[pin]["raw"]["passed"] for c in cases),
                          filtered_pass=sum(c[pin]["five_samples"]["passed"] for c in cases),
                          read_edge_range=[min(edges), max(edges)], nack_edge_range=[min(other), max(other)],
                          short_runs=dict(short), first_high_delay_ns=limits(cases, pin, "first_high_after_release_ns"))
            for guard in (0, 24):
                subset = [c for case, c in run["cases"].items() if case.startswith(f"{guard}-")]
                result[f"guard{guard}_sda_command_after_sampled_low_ns"] = limits(subset, pin, "sda_command_after_first_sampled_low_ns")
            row[pin] = result
        if "target_scl" in meta:
            mux = [[g, 0x5a, 3 if g in (active - 1, active) else 5] for g in (18, 19, 26, 27)]
            need(all(c["pad_registers"] == mux and c["pio2_input_sync_bypass"] == 0 for c in cases),
                 name + " pin-function, pad settings and input synchronizers")
            row["pad_registers"] = mux
        rows[name] = row
    return rows


def falsify():
    data = gzip.decompress((HERE / "full19-first/terminal.bin.gz").read_bytes())
    rows = [json.loads(line[7:]) for line in data.splitlines() if line.startswith(b"I2CLAB ")]
    fragments = [r["changes"] for r in rows if r.get("name") == "0-96-2e" and r["event"] == "pins"]
    changes = [p for fragment in fragments for p in fragment]
    count = 24000
    def assess(c):
        return analyze(c, count, 0x96, 1, True, 100, True)
    initial = assess(changes)
    need(changes[1][0] > 2 and initial["commands_match"] and initial["gpio19"]["raw"]["passed"], "control baseline")
    level = changes[0][1]
    extra = assess([changes[0], [1, level ^ SCL_OE], [2, level], *changes[1:]])
    need(not extra["commands_match"] and extra["gpio19"]["raw"]["passed"], "reject an extra command with identical bus data")
    for bit in (LINK, LINK_SDA):
        altered = []
        for t, val in changes:
            v = val | bit
            if not altered or v != altered[-1][1]:
                altered.append([t, v])
        res = assess(altered)
        need(res["commands_match"] and not res["gpio19"]["raw"]["passed"], "reject stuck input on the selected pair")


def main():
    m = json.loads((HERE / "manifest.json").read_bytes())
    for base, key in ((HERE, "files"), (ROOT, "inputs")):
        for name, digest in m[key].items():
            need(sha(base / name) == digest, name)
    need(verify(ROOT)["profile_sha256"] == m["profile_sha256"], "qualified profile")
    ids = {json.loads((HERE / name / "result.json").read_bytes())["identity_sha256"] for name in SESSIONS}
    need(ids == {m["board_identity_sha256"]}, "single physical board")
    rows = summarize(HERE)
    need(rows == json.loads((HERE / "measurements.json").read_bytes()), "regenerated measurements")
    falsify()
    print(f"{len(rows)*6} physical cases, {sum(v['command_count_passes'] for v in rows.values())} matched command counts, "
          f"{sum(v['gpio19']['raw_pass'] for v in rows.values())} raw GPIO19 decodes, "
          f"{sum(v['gpio27']['raw_pass'] for v in rows.values())} raw GPIO27 decodes; three altered records rejected")


if __name__ == "__main__":
    main()
