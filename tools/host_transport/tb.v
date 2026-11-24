// SPDX-License-Identifier: Apache-2.0
`timescale 1ns / 1ps
`default_nettype none

// Instrumented digital fixture. Runtime protocol sources use uio_in.
module tb;
    reg clk = 0;
    reg rst_n = 0;
    reg ena = 1;
    reg [7:0] ui_in = 8'he7;
    reg [7:0] uio_in = 0;
    reg loading = 1;
    reg [7:0] host_mask = 0, host_data = 0;
    reg [7:0] peer_mask = 0;
    reg peer_connected = 0, peer_stuck = 0;
    wire [7:0] uo_out, uio_out, uio_oe;
    wire [7:0] peer_drive = (peer_connected || peer_stuck) ? peer_mask : 8'h00;
    wire [7:0] overlap = (host_mask & uio_oe) | (peer_drive & (host_mask | uio_oe));
    // The external idle environment becomes visible when its link closes.
    wire [7:0] external_pins = (peer_connected || peer_stuck) ? uio_in : 8'h00;
    wire [7:0] loader_pins = (host_data & host_mask) | (uio_out & uio_oe) |
                             (external_pins & ~host_mask & ~uio_oe);
    reg [31:0] rising_edges = 0;
    always @(posedge clk) begin
        rising_edges <= rising_edges + 1;
        if (ena !== 1'b1) $fatal(1, "project deselected at a rising edge");
    end

    tt_um_khangelani_protocol_emulator user_project (
        .ui_in(ui_in), .uo_out(uo_out), .uio_in(loading ? loader_pins : uio_in),
        .uio_out(uio_out), .uio_oe(uio_oe), .ena(1'b1), .clk(clk), .rst_n(rst_n)
    );
endmodule
`default_nettype wire
