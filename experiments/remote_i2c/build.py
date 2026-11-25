# SPDX-License-Identifier: Apache-2.0
"""Route the measured open-drain pins on the FabricFox v2."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.fpga_uart.run import PCF, SEED, command, digest, require
from tools.cold_load import fresh_directory
from tools.production_sram import verify


def build(out):
    profile = verify(ROOT)
    sources = [HERE / "fabricfox.v", ROOT / "experiments/fpga_uart/program_ram.v"]
    sources.extend(ROOT / "src" / name for name in profile["source_sha256"])
    script = "read_verilog -sv " + " ".join(map(str, sources)) + "\nsynth_ice40 -top tt_fpga_top -json design.json\n"
    (out / "build.ys").write_text(script)
    command(out, "synth", ["yosys", "-s", "build.ys"])
    design = json.loads((out / "design.json").read_bytes())["modules"]["tt_fpga_top"]
    pads = design["ports"]["uio"]["bits"]
    ios = {c["connections"]["PACKAGE_PIN"][0]: c for c in design["cells"].values() if c["type"] == "SB_IO"}
    require(set(pads) == set(ios), "eight package pins")
    for pin in (1, 2):
        require(ios[pads[pin]]["parameters"]["PIN_TYPE"] == "101001"
                and ios[pads[pin]]["connections"]["D_OUT_0"] == ["0"], "open-drain package output")
    require(ios[pads[1]]["connections"]["OUTPUT_ENABLE"] == ios[pads[4]]["connections"]["D_OUT_0"],
            "pad drive witness")
    require(sum(c["type"] == "SB_RAM40_4K" for c in design["cells"].values()) == 4, "four embedded RAMs")
    command(out, "route", ["nextpnr-ice40", "--up5k", "--package", "sg48", "--seed", str(SEED),
                           "--freq", "12.5", "--pcf", PCF, "--json", "design.json",
                           "--asc", "routed.asc", "--report", "timing.json"])
    timing = json.loads((out / "timing.json").read_bytes())
    clock, = timing["fmax"].values()
    require(clock["constraint"] == 12.5 and clock["achieved"] >= 12.5, "strict internal timing")
    command(out, "pack", ["icepack", "routed.asc", "image.bin"])
    report = dict(profile_sha256=profile["profile_sha256"], clock=clock, resources=timing["utilization"],
                  seed=SEED, image_sha256=digest(out / "image.bin"),
                  source_sha256={p.relative_to(ROOT).as_posix(): digest(p) for p in [*sources, PCF]})
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["image_sha256"], clock)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    build(fresh_directory(parser.parse_args().out))
