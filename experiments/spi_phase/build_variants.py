# SPDX-License-Identifier: Apache-2.0
"""Reproducible experimental copies; never edits production RTL.

All replacement anchors and E0020 baseline hashes must match. Generated source
and diffs live only under build/. This is not a production ISA implementation.
"""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
from legacy_baseline import FILES, baseline_sources

ROOT = Path(__file__).resolve().parents[2]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"experimental patch anchor count !=1: {old[:70]!r}")
    return text.replace(old, new, 1)


PHASE_WIRES = """
    reg phase_active;
    reg phase_prepared;
    wire phase_drive_word = instruction[29] && !instruction[21] &&
                            (instruction[20:19] == 2'b01);
    wire phase_sample_word = instruction[29] && !instruction[21] &&
                             (instruction[20:19] == 2'b10);
    wire [7:0] phase_aux_mask = COMPACT_PHASE ? instruction[18:11] : 8'd0;
    wire [7:0] phase_aux_value = COMPACT_PHASE ? instruction[10:3] : 8'd0;
    wire [15:0] phase_delay = instruction[18:3];
    wire phase_pins_valid = (instruction[27:25] != instruction[24:22]);
    wire phase_drive_valid = phase_drive_word && phase_pins_valid &&
                             (instruction[2:0] == 3'd0) &&
                             (COMPACT_PHASE || (instruction[18:0] == 19'd0)) &&
                             ((phase_aux_mask & (shift_tx_mask | shift_rx_mask)) == 8'd0) &&
                             (!shift_active ? (!phase_active && !phase_prepared) :
                              (phase_active && !phase_prepared && shift_config_matches));
    wire phase_sample_valid = phase_sample_word && phase_pins_valid &&
                              (instruction[2:0] == 3'd0) &&
                              (COMPACT_PHASE || (instruction[18:0] == 19'd0)) &&
                              phase_active && phase_prepared && shift_active &&
                              shift_config_matches;
"""

PHASE_CAPTURE = """
    task automatic capture_phase_sample;
        begin
            shift_rx_data <= shift_rx_next;
            phase_prepared <= 1'b0;
            if (shift_bits_done == 3'd7) begin
                shift_active <= 1'b0;
                shift_bits_done <= 3'd0;
                phase_active <= 1'b0;
            end else
                shift_bits_done <= shift_bits_done + 3'd1;
            shift_period <= 16'd0;
            wait_left <= 16'd0;
            advance_pc();
            state <= Run;
        end
    endtask

"""

PHASE_HALT = """                            OpHalt: begin
                                wait_is_input <= 1'b0;
                                wait_left <= 16'd0;
                                if (!instruction[29]) begin
                                    state <= (halt_valid && !loop_active && !shift_active) ?
                                             Halted : Faulted;
                                end else if (phase_drive_word) begin
                                    if (!phase_drive_valid) begin
                                        state <= Faulted;
                                    end else begin
                                        gpio_value <= (gpio_value & ~phase_aux_mask & ~shift_tx_mask) |
                                                      (phase_aux_value & phase_aux_mask) |
                                                      (selected_shift_tx_bit ? shift_tx_mask : 8'd0);
                                        gpio_oe <= (gpio_oe | phase_aux_mask | shift_tx_mask) & ~shift_rx_mask;
                                        phase_active <= 1'b1;
                                        phase_prepared <= 1'b1;
                                        shift_period <= 16'd0;
                                        if (!shift_active) begin
                                            shift_active <= 1'b1;
                                            shift_bits_done <= 3'd0;
                                            shift_rx_data <= 8'd0;
                                            shift_msb_first <= instruction[28];
                                            shift_tx_pin <= instruction[27:25];
                                            shift_rx_pin <= instruction[24:22];
                                            shift_tx_data <= instruction[28] ?
                                                             {selected_payload[6:0], 1'b0} :
                                                             {1'b0, selected_payload[7:1]};
                                        end else
                                            shift_tx_data <= shift_msb_first ?
                                                             {shift_tx_data[6:0], 1'b0} :
                                                             {1'b0, shift_tx_data[7:1]};
                                        advance_pc();
                                    end
                                end else if (phase_sample_word) begin
                                    if (!phase_sample_valid) begin
                                        state <= Faulted;
                                    end else if (phase_delay == 16'd0) begin
                                        capture_phase_sample();
                                    end else begin
                                        state <= Waiting;
                                        wait_left <= phase_delay;
                                        shift_period <= 16'd1;
                                    end
                                end else if (!shift_valid || phase_active ||
                                             (shift_active && !shift_config_matches)) begin
                                    state <= Faulted;
                                end else begin
                                    gpio_value <= (gpio_value & ~shift_tx_mask) |
                                                  (selected_shift_tx_bit ? shift_tx_mask : 8'd0);
                                    gpio_oe <= (gpio_oe | shift_tx_mask) & ~shift_rx_mask;
                                    shift_rx_data <= shift_rx_next;
                                    if (!shift_active) begin
                                        shift_active <= 1'b1;
                                        shift_bits_done <= 3'd1;
                                        shift_msb_first <= instruction[28];
                                        shift_tx_pin <= instruction[27:25];
                                        shift_rx_pin <= instruction[24:22];
                                        shift_period <= instruction_shift_burst ?
                                                        instruction_shift_period : 16'd0;
                                        shift_tx_data <= instruction[28] ?
                                                         {selected_payload[6:0], 1'b0} :
                                                         {1'b0, selected_payload[7:1]};
                                    end else begin
                                        shift_tx_data <= shift_msb_first ?
                                                         {shift_tx_data[6:0], 1'b0} :
                                                         {1'b0, shift_tx_data[7:1]};
                                        if (shift_bits_done == 3'd7) begin
                                            shift_active <= 1'b0;
                                            shift_bits_done <= 3'd0;
                                        end else
                                            shift_bits_done <= shift_bits_done + 3'd1;
                                    end
                                    if (instruction_shift_burst) begin
                                        state <= Waiting;
                                        wait_left <= instruction_shift_period;
                                    end else
                                        advance_pc();
                                end
                            end
"""


