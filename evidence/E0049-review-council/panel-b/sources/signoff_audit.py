"""Read the two retained G4 candidates. Python 3.11+, standard library only."""
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

from inspect_retained import source_archive


TOP = "tt_um_khangelani_protocol_emulator"
CORNERS = ("nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C")
SIGNOFF = "runs/wokwi/60-openroad-stapostpnr/"
FINAL = "runs/wokwi/final/"


def static_path(report, is_hold):
    first = report.split("Startpoint:", 1)[1].split("slack (MET)", 1)[0]
    lines = [line.strip() for line in first.splitlines()]
    arrival = Decimal(next(line.split()[0] for line in lines if "data arrival time" in line))
    required = Decimal(next(line.split()[0] for line in lines if "data required time" in line))
    slack = arrival - required if is_hold else required - arrival
    printed_slack = Decimal(lines[-1].split()[0])
    if slack != printed_slack:
        raise ValueError("printed slack disagrees with endpoint arithmetic")
    relevant = ("clock uncertainty", "library hold time", "library setup time",
                "/A_ADDR[6]", "/A_DOUT[24]", "/A_CLK", "_7350_/Q", "_7350_/CLK",
                "_7498_/D", "_7498_/CLK")
    return {"start": lines[0].split()[0], "end": next(l.split()[1] for l in lines if l.startswith("Endpoint:")),
            "arrival_ns": str(arrival), "required_ns": str(required), "slack_ns": str(slack),
            "selected_native_report_lines": [l for l in lines if any(term in l for term in relevant)]}


def cells_and_sync_paths(netlist, placed):
    cells = {}
    uses = defaultdict(list)
    for item in re.finditer(r"^\s*(sg13cmos5l_\w+)\s+(\S+)\s+\(([^;]+)\);", netlist, re.M):
        kind, name, body = item.groups()
        ports = {pin: wire.strip() for pin, wire in re.findall(r"\.(\w+)\(([^()]+)\)", body)}
        cells[name] = (kind, ports)
        for pin, wire in ports.items():
            uses[wire].append((name, pin))
    locations = {name: (int(x), int(y)) for name, x, y in
                 re.findall(r"^\s*- (\S+) \S+[^\n]*?\+ PLACED \( (\d+) (\d+) \)", placed, re.M)}
    if "UNITS DISTANCE MICRONS 1000 ;" not in placed:
        raise ValueError("unexpected DEF distance units")
    result = []
    for bit in range(8):
        wire = rf"\input_sync.metastability_stage[{bit}]"
        edges = uses[wire]
        launch, = [n for n, pin in edges if pin == "Q"]
        delay, = [n for n, pin in edges if pin == "A"]
        if len(edges) != 2:
            raise ValueError("unexpected first-stage fanout")
        delay_out = cells[delay][1]["X"]
        gate, = [n for n, pin in uses[delay_out] if n != delay and pin == "B"]
        gate_out = cells[gate][1]["X"]
        capture, = [n for n, pin in uses[gate_out] if n != gate and pin == "D"]
        if (len(uses[delay_out]) != 2 or len(uses[gate_out]) != 2 or
                [cells[n][0] for n in (launch, delay, gate, capture)] !=
                ["sg13cmos5l_dfrbpq_1", "sg13cmos5l_dlygate4sd3_1", "sg13cmos5l_and2_1", "sg13cmos5l_dfrbpq_1"] or
                cells[capture][1]["Q"] != rf"\engine.sampled_inputs[{bit}]"):
            raise ValueError(f"unexpected stage chain at bit {bit}")
        result.append({"bit": bit, "cells": [launch, delay, gate, capture],
                       "clock_nets": [cells[n][1]["CLK"] for n in (launch, capture)],
                       "stage1_to_stage2_placement_origin_manhattan_um":
                       sum(abs(a-b) for a,b in zip(locations[launch], locations[capture])) / 1000})
    return result


