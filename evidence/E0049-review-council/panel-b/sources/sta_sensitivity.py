"""Replay G4 fast-corner OpenSTA then impose an extra 125 ps clock uncertainty."""
from contextlib import ExitStack
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

from inspect_retained import source_archive


TOP = "tt_um_khangelani_protocol_emulator"
COMMIT = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"
PDK = Path("/pdk/ciel/ihp-sg13/versions")/COMMIT/"ihp-sg13cmos5l/libs.ref"
LIBRARIES = [
    PDK / "sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_fast_1p32V_m40C.lib",
    PDK / "sg13cmos5l_io/lib/sg13cmos5l_io_fast_1p32V_3p6V_m40C.lib",
    PDK / "sg13cmos5l_sram/lib/RM_IHPSG13_1P_256x32_c2_bm_bist_fast_1p32V_m55C.lib",
]


def memoryfile(stack, name, payload):
    stream = stack.enter_context(os.fdopen(os.memfd_create(name), "w+b"))
    stream.write(payload)
    stream.seek(0)
    return stream.fileno()


def parse_path(text):
    if "_7350_/Q" not in text or "store.program_memory/A_ADDR[6]" not in text:
        raise ValueError("endpoint/path changed\n" + text[-3500:])
    slack = re.search(r"^\s*(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)", text, re.M)
    if not slack:
        raise ValueError("missing slack\n" + text[-3500:])
    keep = ("_7350_/CLK ", "_7350_/Q ", "/A_ADDR[6]", "/A_CLK ", "uncertainty",
            "library hold time", "data required time", "data arrival time", "slack (")
    return {"status": slack[2], "hold_slack_ns": slack[1],
            "path_lines": [l.strip() for l in text.splitlines() if any(k in l for k in keep)]}


def run():
    directory = Path("evidence/E0047-g4-submission-candidate/ci-43543626249")
    result = json.loads((directory/"result.json").read_bytes())
    index = json.loads((directory/"zip-files.json").read_bytes())["GDS_logs"]
    binaries = {"sta_version": subprocess.run(["sta","-version"], capture_output=True,text=True,check=True).stdout.strip()}
    libraries = {p.name:sha256(p.read_bytes()).hexdigest() for p in LIBRARIES}
    if libraries[LIBRARIES[-1].name] != result["macro_views"]["lib/"+LIBRARIES[-1].name]["sha256"]:
        raise ValueError("vendor SRAM Liberty identity differs")
    hashes = {}
    with ExitStack() as stack:
        z = stack.enter_context(source_archive(directory,result,"GDS_logs"))
        fds = []
        for sub, name in (("nl", TOP+".nl.v"),("sdc",TOP+".sdc"),("spef/nom",TOP+".nom.spef")):
            member = f"runs/wokwi/final/{sub}/{name}"
            raw = z.read(member)
            hashes[member] = sha256(raw).hexdigest()
            if hashes[member] != index[member]:
                raise ValueError("final STA input digest differs")
            fds.append(memoryfile(stack, name, raw))
        nl, sdc, spef = (f"/proc/self/fd/{fd}" for fd in fds)
        tcl = [f"read_liberty {p}" for p in LIBRARIES] + [f"read_verilog {nl}", f"link_design {TOP}",
            f"read_sdc {sdc}", f"read_spef {spef}", "puts BASELINE", "report_checks -path_delay min -format full_clock_expanded -digits 6",
            "puts EXTRA_UNCERTAINTY", "set_clock_uncertainty 0.375 [get_clocks clk]",
            "report_checks -path_delay min -format full_clock_expanded -digits 6", "puts END_COUNCIL", "exit"]
        tclfd = memoryfile(stack,"sta-council.tcl",("\n".join(tcl)+"\n").encode())
        command = ["sta","-no_init","-no_splash","-exit",f"/proc/self/fd/{tclfd}"]
        process = subprocess.run(command, pass_fds=(*fds,tclfd), stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, errors="replace", timeout=100)
    log = process.stdout
    if process.returncode or "Error:" in log or "END_COUNCIL" not in log:
        raise ValueError("OpenSTA failed\n" + log[-5000:])
    base, variant = log.split("BASELINE\n",1)[1].split("EXTRA_UNCERTAINTY\n",1)
    a, b = parse_path(base), parse_path(variant)
    if (a["status"] != "MET" or b["status"] != "VIOLATED" or
            abs(Decimal(a["hold_slack_ns"])-Decimal("0.120791")) > Decimal("0.001") or
            abs(Decimal(b["hold_slack_ns"])-Decimal("-0.004209")) > Decimal("0.001")):
        raise ValueError("threshold failed\n"+json.dumps([a,b],indent=2))
    return {"scope":"fresh OpenSTA on retained fast-corner G4 inputs; second condition deliberately hypothetical",
            "binary":binaries, "inputs":hashes, "liberty_sha256":libraries, "pdk_commit":COMMIT,
            "warnings":[l for l in log.splitlines() if "warning" in l.lower()][:14],
            "uncertainty_0p250_ns":a, "uncertainty_0p375_ns":b}


if __name__ == "__main__":
    print(json.dumps(run(),indent=2))
