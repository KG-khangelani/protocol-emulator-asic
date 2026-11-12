# SPDX-License-Identifier: Apache-2.0
"""Isolated general I/O candidates derived from the qualified compact10 RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"experiments/spi_phase"))
from build_timed_gpio import build as build_legacy
from build_variants import FILES, once


def engine(source, serial_options):
    s = source.replace("output reg [4:0] pc", "output reg [7:0] pc")
    s = once(s, "parameter [0:0] COMPACT_PHASE", "parameter reg [0:0] COMPACT_PHASE")
    s = s.replace("[4:0] loop_", "[7:0] loop_")
    s = once(s, "wire [5:0] loop_target_wide = {1'b0, pc} + 6'd1 +\n                                  {1'b0, instruction[28:24]};",
             "wire [8:0] loop_target_wide = {1'b0, pc} + 9'd1 +\n                                  {4'd0, instruction[28:24]};")
    s = s.replace("loop_target_wide[5]", "loop_target_wide[8]")
    s = s.replace("loop_target_wide[4:0]", "loop_target_wide[7:0]")
    for n in (1, 2):
        s = s.replace(f"pc + 5'd{n}", f"pc + 8'd{n}")
    for name in ("pc", "loop_start", "loop_end"):
        s = s.replace(f"{name} <= 5'd0", f"{name} <= 8'd0")
    s = once(s, "    reg wait_timeout_skip;", "    reg wait_timeout_skip;\n    reg wait_timeout_jump;\n    reg [7:0] wait_failure_pc;")
    s = once(s, "    wire wait_pin_valid = (instruction[24:16] == 9'b0);",
             "    wire wait_pin_valid = instruction[24] ? !instruction[25] :\n                          (instruction[23:16] == 8'd0);")
    task = """    task automatic abort_to(input reg [7:0] destination);
        begin
            pc <= destination;
            state <= Run;
            wait_left <= 16'd0;
            wait_is_input <= 1'b0;
            wait_timeout_skip <= 1'b0;
            wait_timeout_jump <= 1'b0;
            wait_failure_pc <= 8'd0;
            loop_active <= 1'b0;
            loop_remaining <= 8'd0;
            loop_start <= 8'd0;
            loop_end <= 8'd0;
            shift_active <= 1'b0;
            shift_bits_done <= 3'd0;
            shift_period <= 16'd0;
            phase_active <= 1'b0;
            phase_prepared <= 1'b0;
        end
    endtask