def sdf_components(sdf, chains):
    if "(TIMESCALE 1ns)" not in sdf or "(DIVIDER .)" not in sdf:
        raise ValueError("unexpected SDF units or hierarchy divider")
    blocks = {m[1]: m[2] for m in re.finditer(r"\(INSTANCE ([^)]+)\)(.*?)(?=\n \(CELL|\Z)", sdf, re.S)}
    wires = {f"{a} {b}": data for a, b, data in re.findall(r"\(INTERCONNECT (\S+) (\S+) ([^\n]+)", sdf)}

    def peak(row):
        return max(Decimal(n) for n in re.findall(r"-?\d+\.\d+", row))

    def max_arc(name, function):
        matches = [peak(line) for line in blocks[name].splitlines() if function in line]
        if not matches:
            raise ValueError(f"missing {function} arc for {name}")
        return max(matches)

    values = []
    for chain in chains:
        a, b, c, d = chain["cells"]
        segments = (f"{a}.Q {b}.A", f"{b}.X {c}.B", f"{c}.X {d}.D")
        q_to_d = sum(peak(wires[k]) for k in segments) + max_arc(b, "IOPATH A X") + max_arc(c, "IOPATH B X")
        values.append({"bit": chain["bit"], "normal_clk_to_q_ns": str(max_arc(a, "IOPATH CLK Q")),
                       "conservative_q_to_d_ns": str(q_to_d), "capture_setup_ns": str(max_arc(d, "(SETUP "))})
    return values


def gds_features(payload):
    # GDSII record types use a one-byte type and one-byte data format after a 16-bit length.
    data = memoryview(payload)
    offset = 0
    in_top = False
    layer = purpose = element = None
    points = []
    shapes = defaultdict(set)
    labels = {}
    while offset < len(data):
        length, typ, _ = struct.unpack_from(">HBB", data, offset)
        if length < 4 or offset + length > len(data):
            raise ValueError("invalid GDS record length")
        value = data[offset+4:offset+length]
        offset += length
        if typ == 3:  # UNITS, second IBM real is meters per database unit.
            raw = value[8:]
            meters = 16**((raw[0] & 127)-64) * int.from_bytes(raw[1:], "big") / 2**56
            if abs(meters - 1e-9) > 1e-15:
                raise ValueError("expected 1 nm database unit")
        if typ == 6:
            in_top = bytes(value).rstrip(b"\0").decode() == TOP
        if not in_top:
            continue
        if typ in (8, 9, 10, 11, 12, 21, 45):
            element, layer, purpose, points = typ, None, None, []
        elif typ == 13:
            layer, = struct.unpack(">H", value)
        elif typ in (14, 22, 46):
            purpose, = struct.unpack(">H", value)
        elif typ == 16:
            points = list(struct.iter_unpack(">ii", value))
        elif typ == 25 and element == 12 and (layer, purpose) == (50, 25):
            label = bytes(value).rstrip(b"\0").decode()
            if label in ("VPWR", "VGND"):
                if label in labels or len(points) != 1:
                    raise ValueError("unexpected duplicate or displaced supply label")
                labels[label] = points[0]
        elif typ == 17 and element == 8 and layer == 50 and purpose in (0, 2) and len(points) == 5:
            x, y = zip(*points)
            x1, x2, y1, y2 = min(x), max(x), min(y), max(y)
            if (points[0] == points[-1] and set(points) == {(x1,y1), (x1,y2), (x2,y1), (x2,y2)}
                    and x2-x1 == 2100 and y2-y1 > 690000):
                shapes[purpose].add((x1, y1, x2, y2))
    return shapes, labels


def verify_supply(ports, shapes, labels):
    if len(ports["VPWR"]) != 27 or len(ports["VGND"]) != 27:
        raise ValueError("LEF full-height count")
    both = ports["VPWR"] | ports["VGND"]
    if len(both) != 54 or shapes[0] != both or shapes[2] != both:
        raise ValueError("GDS drawing/pin and LEF port mismatch")
    for net, boxes in ports.items():
        x, y = labels[net]
        if not any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in boxes):
            raise ValueError("GDS label outside same-net LEF strip")
        if any(y1 != 3560 or y2 != 707080 or x2-x1 != 2100 for x1,y1,x2,y2 in boxes):
            raise ValueError("unexpected supply dimensions")


