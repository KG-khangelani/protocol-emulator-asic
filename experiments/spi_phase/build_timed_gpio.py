# SPDX-License-Identifier: Apache-2.0
"""Isolated timed variants; production and the historical builder are immutable."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
from build_variants import ROOT, FILES, phase_engine, banked_store, banked_top, once

def timed_engine(compact, variant):
    if variant not in ("P", "F"):
        raise ValueError(variant)
    delay = "{10'd0, instruction[29:24]}" if variant == "P" else "{11'd0, instruction[28:24]}"
    text = once(compact, "    wire set_valid = (instruction[29:24] == 6'b0);",
        "    wire [15:0] gpio_delay = " + delay + ";\n"
        "    wire [7:0] gpio_next_value = (gpio_value & ~instruction[23:16]) |\n"
        "                                  (instruction[7:0] & instruction[23:16]);\n"
        "    wire [7:0] gpio_next_oe = (gpio_oe & ~instruction[23:16]) |\n"
        "                               (instruction[15:8] & instruction[23:16]);")
    start = text.index("                            OpSet: begin")
    end = text.index("                            OpWait: begin", start)
    pre = """
                                    if (instruction[29]) begin
                                        gpio_pending <= 1'b1;
                                        gpio_pending_value <= gpio_next_value;
                                        gpio_pending_oe <= gpio_next_oe;
                                    end else begin
                                        gpio_value <= gpio_next_value;
                                        gpio_oe <= gpio_next_oe;
                                    end
""" if variant == "F" else """
                                    gpio_value <= gpio_next_value;
                                    gpio_oe <= gpio_next_oe;
"""
    block = """                            OpSet: begin
                                if (gpio_delay == 16'd0) begin
                                    gpio_value <= gpio_next_value;
                                    gpio_oe <= gpio_next_oe;
                                    advance_pc(); wait_left <= 16'd0;
                                end else begin
                                    wait_is_input <= 1'b0;
                                    shift_period <= 16'd0;
                                    state <= Waiting; wait_left <= gpio_delay;
""" + pre + """                                end
                            end
"""
    text = text[:start] + block + text[end:]
    if variant == "P":
        text = once(text, """    wire phase_drive_valid = phase_drive_word && phase_pins_valid &&
                             (instruction[2:0] == 3'd0) &&""",
                    "    wire phase_drive_valid = phase_drive_word && phase_pins_valid &&")
        text = once(text, """                                        advance_pc();
                                    end
                                end else if (phase_sample_word) begin""",
                    """                                        if (instruction[2:0] == 3'd0)
                                            advance_pc();
                                        else begin
                                            state <= Waiting;
                                            wait_left <= {11'd0, instruction[2:0], 2'b00};
                                        end
                                    end
                                end else if (phase_sample_word) begin""")
    else:
        text = once(text, "    reg phase_active;", """    reg gpio_pending;
    reg [7:0] gpio_pending_value, gpio_pending_oe;
    reg phase_active;""")
        text = once(text, "            phase_active <= 1'b0; phase_prepared <= 1'b0;",
                    """            phase_active <= 1'b0; phase_prepared <= 1'b0;
            gpio_pending <= 1'b0;
            gpio_pending_value <= 8'd0; gpio_pending_oe <= 8'd0;""")
        text = once(text, """                Waiting: begin
                    if (shift_period == 16'd1) begin""", """                Waiting: begin
                    if (gpio_pending) begin
                        if (wait_left > 16'd1)
                            wait_left <= wait_left - 16'd1;
                        else begin
                            gpio_value <= gpio_pending_value;
                            gpio_oe <= gpio_pending_oe;
                            gpio_pending <= 1'b0;
                            wait_left <= 16'd0;
                            advance_pc(); state <= Run;
                        end
                    end else if (shift_period == 16'd1) begin""")
    return text

def build(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("isolated build/ output required")
    expected = json.loads((ROOT/"evidence/E0020-spi-mode0-feasibility/result.json").read_text())["unchanged_source_sha256"]
    original = {name:(ROOT/"src"/name).read_text(encoding="utf-8") for name in FILES}
    for name in FILES:
        assert hashlib.sha256((ROOT/"src"/name).read_bytes()).hexdigest() == expected["src/"+name]
    compact = phase_engine(original["m1_engine.v"], True)
    assert hashlib.sha256(compact.encode()).hexdigest() == "b429d48e87993f3878aca37f804b2758fa439dc80afc275317e6a10c91d0eaa0"
    manifests = {}
    for variant in ("compact8", "compact10", "P", "F"):
        files = dict(original)
        files["m1_engine.v"] = timed_engine(compact, variant) if variant in ("P","F") else compact
        if variant == "compact10":
            files["m1_program_store.v"] = banked_store(original["m1_program_store.v"])
            files["project.v"] = banked_top(original["project.v"])
        directory = output/variant/"src"
        directory.mkdir(parents=True, exist_ok=True)
        hashes, patch = {}, []
        for name, source in files.items():
            (directory/name).write_bytes(source.encode())
            hashes[name] = hashlib.sha256(source.encode()).hexdigest()
            patch.extend(difflib.unified_diff(original[name].splitlines(True), source.splitlines(True),
                                             fromfile="src/"+name, tofile=variant+"/"+name))
        (directory.parent/"source.patch").write_text("".join(patch), encoding="utf-8", newline="\n")
        manifests[variant] = {"directory":str(directory), "source_sha256":hashes}
    (output/"source-manifest.json").write_text(json.dumps(manifests,indent=2)+"\n")
    return manifests

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output),indent=2))
