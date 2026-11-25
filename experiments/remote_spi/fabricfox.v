// SPDX-License-Identifier: Apache-2.0
`default_nettype none
module tt_fpga_top (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    inout wire [7:0] uio, input wire clk, input wire rst_n
);
    wire run_mode, stage, miso;
    wire [2:0] requester;
    wire [7:0] data_out, oe, status;
    wire observe = run_mode && rst_n;
    wire drive_miso = observe && oe[3];
    SB_IO #(.PIN_TYPE(6'b000001)) run_pin (.PACKAGE_PIN(uio[7]), .D_IN_0(run_mode));
    SB_IO #(.PIN_TYPE(6'b000001)) peer_pin[2:0] (.PACKAGE_PIN(uio[2:0]), .D_IN_0(requester));
    SB_IO #(.PIN_TYPE(6'b101001)) miso_pin (.PACKAGE_PIN(uio[3]), .D_IN_0(miso),
        .OUTPUT_ENABLE(drive_miso), .D_OUT_0(data_out[3]));
    SB_IO #(.PIN_TYPE(6'b101001)) enable_copy (.PACKAGE_PIN(uio[4]),
        .OUTPUT_ENABLE(observe), .D_OUT_0(drive_miso));
    // The controller releases the staging pin before enabling runtime observation.
    SB_IO #(.PIN_TYPE(6'b101001)) stage_halt (.PACKAGE_PIN(uio[5]), .D_IN_0(stage),
        .OUTPUT_ENABLE(observe), .D_OUT_0(status[7:6] == 2'b10));
    SB_IO #(.PIN_TYPE(6'b101001)) clock_copy (.PACKAGE_PIN(uio[6]),
        .OUTPUT_ENABLE(observe), .D_OUT_0(clk));

    reg [7:0] staged_data;
    always @(posedge clk)
        if (!run_mode && stage)
            staged_data <= ui_in;
    // E7 resets only the executor. Two parked-loader clocks also flush the pin synchronizer.
    wire [7:0] selector = run_mode ? 8'h00 :
        (!stage && (ui_in[7] || ui_in == 8'h67)) ? ui_in : 8'he7;
    wire [7:0] data_in = run_mode || selector == 8'he7 ? {4'b0, miso, requester} : staged_data;
    assign uo_out = run_mode ? {status[7:5], oe[5:3], data_out[5:4]} :
        (selector[7] && !selector[6] ? data_out : status);
    tt_um_khangelani_protocol_emulator target (.clk(clk), .rst_n(rst_n), .ena(1'b1),
        .ui_in(selector), .uio_in(data_in), .uio_out(data_out), .uio_oe(oe), .uo_out(status));
endmodule
`default_nettype wire
