"""Prepare and execute the frozen SPI comparison in the Linux workbench."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

from requester import matrix
from revised import ORIGINAL, ROOT, source


HERE = Path(__file__).resolve().parent
COUNCIL = ROOT / "evidence/E0049-review-council"
sys.path.insert(0, str(COUNCIL / "panel-c"))
sys.path.insert(0, str(ORIGINAL.parent))
from spi_target_screen import make_plan
from selector_orders import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES, checked


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_bytes())


REPRESENTATIVE = ("opcode-a4", "opcode-a5", "opcode-00", "uneven-a4", "missing", "late", "early",
                  "missing_reply", "hold-a5-0-1", "hold-a4-0-0", "reselect-a5-250-7-0-1",
                  "reselect-a4-250-7-0-0", "reselect-a5-250-19-7-0", "pause-a5-7-1", "stuck-select-a5")


def prepare(out, tools, smoke):
    out.mkdir(parents=True, exist_ok=False)
    cases = dict(matrix())
    if smoke:
        cases = {name: cases[name] for name in REPRESENTATIVE}
    save(out / "cases.json", cases)
    schedules = out / "schedules"
    schedules.mkdir()
    for name, case in cases.items():
        (schedules / name).write_text("".join(f"{t} {v}\n" for t, v in case["events"]), encoding="ascii")
    ident = json.loads(gzip.decompress((COUNCIL / "panel-a/pio/tool-identities.json.gz").read_bytes()))
    checked((tools / "pioasm").read_bytes(), ident["assembler_binary_sha256"], "pioasm")
    for name, wanted in ident["emulator_members"].items():
        checked((tools / name.removeprefix("package/dist/")).read_bytes(), wanted, name)
    subprocess.run([tools / "pioasm", "-o", "hex", HERE / "target.pio", out / "target.hex"], check=True)
    program = source()
    (out / "revised.asm").write_text(program, encoding="ascii")
    images = {key: make_plan(ROOT, text, out, key) for key, text in
              (("original", ORIGINAL.read_text(encoding="utf-8")), ("revised", program))}
    words = [int(w, 16) for w in (out / "target.hex").read_text().split()]
    images["pio"] = dict(words=len(words), bytes=len(words) * 2,
                         binary_sha256=digest(b"".join(w.to_bytes(2, "little") for w in words)))
    if images["original"]["binary_sha256"] != "8d257ace7cc236c3ff5b2b71242679422f81900b6ee10dbd0daa78a7f318a81e":
        raise ValueError("council image changed")
    save(out / "images.json", images)


def parse_pin_log(raw, case, steps):
    records, applied = {}, []
    loaded = ended = False
    for line in raw.splitlines():
        fields = line.split()
        if fields[:1] == ["PIN"]:
            t, oe, bit, marker, halt = fields[1:]
            records[int(t)] = [int(oe, 16), int(bit), int(marker), int(halt)]
        elif fields[:1] == ["IN"]:
            applied.append([int(s) for s in fields[1:]])
        elif fields[:1] == ["LOAD"]:
            loaded = int(fields[1]) == steps
        elif fields[:1] == ["END"]:
            ended = int(fields[1]) == case["finish"]
    if not (applied == case["events"] and loaded and ended):
        raise ValueError("incomplete requester, cold readback or observation")
    rows = []
    for t, state in records.items():
        if not rows or state != rows[-1][1:]:
            rows.append([t, *state])
    return rows


def vm(out, pdk=None):
    cases = load(out / "cases.json")
    images = load(out / "images.json")
    work = out / ("gate-build" if pdk else "rtl-build")
    work.mkdir(exist_ok=False)
    profile = load(ROOT / "tools/production-profile.json")
    rtl = []
    for name, wanted in profile["files_sha256"].items():
        checked((ROOT / name).read_bytes(), wanted, name)
        if name.startswith("src/") and name.endswith(".v"):
            rtl.append(ROOT / name)
    if len(rtl) != 5:
        raise ValueError("qualified RTL source count")
    models = []
    for name, wanted in profile["model_sha256"].items():
        data = gzip.decompress((ROOT / f"evidence/E0042-sram-prefetch-screen/feasibility/verilog/{name}.gz").read_bytes())
        path = work / name
        path.write_bytes(checked(data, wanted, name))
        models.append(path)
    if pdk:
        archive = ROOT / ARCHIVE
        checked(archive.read_bytes(), ARCHIVE_SHA, ARCHIVE)
        netlist = work / "submission.v"
        with ZipFile(archive) as zipped:
            netlist.write_bytes(checked(zipped.read("tt_submission/tt_um_khangelani_protocol_emulator.v"),
                                        NETLIST_SHA, "submitted netlist"))
        rtl = [netlist]
        for name, wanted in PDK_FILES.items():
            checked((pdk / name).read_bytes(), wanted, name)
            rtl.append(pdk / name)
        cases = {name: cases[name] for name in REPRESENTATIVE}
    executable = work / "target.vvp"
    subprocess.run(["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-DSIM", "-s", "target_tb",
                    "-o", executable, HERE / "target_tb.sv", *rtl, *models], cwd=ROOT, check=True)
    for image in ("original", "revised"):
        steps = images[image]["clocked_load_steps"]
        def trial(item):
            name, case = item
            result = subprocess.run(["vvp", executable, f"+plan={out}/{image}.plan", f"+rows={steps}",
                                     f"+events={out}/schedules/{name}", f"+count={len(case['events'])}",
                                     f"+finish={case['finish']}"], capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise ValueError(f"{image}/{name}: {result.stdout[-500:]} {result.stderr[-500:]}")
            return name, parse_pin_log(result.stdout, case, steps)

        with ThreadPoolExecutor(max_workers=4) as workers:
            observed = dict(workers.map(trial, cases.items()))
        save(out / (image + ("-gate" if pdk else "") + ".json"), observed)
        print(image, "netlist" if pdk else "RTL", len(observed), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "rtl", "gate"])
    parser.add_argument("out", type=Path)
    parser.add_argument("--tools", type=Path, default=Path("/pio-tools"))
    parser.add_argument("--pdk", type=Path, default=Path("/pdk"))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "build"):
        parser.error("scratch belongs under build")
    if args.stage == "prepare":
        prepare(out, args.tools, args.smoke)
    else:
        vm(out, args.pdk if args.stage == "gate" else None)


if __name__ == "__main__":
    main()
