/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module m1_input_sync (
    input wire clk, input wire rst_n, input wire [7:0] async_in,
    output reg [7:0] sampled_in
);
    reg [7:0] metastability_stage;
    always @(posedge clk) begin
        if (!rst_n) begin
            metastability_stage <= 8'd0;
            sampled_in <= 8'd0;
        end else begin
            metastability_stage <= async_in;
            sampled_in <= metastability_stage;
        end
    end
endmodule
`default_nettype wire
