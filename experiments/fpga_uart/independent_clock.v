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
    wire stage_byte;
    wire uart_rx;
    // These pads stay input-only, including while the controller changes loader selectors.
    SB_IO #(.PIN_TYPE(6'b0000_01)) uart_input (.PACKAGE_PIN(uio[1]), .D_IN_0(uart_rx));
    SB_IO #(.PIN_TYPE(6'b0000_01)) stage_input (.PACKAGE_PIN(uio[7]), .D_IN_0(stage_byte));
    assign {uio[6:5], uio[3:2], uio[0]} = 5'bzzzzz;
    reg [7:0] staged_data;
    always @(posedge receiver_clock) begin
        if (stage_byte)
            staged_data <= ui_in;
    end
    // The physical UI1 driver is released throughout reception. UI4 carries its
    // logical selector bit so that the HAT's UI1/UIO1 link can carry the UART.
    wire [7:0] runtime_selector = {ui_in[7:5], 1'b0, ui_in[3:2], ui_in[4], ui_in[0]};
    wire [7:0] selector = stage_byte ? 8'he7 : (ui_in[7] ? ui_in : runtime_selector);
    wire enabled = request_sync && (!selector[7] || !request_previous);
    wire [7:0] pin_input = selector[7] ? staged_data : {6'b0, uart_rx, 1'b0};
    wire [7:0] project_data;
    wire [7:0] project_oe;
    wire [7:0] project_status;
    assign uo_out = selector[7] && !selector[6] ? project_data : project_status;
    wire observe = rst_n && !selector[7];
    SB_IO #(.PIN_TYPE(6'b1010_01)) monitor (
        .PACKAGE_PIN(uio[4]), .OUTPUT_ENABLE(observe), .D_OUT_0(receiver_clock)
    );
    tt_um_khangelani_protocol_emulator receiver (
        .ui_in(selector), .uo_out(project_status), .uio_in(pin_input),
        .uio_out(project_data), .uio_oe(project_oe), .ena(enabled),
        .clk(receiver_clock), .rst_n(rst_n)
    );
endmodule

`default_nettype wire
