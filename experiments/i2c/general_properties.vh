// SPDX-License-Identifier: Apache-2.0
// Assertions are appended to an otherwise byte-identical generated engine.
reg f_past_valid = 1'b0;
wire [127:0] f_state = {pc, state, wait_left, gpio_value, gpio_oe,
    wait_is_input, wait_pin, wait_level, wait_timeout_skip,
    wait_timeout_jump, wait_failure_pc, loop_active, loop_start, loop_end,
    loop_remaining, shift_active, shift_bits_done, shift_msb_first,
    shift_tx_pin, shift_rx_pin, shift_tx_data, shift_rx_data, shift_period,
    shift_tx_slot, phase_active, phase_prepared};
wire f_issued_wait = rst_n && ena && state == Run && instruction_valid &&
                     instruction[31:30] == 2'b11;
wire f_new_wait_valid = instruction[24] && !instruction[25];
wire f_immediate_branch = f_issued_wait && f_new_wait_valid &&
                         instruction[15:0] == 0 &&
                         sampled_inputs[instruction[29:27]] != instruction[26];
wire f_expired_branch = rst_n && ena && state == Waiting &&
                        shift_period == 0 && wait_is_input &&
                        wait_timeout_jump && wait_left == 1 &&
                        sampled_inputs[wait_pin] != wait_level;
wire f_branch = f_immediate_branch || f_expired_branch;
wire [7:0] f_destination = f_immediate_branch ? instruction[23:16] : wait_failure_pc;
wire f_final_match = rst_n && ena && state == Waiting && shift_period == 0 &&
                     wait_is_input && wait_left == 1 && sampled_inputs[wait_pin] == wait_level;
wire f_serial_shape = instruction[31:29] == 3'b101 && !instruction[21] &&
                       instruction[27:25] != instruction[24:22];
wire f_manual = f_serial_shape && instruction[20:2] == 0 && !phase_active &&
                 (!shift_active || (instruction[28] == shift_msb_first &&
                   instruction[27:25] == shift_tx_pin && instruction[24:22] == shift_rx_pin));
wire [7:0] f_tx_mask = 8'd1 << instruction[27:25];
wire [7:0] f_rx_mask = 8'd1 << instruction[24:22];
wire f_drive = f_serial_shape && instruction[20:19] == 1 && !instruction[2] &&
                (instruction[18:11] & (f_tx_mask | f_rx_mask)) == 0 &&
                (!shift_active ? (!phase_active && !phase_prepared) :
                 (phase_active && !phase_prepared && instruction[28] == shift_msb_first &&
                  instruction[27:25] == shift_tx_pin && instruction[24:22] == shift_rx_pin));
wire f_serial = rst_n && ena && state == Run && instruction_valid && (f_manual || f_drive);
wire [7:0] f_payload = instruction[1] ? tx_payload_alt : tx_payload;
wire f_tx_bit = shift_active ? (shift_msb_first ? shift_tx_data[7] : shift_tx_data[0]) :
                               (instruction[28] ? f_payload[7] : f_payload[0]);

always @(posedge clk) begin
    f_past_valid <= 1'b1;
    if (!f_past_valid) assume(!rst_n);
    if (f_past_valid) begin
        if (!$past(rst_n)) begin
            assert(pc == 0 && state == Run && wait_left == 0);
            assert(!wait_timeout_jump && wait_failure_pc == 0);
            assert(!loop_active && !shift_active && !phase_active && !phase_prepared);
            assert(gpio_value == 0 && gpio_oe == 0);
        end else if (!$past(ena)) begin
            assert(f_state == $past(f_state));
        end
        if ($past(f_branch)) begin
            assert(pc == $past(f_destination) && state == Run);
            assert(wait_left == 0 && !wait_is_input && !wait_timeout_skip);
            assert(!wait_timeout_jump && wait_failure_pc == 0);
            assert(!loop_active && loop_remaining == 0 && loop_start == 0 && loop_end == 0);
            assert(!shift_active && shift_bits_done == 0 && shift_period == 0);
            assert(!phase_active && !phase_prepared);
            assert({gpio_value, gpio_oe} == $past({gpio_value, gpio_oe}));
        end
        if ($past(f_final_match)) begin
            assert(state == Run && wait_left == 0 && !wait_is_input);
            if ($past(loop_active) && $past(pc) + 8'd1 == $past(loop_end)) begin
                assert(pc == ($past(loop_remaining) > 1 ? $past(loop_start) : $past(loop_end)));
            end else assert(pc == $past(pc) + 8'd1);
            assert({shift_active, shift_bits_done, phase_active, phase_prepared} ==
                   $past({shift_active, shift_bits_done, phase_active, phase_prepared}));
        end
        if ($past(f_issued_wait && instruction[24] && instruction[25]))
            assert(state == Faulted);
        if ($past(f_issued_wait && !instruction[24] && instruction[23:16] != 0))
            assert(state == Faulted);
        if ($past(f_issued_wait && f_new_wait_valid && instruction[15:0] != 0 &&
                   sampled_inputs[instruction[29:27]] != instruction[26])) begin
            assert(state == Waiting && wait_left == $past(instruction[15:0]));
            assert(wait_timeout_jump && wait_failure_pc == $past(instruction[23:16]));
        end
        if ($past(f_issued_wait && !instruction[24] && instruction[23:16] == 0 &&
                  instruction[25] && instruction[15:0] == 0 && pc >= 254 &&
                  sampled_inputs[instruction[29:27]] != instruction[26]))
            assert(state == Faulted && pc == $past(pc));
        if ($past(rst_n && ena && state == Waiting && shift_period == 0 &&
                  wait_is_input && wait_timeout_skip && !wait_timeout_jump &&
                  wait_left == 1 && pc >= 254 && sampled_inputs[wait_pin] != wait_level))
            assert(state == Faulted && pc == $past(pc));
`ifdef SERIAL_OPTIONS
        if ($past(f_serial)) begin
            assert((gpio_value & $past(f_tx_mask)) ==
                   (($past(instruction[0]) || !$past(f_tx_bit)) ? 0 : $past(f_tx_mask)));
            assert((gpio_oe & $past(f_tx_mask)) ==
                   (($past(instruction[0]) && $past(f_tx_bit)) ? 0 : $past(f_tx_mask)));
            assert((gpio_oe & $past(f_rx_mask)) == 0);
        end
`endif
    end
    if (f_past_valid) begin
        if (f_branch) assert(!shift_result_write);
        if (shift_result_write) begin
            assert(rst_n && ena && shift_active && shift_bits_done == 7);
            assert(shift_result_data == (shift_msb_first ?
                {shift_rx_data[6:0], sampled_inputs[shift_rx_pin]} :
                {sampled_inputs[shift_rx_pin], shift_rx_data[7:1]}));
        end
`ifdef SERIAL_OPTIONS
        if (f_serial)
            assert(shift_result_write == (f_manual && shift_active && shift_bits_done == 7));
`endif
        cover(f_immediate_branch && loop_active && shift_active && phase_prepared);
        cover(f_expired_branch && loop_active && shift_active && phase_prepared);
        cover(f_final_match && wait_timeout_jump && loop_active && shift_active);
        cover(f_expired_branch && wait_failure_pc > 127);
`ifdef SERIAL_OPTIONS
        cover(f_serial && instruction[0] && instruction[1] && !shift_active && f_tx_bit);
`endif
    end
end