def supply_geometry(gds, lef):
    if "SIZE 1724.160 BY 710.640" not in lef and "SIZE 1724.16 BY 710.64" not in lef:
        raise ValueError("unexpected LEF size")
    ports = {}
    for net in ("VGND", "VPWR"):
        section = lef.split(f"  PIN {net}\n",1)[1].split(f"  END {net}",1)[0]
        if set(re.findall(r"LAYER (\w+) ;", section)) != {"Metal4"}:
            raise ValueError("unexpected supply layer")
        ports[net] = {tuple(int(Decimal(x)*1000) for x in row.split())
                      for row in re.findall(r"RECT ([0-9. ]+) ;", section)}
    shapes, labels = gds_features(gds)
    verify_supply(ports, shapes, labels)
    missing = {k: set(v) for k,v in shapes.items()}
    missing[2].remove(min(missing[2]))
    swapped = {"VPWR": labels["VGND"], "VGND": labels["VPWR"]}
    for mutated_shapes, mutated_labels in ((missing, labels), (shapes, swapped)):
        try:
            verify_supply(ports, mutated_shapes, mutated_labels)
        except ValueError:
            continue
        raise AssertionError("geometry checker accepted negative control")
    return {"strips_per_net": {k: len(v) for k,v in ports.items()}, "die_nm": [1724160,710640],
            "width_nm": 2100, "y1_y2_nm": [3560,707080], "top_gds_full_strips_on_each_layer_purpose":
            {f"50/{k}": len(v) for k,v in shapes.items()}, "labels_50_25_nm": labels,
            "missing_strip_rejected": True, "swapped_labels_rejected": True}


def audit(directory):
    result = json.loads((directory/"result.json").read_bytes())
    manifest = json.loads((directory/"zip-files.json").read_bytes())
    refs = {}

    def read(archive, key, path):
        raw = archive.read(path)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest[key][path]:
            raise ValueError(f"member digest failed for {path}")
        refs[f"{key}/{path}"] = digest
        return raw

    with source_archive(directory, result, "tt_submission") as archive:
        prefix = f"tt_submission/{TOP}"
        gds = read(archive, "tt_submission", prefix+".gds")
        lef = read(archive, "tt_submission", prefix+".lef").decode()
        netlist = read(archive, "tt_submission", prefix+".v").decode()
        geometry = supply_geometry(gds, lef)
    with source_archive(directory, result, "GDS_logs") as archive:
        def log(path):
            return read(archive, "GDS_logs", path).decode()
        paths = [static_path(log(f"{SIGNOFF}{CORNERS[0]}/min.rpt"), True),
                 static_path(log(f"{SIGNOFF}{CORNERS[2]}/max.rpt"), False)]
        chains = cells_and_sync_paths(netlist, log(f"{FINAL}def/{TOP}.def"))
        timing = {corner: sdf_components(log(f"{FINAL}sdf/{corner}/{TOP}__{corner}.sdf"), chains)
                  for corner in CORNERS}
        power = log(f"{SIGNOFF}{CORNERS[1]}/power.rpt")
        power_by_group = {m[1]: m[2] for m in re.finditer(r"^(Sequential|Combinational|Clock|Macro|Pad|Total)\s+(?:\S+\s+){3}(\S+)", power, re.M)}
        ir = log("runs/wokwi/61-openroad-irdropreport/irdrop.rpt")
        ir_drop = dict(re.findall(r"Net\s+: (\w+).*?Worstcase IR drop: (\S+) V", ir, re.S))
        parasitics = [n for n in archive.namelist() if n.startswith(FINAL+"spef/") and n.endswith(".spef")]
    with source_archive(directory, result, "precheck_reports") as archive:
        tree = ET.fromstring(read(archive, "precheck_reports", "drc_sg13cmos5l.xml"))
        categories = [c.findtext("name") for c in tree.findall("categories/category")]
        counts = {"categories": len(categories), "items": len(tree.findall("items/item")),
                  "contact_rules": [s for s in categories if s in ("Cnt.c", "Cnt.c.SRAM", "Cnt.c.digibnd")]}
    fingerprint = {"static_paths": paths, "supply": geometry, "stages": chains, "sdf_ns": timing,
                   "power_W": power_by_group, "typical_static_IR_drop_V": ir_drop,
                   "extracted_parasitics": parasitics, "official_klayout_report": counts}
    return fingerprint, {"run": result["run_id"], "hashed_members": refs}


if __name__ == "__main__":
    base = Path("evidence/E0047-g4-submission-candidate")
    runs = [audit(base/f"ci-{n}") for n in (43543626249,43543629839)]
    if runs[0][0] != runs[1][0]:
        raise ValueError("physical observations differ between the two G4 runs")
    print(json.dumps({"scope": "New extraction from retained artifacts; no fresh P&R or silicon",
                      "observations": runs[0][0], "matched_runs": [x[1] for x in runs]}, indent=2))
