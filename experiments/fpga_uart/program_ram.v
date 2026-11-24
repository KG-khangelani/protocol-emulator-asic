// SPDX-License-Identifier: Apache-2.0
`default_nettype none

// FPGA-only binding for the active ports of the ASIC's single-port SRAM.
// The production store ties BIST off and writes complete byte lanes.
module RM_IHPSG13_1P_256x32_c2_bm_bist (
    input wire A_CLK, A_MEN, A_WEN, A_REN, A_DLY,
    input wire [7:0] A_ADDR,
    input wire [31:0] A_DIN, A_BM,
    output wire [31:0] A_DOUT,
    input wire A_BIST_CLK, A_BIST_EN, A_BIST_MEN, A_BIST_WEN, A_BIST_REN,
    input wire [7:0] A_BIST_ADDR,
    input wire [31:0] A_BIST_DIN, A_BIST_BM
);
    genvar lane;
    generate for (lane = 0; lane < 4; lane = lane + 1) begin : bytes
        wire write_lane = A_WEN && A_BM[8*lane];
        wire [15:0] ram_data;
        reg forwarded;
        reg [7:0] write_data;
        // Separate blocks let unselected lanes read the old word while a
        // selected lane returns the written byte without a RAM port collision.
        SB_RAM40_4K #(.READ_MODE(0), .WRITE_MODE(0)) ram (
            .RCLK(A_CLK), .RCLKE(A_MEN && A_REN && !write_lane), .RE(1'b1),
            .RADDR({3'b000, A_ADDR}), .RDATA(ram_data),
            .WCLK(A_CLK), .WCLKE(A_MEN && write_lane), .WE(1'b1),
            .WADDR({3'b000, A_ADDR}), .MASK(16'hff00),
            .WDATA({8'h00, A_DIN[8*lane +: 8]})
        );
        always @(posedge A_CLK) begin
            if (A_MEN && A_REN) begin
                forwarded <= write_lane;
                if (write_lane)
                    write_data <= A_DIN[8*lane +: 8];
            end
        end
        assign A_DOUT[8*lane +: 8] = forwarded ? write_data : ram_data[7:0];
    end endgenerate
endmodule
`default_nettype wire
