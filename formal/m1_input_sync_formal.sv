/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_input_sync_formal (
    input wire clk, input wire rst_n, input wire [7:0] async_inputs
);
    wire [7:0] sampled_inputs;
    reg past_valid = 1'b0;
    reg past2_valid = 1'b0;

    m1_input_sync dut (
        .clk(clk), .rst_n(rst_n), .async_in(async_inputs),
        .sampled_in(sampled_inputs)
    );

    always @(posedge clk) begin
        past_valid <= 1'b1;
        past2_valid <= past_valid;
        if (past_valid && !$past(rst_n))
            assert (sampled_inputs == 8'd0);
        if (past2_valid && $past(rst_n) && $past($past(rst_n)))
            assert (sampled_inputs == $past($past(async_inputs)));
        cover (past2_valid && sampled_inputs != 8'd0);
    end
endmodule

`default_nettype wire
