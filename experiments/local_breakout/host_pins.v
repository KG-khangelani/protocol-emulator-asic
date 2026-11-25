// SPDX-License-Identifier: Apache-2.0
// The host uses the stock Pico GPIO numbers. header_instance.vh comes from the SG48 decode.
`default_nettype none
module tt_fpga_top(input wire [7:0] ui_in, output wire [7:0] uo_out,
                   inout wire [7:0] uio, input wire clk, input wire rst_n);
    tri [28:0] gp;
    assign gp[7:0] = ui_in;
    assign uo_out = gp[15:8];
    assign gp[27] = clk;
    assign gp[28] = rst_n;
    tran link[7:0](uio, {gp[16], gp[26], gp[22:17]});
    `include "header_instance.vh"
endmodule
`default_nettype wire
