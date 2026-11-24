`timescale 1ns/1ps
`default_nettype none

module resident_tb;
    reg clk, rst_n, host_drives, peer_connected;
    reg [7:0] ui_in, host_data;
    reg [1:0] peer_pulls;
    wire ena = 1'b1;
    wire [7:0] pads, uio_out, uio_oe, uo_out;
    assign (weak0, weak1) pads = 8'h03;
    assign pads = host_drives ? host_data : 8'bz;
    genvar pin;
    for (pin=0; pin<8; pin=pin+1) begin : chip_driver
        assign pads[pin] = uio_oe[pin] ? uio_out[pin] : 1'bz;
    end
    for (pin=0; pin<2; pin=pin+1) begin : target_driver
        assign pads[pin] = (peer_connected && peer_pulls[pin]) ? 1'b0 : 1'bz;
    end
    tt_um_khangelani_protocol_emulator chip (
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui_in), .uo_out(uo_out),
        .uio_in(pads), .uio_out(uio_out), .uio_oe(uio_oe)
    );
endmodule

`default_nettype wire
