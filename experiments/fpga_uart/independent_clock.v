// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module tt_fpga_top (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    inout  wire [7:0] uio,
    input  wire clk,     // Controller request: one loader strobe, or a sustained run.
    input  wire rst_n
);
    wire receiver_clock;
    SB_HFOSC #(.CLKHF_DIV(`RX_OSC_DIV)) oscillator (
        .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(receiver_clock)
    );
    reg request_meta;
    reg request_sync;
    reg request_previous;
    always @(posedge receiver_clock) begin
        if (!rst_n) begin
            request_meta <= 1'b0;
            request_sync <= 1'b0;
            request_previous <= 1'b0;
        end else begin
            request_meta <= clk;
            request_sync <= request_meta;
            request_previous <= request_sync;
        end
    end
    wire enabled = request_sync && (!ui_in[7] || !request_previous);
    wire [7:0] pin_input;
    wire [7:0] project_data;
    wire [7:0] project_oe;
    wire observe = rst_n && !ui_in[7];
    // The UART program uses UIO1 as RX and UIO0 as a dummy TX.
    // UIO2 returns to the ordinary eight-bit interface during all loader operations.
    wire [7:0] pin_data = {project_data[7:3], observe ? receiver_clock : project_data[2], project_data[1:0]};
    wire [7:0] pin_oe = project_oe | {5'b0, observe, 2'b0};
    SB_IO #(.PIN_TYPE(6'b1010_01)) pads[7:0] (
        .PACKAGE_PIN(uio), .OUTPUT_ENABLE(pin_oe), .D_OUT_0(pin_data), .D_IN_0(pin_input)
    );
    tt_um_khangelani_protocol_emulator receiver (
        .ui_in(ui_in), .uo_out(uo_out), .uio_in(pin_input),
        .uio_out(project_data), .uio_oe(project_oe), .ena(enabled),
        .clk(receiver_clock), .rst_n(rst_n)
    );
endmodule

`default_nettype wire
