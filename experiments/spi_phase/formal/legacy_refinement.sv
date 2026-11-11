/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module legacy_refinement (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs, tx_payload, tx_payload_alt
);
    `include "legacy_bindings.vh"
    reg past_valid = 1'b0;
    wire allocated_phase_type = instruction[31:29] == 3'b101 && !instruction[21] &&
                                (instruction[20:19] == 2'd1 || instruction[20:19] == 2'd2);
    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!past_valid) assume(!rst_n);
        if (rst_n && ena && l_state == 2'd0 && instruction_valid)
            assume(!allocated_phase_type);
        if (past_valid) begin
            assert(!formal_phase_active && !formal_phase_prepared);
            assert(candidate_outputs == legacy_outputs);
        end
        cover(past_valid && c_shift_result_write && c_shift_burst_status);
        cover(past_valid && c_shift_result_write && !c_shift_burst_status);
        cover(past_valid && c_shift_tx_slot_status && !c_shift_active_status);
    end
endmodule
`default_nettype wire
