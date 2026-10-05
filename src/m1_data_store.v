/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_data_store (
    input wire clk, input wire rst_n, input wire ena,
    input wire register_select, input wire register_write,
    input wire [4:0] register_address, input wire [7:0] data_in,
    input wire shift_result_write, input wire [7:0] shift_result_data,
    output reg [7:0] data_out, output reg [7:0] tx_payload,
    output reg [7:0] rx_result, output reg rx_valid
);
    always @(posedge clk) begin
        if (!rst_n) begin
            tx_payload <= 8'd0;
            rx_result <= 8'd0;
            rx_valid <= 1'b0;
        end else begin
            if (shift_result_write) begin
                rx_result <= shift_result_data;
                rx_valid <= 1'b1;
            end
            if (ena && register_select && register_write &&
                (register_address == 5'd1)) begin
                tx_payload <= data_in;
                rx_valid <= 1'b0;
            end
        end
    end

    // verilog_lint: waive always-comb
    always @(*) begin
        case (register_address)
            5'd1: data_out = tx_payload;
            5'd2: data_out = rx_result;
            5'd3: data_out = {7'd0, rx_valid};
            default: data_out = 8'd0;
        endcase
    end
endmodule

`default_nettype wire