def phase_engine(source, compact):
    text = once(source, "module m1_engine (", "module m1_engine #(parameter [0:0] COMPACT_PHASE = 1'b" + str(int(compact)) + ") (")
    text = once(text, "    assign shift_result_write =", PHASE_WIRES + "    assign shift_result_write =")
    text = once(text, "    assign shift_burst_status = (shift_period != 16'd0);",
                "    assign shift_burst_status = (shift_period >= 16'd2);")
    start = text.index("    assign shift_result_write =")
    end = text.index("    assign shift_result_data =", start)
    text = text[:start] + """    assign shift_result_write = rst_n && ena &&
        (((state == Run) && instruction_valid && (opcode == OpHalt) &&
          ((shift_valid && !phase_active && shift_active && shift_config_matches &&
            (shift_bits_done == 3'd7)) ||
           (phase_sample_valid && (phase_delay == 16'd0) && (shift_bits_done == 3'd7)))) ||
         ((state == Waiting) && (wait_left == 16'd1) && shift_active &&
          (shift_bits_done == 3'd7) &&
          (((shift_period >= 16'd2) && !phase_active) ||
           ((shift_period == 16'd1) && phase_active && phase_prepared))));
""" + text[end:]
    text = once(text, "    always @(posedge clk) begin", PHASE_CAPTURE + "    always @(posedge clk) begin")
    text = once(text, "            shift_period <= 16'd0; shift_tx_slot <= 1'b0;",
                "            shift_period <= 16'd0; shift_tx_slot <= 1'b0;\n            phase_active <= 1'b0; phase_prepared <= 1'b0;")
    text = once(text, "                    if (shift_period != 16'd0) begin", """                    if (shift_period == 16'd1) begin
                        if (!phase_active || !phase_prepared || !shift_active) begin
                            state <= Faulted; wait_left <= 16'd0;
                        end else if (wait_left > 16'd1)
                            wait_left <= wait_left - 16'd1;
                        else
                            capture_phase_sample();
                    end else if (shift_period >= 16'd2) begin""")
    start = text.index("                            OpHalt: begin")
    end = text.index("                            OpWaitPin: begin", start)
    return text[:start] + PHASE_HALT + text[end:]


