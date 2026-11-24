// SPDX-License-Identifier: Apache-2.0
`timescale 1ps/1ps
`default_nettype none
module tb;
    reg [7:0] ui_in = 8'he7, host_data = 0, host_mask = 0;
    reg clk = 0, rst_n = 0, peer_connected = 0, peer_level = 1;
    reg [31:0] minimum_period_ps = 0, observed_edges = 0;
    time previous_rise_ps = 0, shortest_period_ps = 64'hffffffffffffffff;
    wire [7:0] uo_out;
    tri [7:0] uio;
    always @(posedge clk) begin
        if (observed_edges != 0) begin
            if ($time - previous_rise_ps < minimum_period_ps)
                $fatal(1, "FPGA_CLOCK_TOO_FAST interval_ps=%0d minimum_ps=%0d",
                       $time - previous_rise_ps, minimum_period_ps);
            if ($time - previous_rise_ps < shortest_period_ps)
                shortest_period_ps <= $time - previous_rise_ps;
        end
        previous_rise_ps <= $time;
        observed_edges <= observed_edges + 1;
    end
    genvar bit_index;
    generate for (bit_index = 0; bit_index < 8; bit_index = bit_index+1) begin : host
        assign uio[bit_index] = host_mask[bit_index] ? host_data[bit_index] : 1'bz;
    end endgenerate
    assign uio[1] = peer_connected ? peer_level : 1'bz;
    tt_fpga_top package_model (.ui_in(ui_in), .uo_out(uo_out), .uio(uio), .clk(clk), .rst_n(rst_n));
endmodule
`default_nettype wire