"""
    s = once(s, "    task automatic advance_pc;", task+"    task automatic advance_pc;")
    s = once(s, "            wait_timeout_skip <= 1'b0;\n            loop_active", "            wait_timeout_skip <= 1'b0;\n            wait_timeout_jump <= 1'b0; wait_failure_pc <= 8'd0;\n            loop_active")
    s = once(s, "                        if (wait_timeout_skip && !loop_active) begin",
             "                        if (wait_timeout_jump) begin\n                            abort_to(wait_failure_pc);\n                        end else if (wait_timeout_skip && !loop_active) begin")
    s = once(s, "                                    if (instruction[25] && !loop_active)\n                                        pc <= pc + 8'd2;",
             "                                    if (instruction[24])\n                                        abort_to(instruction[23:16]);\n                                    else if (instruction[25] && !loop_active)\n                                        pc <= pc + 8'd2;")
    s = once(s, "                                    wait_timeout_skip <= instruction[25];",
             "                                    wait_timeout_skip <= instruction[25];\n                                    wait_timeout_jump <= instruction[24];\n                                    wait_failure_pc <= instruction[23:16];")
    # A skip from word 254 must fault instead of wrapping the eight-bit PC.
    s = once(s, "wait_timeout_skip && !loop_active", "wait_timeout_skip && !loop_active && (pc <= 8'd253)")
    s = once(s, "instruction[25] && !loop_active", "instruction[25] && !loop_active && (pc <= 8'd253)")
    if serial_options:
        s = once(s, "(instruction[20:0] == 21'd0)", "(instruction[20:2] == 19'd0)")
        s = once(s, "    wire [7:0] selected_payload = (instruction_shift_burst && shift_tx_slot) ?",
                 "    wire serial_open_drain = !instruction_shift_burst && instruction[0];\n"
                 "    wire [7:0] selected_payload = (instruction_shift_burst ? shift_tx_slot : instruction[1]) ?")
        s = once(s, "(instruction[2:0] == 3'd0) &&\n                             (COMPACT_PHASE", "!instruction[2] &&\n                             (COMPACT_PHASE")
        start, end = s.index("                            OpHalt: begin"), s.index("                            OpWaitPin: begin")
        block = s[start:end]
        assert block.count("(selected_shift_tx_bit ? shift_tx_mask : 8'd0)") == 2
        block = block.replace("(selected_shift_tx_bit ? shift_tx_mask : 8'd0)", "serial_drive_value")
        mask = "serial_drive_oe"
        block = once(block, "(gpio_oe | phase_aux_mask | shift_tx_mask) & ~shift_rx_mask",
                     "((gpio_oe | phase_aux_mask) &\n                                                    ~shift_tx_mask & ~shift_rx_mask) | "+mask)
        block = once(block, "(gpio_oe | shift_tx_mask) & ~shift_rx_mask",
                     "(gpio_oe & ~shift_tx_mask & ~shift_rx_mask) |\n                                              "+mask)
        s = s[:start]+block+s[end:]
        s = once(s, "    task automatic abort_to", """    wire [7:0] serial_drive_value =
        (selected_shift_tx_bit && !serial_open_drain) ? shift_tx_mask : 8'd0;
    wire [7:0] serial_drive_oe =
        (!serial_open_drain || !selected_shift_tx_bit) ? shift_tx_mask : 8'd0;

    task automatic abort_to""")
    s = s.replace("gpio_value <= (gpio_value & ~phase_aux_mask & ~shift_tx_mask) |",
                  "gpio_value <=\n                                            (gpio_value & ~phase_aux_mask & ~shift_tx_mask) |")
    s = s.replace("                                                      (phase_aux_value", "                                            (phase_aux_value")
    s = s.replace("                                                      (selected_shift_tx_bit", "                                            (selected_shift_tx_bit")
    s = s.replace("                                                      serial_drive_value;", "                                            serial_drive_value;")
    s = s.replace("                                                    ~shift_tx_mask & ~shift_rx_mask) | serial_drive_oe;",
                  "                                                  ~shift_tx_mask & ~shift_rx_mask) |\n                                                  serial_drive_oe;")
    s = s.replace("gpio_oe <= (gpio_oe | phase_aux_mask | shift_tx_mask) & ~shift_rx_mask;",
                  "gpio_oe <= (gpio_oe | phase_aux_mask | shift_tx_mask) &\n                                                   ~shift_rx_mask;")
    return s


def store(words):
    bank_width = 4 if words == 128 else 5
    address_width = bank_width+5
    word_width = address_width-2
    registers = "\n".join(f"    reg [31:0] word{n};" for n in range(words))
    reset = "\n".join(f"            word{n} <= 32'd0;" for n in range(words))
    writes = "\n".join(f"                    {word_width}'d{n}: word{n}[8*byte_address[1:0] +: 8] <= data_in;" for n in range(words))
    reads = "\n".join(f"            {word_width}'d{n}: data_out = word{n}[8*byte_address[1:0] +: 8];" for n in range(words))
    fetch = "\n".join(f"            8'd{n}: instruction = word{n};" for n in range(words))
    length_valid = "(data_in != 8'd0)" if words == 255 else f"(data_in >= 8'd1) && (data_in <= 8'd{words})"
    return f"""/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module m1_program_store (
    input wire clk, input wire rst_n, input wire ena,
    input wire load_mode, input wire load_write, input wire load_length, input wire load_bank,
    input wire [4:0] byte_address, input wire [7:0] data_in,
    input wire [7:0] pc,
    output reg [7:0] data_out, output reg [7:0] program_length,
    output reg program_ready, output reg [{bank_width-1}:0] program_bank,
    output reg [31:0] instruction, output wire instruction_valid
);
{registers}
    wire [{address_width-1}:0] bank_address = {{program_bank, byte_address}};
    wire length_valid = {length_valid};
    always @(posedge clk) begin
        if (!rst_n) begin
{reset}
            program_bank <= {bank_width}'d0;
            program_length <= 8'd0;
            program_ready <= 1'b0;
        end else if (ena && load_mode && load_write) begin
            if (load_bank) begin
                program_bank <= (data_in < 8'd{1 << bank_width}) ? data_in[{bank_width-1}:0] : {bank_width}'d0;
                program_length <= 8'd0;
                program_ready <= 1'b0;
            end else if (load_length) begin
                program_bank <= {bank_width}'d0;
                program_length <= length_valid ? data_in : 8'd0;
                program_ready <= length_valid;
            end else begin
                program_ready <= 1'b0;
                case (bank_address[{address_width-1}:2])
{writes}
                    default: begin end
                endcase
            end
        end
    end
    // verilog_lint: waive always-comb
    always @(*) begin
        case (bank_address[{address_width-1}:2])
{reads}
            default: data_out = 8'd0;
        endcase
        if (load_length)
            data_out = program_length;
        case (pc)
{fetch}
            default: instruction = 32'd0;
        endcase
    end
    assign instruction_valid = program_ready && (pc < program_length) && (pc < 8'd{words});
endmodule
`default_nettype wire
"""


def top(source, words, isa):
    bank_width = 4 if words == 128 else 5
    s = once(source, "wire [4:0] pc;", "wire [7:0] pc;")
    s = s.replace("wire [4:0] loop_", "wire [7:0] loop_")
    s = once(s, "wire [3:0] program_length;", "wire [7:0] program_length;")
    s = once(s, "wire program_bank;", f"wire [{bank_width-1}:0] program_bank;")
    s = once(s, "(!load_register || (byte_address == 5'd0) || (byte_address == 5'd5));",
             "(!load_register || (byte_address == 5'd0) ||\n                                   (byte_address == 5'd5));")
    s = s.replace("{7'd0, program_bank}", f"{{{8-bank_width}'d0, program_bank}}")
    s = once(s, f"assign register_data_out = (byte_address == 5'd5) ? {{{8-bank_width}'d0, program_bank}} : register_data_out_raw;",
             f"assign register_data_out = (byte_address == 5'd5) ? {{{8-bank_width}'d0, program_bank}} :\n"
             f"                               (byte_address == 5'd6) ? pc :\n"
             f"                               (byte_address == 5'd7) ? 8'h{isa:02x} : register_data_out_raw;")
    s = s.replace("{state, program_ready, pc}", "{state, program_ready, pc[4:0]}")
    s = once(s, "                default: assert (uo_out == 8'b0);",
             f"                5'd6: assert (uo_out == pc);\n                5'd7: assert (uo_out == 8'h{isa:02x});\n"
             "                default: assert (uo_out == 8'b0);")
    return s


def build(output):
    if output.exists():
        raise ValueError("preserve earlier candidate builds; choose a new directory")
    legacy = build_legacy(output/"legacy")
    g1 = json.loads((ROOT/"evidence/E0031-8x4-physical-comparison/attempts/d34/compact10/result.json").read_text())
    assert legacy["compact10"]["source_sha256"] == g1["source_sha256"]
    base = {name: (output/"legacy/compact10/src"/name).read_text() for name in FILES}
    manifests = {}
    for variant, capacity, isa in (("literal255", 255, 0x20), ("od128", 128, 0x21)):
        files = dict(base)
        files["m1_engine.v"] = engine(base["m1_engine.v"], variant == "od128")
        files["m1_program_store.v"] = store(capacity)
        files["project.v"] = top(base["project.v"], capacity, isa)
        directory = output/variant/"src"
        directory.mkdir(parents=True)
        for name, text in files.items():
            (directory/name).write_bytes(text.encode())
        manifests[variant] = {"capacity": capacity, "program_bits": 32*capacity, "isa_id": isa,
                              "source_sha256": {n: hashlib.sha256(s.encode()).hexdigest() for n, s in files.items()}}
    (output/"source-manifest.json").write_text(json.dumps(manifests, indent=2)+"\n")
    return manifests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
