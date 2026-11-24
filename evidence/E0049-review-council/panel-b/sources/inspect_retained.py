"""Read original G4 ZIPs in place and calculate one conditional wire-margin example.

Invoke from the repository root. Output is JSON. The electrical calculation
applies hypothesized transition times to two actual RTL-netlist drive events.
It does not model the feedback-dependent transaction following that edge.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bound(archive, index, name):
    raw = archive.read(name)
    if sha(raw) != index[name]:
        raise ValueError(f"member hash mismatch: {name}")
    return raw.decode()


def source_archive(directory, result, label):
    reference = result["archives"][label]
    path = directory / f"{reference['id']}.zip"
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != reference["sha256"]:
            raise ValueError(f"archive hash mismatch: {path.name}")
    return zipfile.ZipFile(path)


def inspect(directory):
    result = json.loads((directory / "result.json").read_bytes())
    index = json.loads((directory / "zip-files.json").read_bytes())
    paths = []
    with source_archive(directory, result, "GDS_logs") as logs:
        members = index["GDS_logs"]
        for corner, delay, slack in (("nom_fast_1p32V_m40C", "min", "hold"),
                                     ("nom_slow_1p08V_125C", "max", "setup")):
            name = f"runs/wokwi/60-openroad-stapostpnr/{corner}/{delay}.rpt"
            first = read_bound(logs, members, name).split("Startpoint:")[1].split("slack (MET)")[0]
            end = re.search(r"^Endpoint: (\S+)", first, re.M).group(1)
            pins = sorted(set(re.findall(r"store\.program_memory/(A_ADDR\[\d+\]|A_DOUT\[\d+\])", first)))
            paths.append({"member": name, "member_sha256": members[name], "startpoint": first.split()[0],
                          "endpoint": end, "macro_data_pin": pins,
                          "slack_ns": result["physical_metrics"]["checked"][f"timing__{slack}__ws__corner:{corner}"]})
        sdc = "runs/wokwi/final/sdc/tt_um_khangelani_protocol_emulator.sdc"
        sdc_lines = read_bound(logs, members, sdc).splitlines()
        witnesses = [next(l for l in sdc_lines if l.startswith(prefix))
                     for prefix in ("create_clock", "set_clock_uncertainty", "set_input_delay", "set_output_delay")]
    with source_archive(directory, result, "gatelevel_test_results") as tests:
        name = "output/i2c/write_read-96.json"
        rows = json.loads(read_bound(tests, index["gatelevel_test_results"], name))
        if rows["record"]["outcome"] != "OK" or rows["record"]["accepted"] is not True:
            raise ValueError("expected a passing write/read")
        last_scl_fall = None
        pairs = []
        for prev, row in zip(rows["trace"], rows["trace"][1:]):
            if prev["bus"] & 1 and not (row["bus"] & 1):
                last_scl_fall = row["t"]
            if (last_scl_fall is not None and not (row["bus"] & 1)
                    and prev["bus"] & 2 and not (row["bus"] & 2)
                    and not (prev["oe"] & 2) and row["oe"] & 2 and not (row["target_oe"] & 2)):
                pairs.append((row["t"] - last_scl_fall, last_scl_fall, row["t"]))
        ticks, scl, sda = min(pairs)
        transition = {"member": name, "member_sha256": index["gatelevel_test_results"][name],
                      "tick_ns": 5, "scl_fall_tick": scl, "controller_sda_fall_tick": sda,
                      "minimum_gap_ns": ticks * 5, "observed_fastest_clock_hz": rows["record"]["fastest_hz"]}
    return {"run_id": result["run_id"], "producer_commit": result["source_commit"],
            "paths": paths, "sdc_member": sdc, "sdc_lines": witnesses, "i2c_witness": transition}


def timing(gap, scl_fall_ns, sda_fall_ns):
    # tf is the 70%-to-30% width. Starting at VDD, t(x) = -ln(x) * tau.
    denominator = math.log(0.7 / 0.3)
    scl_low = -math.log(0.3) / denominator * scl_fall_ns
    sda_leaves_high = gap - math.log(0.7) / denominator * sda_fall_ns
    return {"scl_fall_70_to_30_ns": scl_fall_ns, "sda_fall_70_to_30_ns": sda_fall_ns,
            "scl_reaches_30_ns": round(scl_low, 4), "sda_reaches_70_ns": round(sda_leaves_high, 4),
            "ordering_margin_ns": round(sda_leaves_high - scl_low, 4)}


if __name__ == "__main__":
    base = Path("evidence/E0047-g4-submission-candidate")
    runs = [inspect(base / f"ci-{number}") for number in (43543626249, 43543629839)]
    if runs[0]["i2c_witness"] != runs[1]["i2c_witness"] or runs[0]["paths"] != runs[1]["paths"]:
        raise ValueError("independent reproductions disagree on the chosen observations")
    gap = runs[0]["i2c_witness"]["minimum_gap_ns"]
    modeled = [timing(gap, *pair) for pair in ((10, 10), (20, 20), (100, 20))]
    print(json.dumps({"g4_archives": runs, "falling_edge_models": modeled}, indent=2))
