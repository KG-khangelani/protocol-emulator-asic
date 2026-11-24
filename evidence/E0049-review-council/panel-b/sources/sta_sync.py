"""Ordinary placed transfer timing for eight pad synchronizers, three G4 corners."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from inspect_retained import source_archive
from signoff_audit import cells_and_sync_paths
from sta_sensitivity import memoryfile, PDK, TOP


CORNERS = {"fast": ("fast_1p32V_m40C","fast_1p32V_3p6V_m40C","fast_1p32V_m55C"),
           "typical": ("typ_1p20V_25C","typ_1p2V_3p3V_25C","typ_1p20V_25C"),
           "slow": ("slow_1p08V_125C","slow_1p08V_3p0V_125C","slow_1p08V_125C")}


def run():
    base = Path("evidence/E0047-g4-submission-candidate/ci-43543626249")
    result = json.loads((base/"result.json").read_bytes())
    index = json.loads((base/"zip-files.json").read_bytes())["GDS_logs"]
    rows = {}
    with ExitStack() as stack:
        z = stack.enter_context(source_archive(base,result,"GDS_logs"))
        raw = {}
        for sub, name in (("nl",TOP+".nl.v"),("sdc",TOP+".sdc"),("spef/nom",TOP+".nom.spef"),("def",TOP+".def")):
            member = f"runs/wokwi/final/{sub}/{name}"
            raw[sub] = z.read(member)
            if sha256(raw[sub]).hexdigest() != index[member]:
                raise ValueError("STA input mismatch")
        chain = cells_and_sync_paths(raw["nl"].decode(),raw["def"].decode())
        fds = [memoryfile(stack, name, raw[name]) for name in ("nl","sdc","spef/nom")]
        nl,sdc,spef = [f"/proc/self/fd/{fd}" for fd in fds]
        for label, (std, io, sram) in CORNERS.items():
            cells = [PDK/f"sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_{std}.lib",
                     PDK/f"sg13cmos5l_io/lib/sg13cmos5l_io_{io}.lib",
                     PDK/f"sg13cmos5l_sram/lib/RM_IHPSG13_1P_256x32_c2_bm_bist_{sram}.lib"]
            if sha256(cells[-1].read_bytes()).hexdigest() != result["macro_views"]["lib/"+cells[-1].name]["sha256"]:
                raise ValueError("vendor SRAM library identity differed")
            tcl = [f"read_liberty {p}" for p in cells] + [f"read_verilog {nl}",f"link_design {TOP}",
                   f"read_sdc {sdc}",f"read_spef {spef}"]
            for cs in chain:
                a,b,c,d = cs["cells"]
                tcl += [f"puts COUNCIL_BIT_{cs['bit']}",f"report_checks -from [get_cells {a}] -to [get_pins {d}/D] -path_delay max -format full_clock_expanded -digits 6"]
            tcl += ["puts COUNCIL_DONE","exit"]
            script = memoryfile(stack,"synchronizer_transfer.tcl",("\n".join(tcl)+"\n").encode())
            proc = subprocess.run(["sta","-no_init","-no_splash","-exit",f"/proc/self/fd/{script}"],
                                  pass_fds=(*fds,script),capture_output=True,text=True,errors="replace",timeout=100)
            output = proc.stdout + proc.stderr
            if proc.returncode or "Error:" in output or "COUNCIL_DONE" not in output:
                raise ValueError("OpenSTA failed\n"+output[-3000:])
            out = []
            for cs in chain:
                a,b,c,d = cs["cells"]
                one = output.split(f"COUNCIL_BIT_{cs['bit']}\n",1)[1].split("COUNCIL_",1)[0]
                if not all(pin in one for pin in (a+"/Q",b+"/X",c+"/X",d+"/D")):
                    raise ValueError("unexpected path\n"+one)
                slack = re.search(r"^\s*(\S+) +slack \((\w+)\)", one,re.M)
                if not slack or slack[2] != "MET":
                    raise ValueError("missing ordinary setup result\n"+one)
                out.append({"bit":cs["bit"],"ordinary_setup_slack_ns":slack[1]})
            rows[label] = {"transfers":out,"liberty_sha256":{c.name:sha256(c.read_bytes()).hexdigest() for c in cells}}
    return {"scope":"fresh synchronous STA with nominal SPEF and original 20 ns SDC; no metastability characterization",
            "run":result["run_id"],"rows":rows}


if __name__ == "__main__":
    print(json.dumps(run(),indent=2))
