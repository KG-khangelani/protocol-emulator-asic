/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module timed_refinement(
    input wire clk,rst_n,ena,
    input wire [31:0] instruction,input wire instruction_valid,
    input wire [7:0] sampled_inputs,tx_payload,tx_payload_alt
);
    `include "refinement_bindings.vh"
    reg past_valid=0;
    wire allocated_set=instruction[31:30]==0 && instruction[29:24]!=0;
`ifdef VARIANT_F
    wire allocated_drive=0;
`else
    wire allocated_drive=instruction[31:29]==3'b101 && !instruction[21] && instruction[20:19]==1 && instruction[2:0]!=0;
`endif
    always @(posedge clk) begin
        past_valid<=1;
        if(!past_valid) assume(!rst_n);
        if(rst_n && ena && l_state==0 && instruction_valid) assume(!allocated_set && !allocated_drive);
        if(past_valid) begin
            assert(candidate_outputs==compact_outputs);
`ifdef VARIANT_F
            assert(!c_formal_gpio_pending && c_formal_gpio_pending_value==0 && c_formal_gpio_pending_oe==0);
`endif
        end
    end
endmodule
`default_nettype wire
