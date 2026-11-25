// SPDX-License-Identifier: Apache-2.0
`default_nettype none
module tt_fpga_top (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    inout wire [7:0] uio, input wire clk, input wire rst_n
);
    wire run_mode, stage, sda, scl, rx_page, valid_page;
    wire [7:0] data_out, oe, status;
    wire observe = run_mode && rst_n;
    wire drive_sda = observe && oe[1];
    wire drive_scl = observe && oe[0];
    SB_IO #(.PIN_TYPE(6'b000001)) run_pin (.PACKAGE_PIN(uio[7]), .D_IN_0(run_mode));
    SB_IO #(.PIN_TYPE(6'b000001)) rx_pin (.PACKAGE_PIN(uio[0]), .D_IN_0(rx_page));
    SB_IO #(.PIN_TYPE(6'b000001)) valid_pin (.PACKAGE_PIN(uio[3]), .D_IN_0(valid_page));
    SB_IO #(.PIN_TYPE(6'b101001)) sda_pin (.PACKAGE_PIN(uio[1]), .D_IN_0(sda),
        .OUTPUT_ENABLE(drive_sda), .D_OUT_0(1'b0));
    SB_IO #(.PIN_TYPE(6'b101001)) scl_pin (.PACKAGE_PIN(uio[2]), .D_IN_0(scl),
        .OUTPUT_ENABLE(drive_scl), .D_OUT_0(1'b0));
    SB_IO #(.PIN_TYPE(6'b101001)) sda_enable (.PACKAGE_PIN(uio[4]),
        .OUTPUT_ENABLE(observe), .D_OUT_0(drive_sda));
    SB_IO #(.PIN_TYPE(6'b101001)) stage_halt (.PACKAGE_PIN(uio[5]), .D_IN_0(stage),
        .OUTPUT_ENABLE(observe), .D_OUT_0(status[7:6] == 2'b10));
    SB_IO #(.PIN_TYPE(6'b101001)) clock_copy (.PACKAGE_PIN(uio[6]),
        .OUTPUT_ENABLE(observe), .D_OUT_0(clk));

    reg [7:0] staged_data;
    always @(posedge clk)
        if (!run_mode && stage)
            staged_data <= ui_in;
    wire [7:0] run_selector = valid_page ? 8'h63 : rx_page ? 8'h62 : 8'h00;
    wire [7:0] selector = run_mode ? run_selector :
        (!stage && (ui_in[7] || ui_in == 8'h67)) ? ui_in : 8'he7;
    wire [7:0] data_in = run_mode || selector == 8'he7 ? {6'b0, sda, scl} : staged_data;
    wire [7:0] result = {status[7:6], data_out[4:2], oe[1:0], 1'b0};
    assign uo_out = run_mode ? (rx_page || valid_page ? status : result) :
        (selector[7] && !selector[6] ? data_out : status);
    tt_um_khangelani_protocol_emulator controller (.clk(clk), .rst_n(rst_n), .ena(1'b1),
        .ui_in(selector), .uio_in(data_in), .uio_out(data_out), .uio_oe(oe), .uo_out(status));
endmodule
`default_nettype wire
