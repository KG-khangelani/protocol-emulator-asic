/*
 * SPDX-License-Identifier: Apache-2.0
 * M1 simulation candidate: preloaded SET/WAIT/HALT engine integration.
 */
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out,
    output wire [7:0] uio_oe, input wire ena, input wire clk, input wire rst_n
);
    wire [4:0] pc;
    wire [1:0] state;
    wire [15:0] wait_left;
    wire [7:0] gpio_value;
    wire [7:0] gpio_oe;
    reg [31:0] instruction;
    reg instruction_valid;

    // Provisional simulation-only preload. A public-pin loader is not present.
    // verilog_lint: waive always-comb
    always @(*) begin
        instruction = 32'hc0000000;
        instruction_valid = 1'b1;
        case (pc)
            5'd0: instruction = 32'h00ffffa5; // SET all: drive A5
            5'd1: instruction = 32'h40000002; // WAIT 2
            5'd2: instruction = 32'h000f0503; // SET low nibble: value 3, OE 5
            5'd3: instruction = 32'h80000000; // HALT
            default: begin instruction = 32'hc0000000; instruction_valid = 1'b0; end
        endcase
    end

    m1_engine engine (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .instruction(instruction), .instruction_valid(instruction_valid),
        .pc(pc), .state(state), .wait_left(wait_left),
        .gpio_value(gpio_value), .gpio_oe(gpio_oe)
    );

    assign uio_out = gpio_value;
    assign uio_oe = gpio_oe;
    assign uo_out = {state, 1'b0, pc};
    wire _unused = &{ui_in, uio_in, wait_left, 1'b0};
endmodule

`default_nettype wire
