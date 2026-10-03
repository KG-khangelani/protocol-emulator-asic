/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out,
    output wire [7:0] uio_oe, input wire ena, input wire clk, input wire rst_n
);
    wire load_mode = ui_in[7];
    wire load_write = ui_in[6];
    wire load_length = ui_in[5];
    wire [4:0] byte_address = ui_in[4:0];
    wire [4:0] pc;
    wire [1:0] state;
    wire [15:0] wait_left;
    wire [7:0] gpio_value;
    wire [7:0] gpio_oe;
    wire [7:0] loader_data_out;
    wire [3:0] program_length;
    wire program_ready;
    wire [31:0] instruction;
    wire instruction_valid;
    wire [7:0] sampled_inputs;
    wire wait_is_input_status;
    wire [2:0] wait_pin_status;
    wire wait_level_status;
    wire engine_rst_n = rst_n && program_ready && !load_mode;

    m1_program_store store (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .load_mode(load_mode), .load_write(load_write), .load_length(load_length),
        .byte_address(byte_address), .data_in(uio_in), .pc(pc),
        .data_out(loader_data_out), .program_length(program_length),
        .program_ready(program_ready), .instruction(instruction),
        .instruction_valid(instruction_valid)
    );

    m1_input_sync input_sync (
        .clk(clk), .rst_n(rst_n), .async_in(uio_in), .sampled_in(sampled_inputs)
    );

    m1_engine engine (
        .clk(clk), .rst_n(engine_rst_n), .ena(ena),
        .instruction(instruction), .instruction_valid(instruction_valid),
        .sampled_inputs(sampled_inputs),
        .pc(pc), .state(state), .wait_left(wait_left),
        .gpio_value(gpio_value), .gpio_oe(gpio_oe),
        .wait_is_input_status(wait_is_input_status),
        .wait_pin_status(wait_pin_status), .wait_level_status(wait_level_status)
    );

    assign uio_out = load_mode ? loader_data_out : gpio_value;
    assign uio_oe = load_mode ? (load_write ? 8'h00 : 8'hff) : gpio_oe;
    assign uo_out = {state, program_ready, pc};
    wire _unused = &{wait_left, program_length, wait_is_input_status,
                     wait_pin_status, wait_level_status, 1'b0};
endmodule

`default_nettype wire
