/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module transport(input wire clk);
    (* anyconst *) reg [7:0] rx_byte;
    (* anyconst *) reg msb_first;
    (* anyseq *) reg raw_miso;
    reg [8:0] cycle = 9'd0;
    reg past_valid = 1'b0, past2_valid = 1'b0;
    reg [7:0] observed = 8'd0;
    wire rst_n = cycle != 9'd0;
    wire [7:0] raw = {6'd0,raw_miso,1'b0};
    wire [7:0] sampled;
    m1_input_sync actual_sync(.clk(clk),.rst_n(rst_n),.async_in(raw),.sampled_in(sampled));
    integer j;
    always @(posedge clk) begin
        past_valid <= 1'b1; past2_valid <= past_valid;
        if (cycle < 9'd403) cycle <= cycle + 9'd1;
        if (!rst_n) observed <= 8'd0;
        if (past_valid && !$past(rst_n)) assert(sampled == 8'd0);
        if (past2_valid && $past(rst_n) && $past($past(rst_n)))
            assert(sampled == $past($past(raw)));
        for (j=0;j<8;j=j+1) begin
            if (cycle == 27+50*j)
                assume(raw_miso == (msb_first ? rx_byte[7-j] : rx_byte[j]));
`ifdef EARLY_CAPTURE
            if (cycle == 28+50*j) begin
`else
            if (cycle == 29+50*j) begin
`endif
                assert(sampled[1] == (msb_first ? rx_byte[7-j] : rx_byte[j]));
                if (msb_first) observed[7-j] <= sampled[1];
                else observed[j] <= sampled[1];
            end
        end
        if (cycle >= 9'd380) assert(observed == rx_byte);
        cover(cycle == 9'd380 && observed == 8'h69 && msb_first);
        cover(cycle == 9'd380 && observed == 8'h69 && !msb_first);
        cover(cycle == 9'd28 && raw_miso != (msb_first ? rx_byte[7] : rx_byte[0]));
    end
endmodule
`default_nettype wire