def banked_store(source):
    text = once(source, "input wire load_mode, input wire load_write, input wire load_length,",
                "input wire load_mode, input wire load_write, input wire load_length, input wire load_bank,")
    text = once(text, "output reg program_ready, output reg [31:0] instruction,",
                "output reg program_ready, output reg program_bank, output reg [31:0] instruction,")
    text = once(text, "    reg [31:0] word4, word5, word6, word7;",
                "    reg [31:0] word4, word5, word6, word7;\n    reg [31:0] word8, word9;\n    wire [5:0] bank_address = {program_bank, byte_address};")
    text = once(text, "(data_in[3:0] <= 4'd8)", "(data_in[3:0] <= 4'd10)")
    text = once(text, "            program_length <= 4'd0;", "            word8 <= 32'd0; word9 <= 32'd0; program_bank <= 1'b0;\n            program_length <= 4'd0;")
    text = once(text, "            if (load_length) begin", """            if (load_bank) begin
                program_bank <= (data_in <= 8'd1) ? data_in[0] : 1'b0;
                program_length <= 4'd0;
                program_ready <= 1'b0;
            end else if (load_length) begin
                program_bank <= 1'b0;""")
    text = text.replace("case (byte_address[4:2])", "case (bank_address[5:2])")
    for index in range(7):
        text = text.replace(f"3'd{index}: word", f"4'd{index}: word").replace(f"3'd{index}: data_out", f"4'd{index}: data_out")
    text = once(text, "                    default: word7[8*byte_address[1:0] +: 8] <= data_in;", """                    4'd7: word7[8*byte_address[1:0] +: 8] <= data_in;
                    4'd8: word8[8*byte_address[1:0] +: 8] <= data_in;
                    4'd9: word9[8*byte_address[1:0] +: 8] <= data_in;
                    default: begin end""")
    text = once(text, "            default: data_out = word7[8*byte_address[1:0] +: 8];", """            4'd7: data_out = word7[8*byte_address[1:0] +: 8];
            4'd8: data_out = word8[8*byte_address[1:0] +: 8];
            4'd9: data_out = word9[8*byte_address[1:0] +: 8];
            default: data_out = 8'd0;""")
    text = once(text, "case (pc[2:0])", "case (pc[3:0])")
    for index in range(7):
        text = text.replace(f"3'd{index}: instruction", f"4'd{index}: instruction")
    text = once(text, "            default: instruction = word7;", """            4'd7: instruction = word7;
            4'd8: instruction = word8;
            4'd9: instruction = word9;
            default: instruction = 32'd0;""")
    text = once(text, "(pc < 5'd8)", "(pc < 5'd10)")
    return text


def banked_top(source):
    text = once(source, "    wire [7:0] register_data_out;", """    wire [7:0] register_data_out;
    wire [7:0] register_data_out_raw;
    wire program_bank;
    assign register_data_out = (byte_address == 5'd5) ? {7'd0, program_bank} : register_data_out_raw;""")
    text = once(text, "(!load_register || (byte_address == 5'd0));",
                "(!load_register || (byte_address == 5'd0) || (byte_address == 5'd5));")
    text = once(text, "        .load_length(load_register),", """        .load_length(load_register), .load_bank(load_register && (byte_address == 5'd5)),
        .program_bank(program_bank),""")
    text = once(text, ".data_out(register_data_out),", ".data_out(register_data_out_raw),")
    return once(text, "                default: assert (uo_out == 8'b0);",
                "                5'd5: assert (uo_out == {7'd0, program_bank});\n                default: assert (uo_out == 8'b0);")


def build(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("experimental output must remain under ignored build/")
    original = baseline_sources()
    result = {}
    for variant in ("baseline", "compact", "banked"):
        directory = output / variant / "src"
        directory.mkdir(parents=True, exist_ok=True)
        files = dict(original)
        if variant != "baseline":
            files["m1_engine.v"] = phase_engine(original["m1_engine.v"], variant == "compact")
        if variant == "banked":
            files["m1_program_store.v"] = banked_store(original["m1_program_store.v"])
            files["project.v"] = banked_top(original["project.v"])
        patch, hashes = [], {}
        for name, source in files.items():
            (directory / name).write_bytes(source.encode())
            hashes[name] = hashlib.sha256(source.encode()).hexdigest()
            patch.extend(difflib.unified_diff(original[name].splitlines(True), source.splitlines(True),
                                             fromfile="experiments/spi_phase/baseline/" + name, tofile=variant + "/" + name))
        (directory.parent / "source.patch").write_bytes("".join(patch).encode())
        result[variant] = {"directory": str(directory), "source_sha256": hashes}
    (output / "source-manifest.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/spi-phase-comparison")
    print(json.dumps(build(parser.parse_args().output), indent=2))
