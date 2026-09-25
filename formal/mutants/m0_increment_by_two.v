/*
 * SPDX-License-Identifier: Apache-2.0
 * INTENTIONALLY WRONG verification mutant: increments by two, not one.
 * This file is never part of the design source list.
 */
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    reg [7:0] count;

    always @(posedge clk) begin
        if (!rst_n)
            count <= 8'h00;
        else if (ena)
            count <= count + 8'h02;
    end

    assign uo_out = count;
    assign uio_out = 8'h00;
    assign uio_oe = 8'h00;
    wire _unused = &{ui_in, uio_in, 1'b0};
endmodule

`default_nettype wire
