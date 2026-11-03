/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module phase_observer(
input wire clk,
input wire rst_n,
input wire ena,
input wire [31:0] instruction,
input wire instruction_valid,
input wire [7:0] sampled_inputs,
input wire [7:0] tx_payload,
input wire [7:0] tx_payload_alt,
input wire [4:0] pc,
input wire [1:0] state,
input wire [15:0] wait_left,
input wire [7:0] gpio_value,
input wire [7:0] gpio_oe,
input wire wait_is_input_status,
input wire [2:0] wait_pin_status,
input wire wait_level_status,
input wire wait_timeout_skip_status,
input wire wait_is_shift_status,
input wire loop_active_status,
input wire [7:0] loop_remaining_status,
input wire [4:0] loop_start_status,
input wire [4:0] loop_end_status,
input wire shift_active_status,
input wire [2:0] shift_bits_done_status,
input wire shift_msb_first_status,
input wire [2:0] shift_tx_pin_status,
input wire [2:0] shift_rx_pin_status,
input wire [7:0] shift_tx_data_status,
input wire [7:0] shift_rx_data_status,
input wire shift_burst_status,
input wire [15:0] shift_period_status,
input wire shift_tx_slot_status,
input wire shift_result_write,
input wire [7:0] shift_result_data,
input wire formal_phase_active,
input wire formal_phase_prepared
);
wire [109:0] all_state = {pc,state,wait_left,gpio_value,gpio_oe,wait_is_input_status,wait_pin_status,wait_level_status,wait_timeout_skip_status,loop_active_status,loop_remaining_status,loop_start_status,loop_end_status,shift_active_status,shift_bits_done_status,shift_msb_first_status,shift_tx_pin_status,shift_rx_pin_status,shift_tx_data_status,shift_rx_data_status,shift_period_status,shift_tx_slot_status,formal_phase_active,formal_phase_prepared};
wire [86:0] phase_latched_state = {gpio_value,gpio_oe,wait_is_input_status,wait_pin_status,wait_level_status,wait_timeout_skip_status,loop_active_status,loop_remaining_status,loop_start_status,loop_end_status,shift_active_status,shift_bits_done_status,shift_msb_first_status,shift_tx_pin_status,shift_rx_pin_status,shift_tx_data_status,shift_rx_data_status,shift_period_status,shift_tx_slot_status,formal_phase_active,formal_phase_prepared};

    reg past_valid = 1'b0;
    wire run = state == 2'd0;
    wire waiting = state == 2'd1;
    wire op_shift = instruction[31:29] == 3'b101;
    wire drive_word = op_shift && !instruction[21] && instruction[20:19] == 2'd1;
    wire sample_word = op_shift && !instruction[21] && instruction[20:19] == 2'd2;
    wire matching = instruction[28] == shift_msb_first_status &&
                    instruction[27:25] == shift_tx_pin_status &&
                    instruction[24:22] == shift_rx_pin_status && !instruction[21];
    wire [7:0] tx_mask = 8'd1 << instruction[27:25];
    wire [7:0] rx_mask = 8'd1 << instruction[24:22];
    wire [7:0] aux_mask = instruction[18:11];
    wire [7:0] aux_value = instruction[10:3];
    wire shape_valid = instruction[27:25] != instruction[24:22] && instruction[2:0] == 3'd0;
    wire drive_valid = drive_word && shape_valid && !(|(aux_mask & (tx_mask | rx_mask))) &&
                       ((!shift_active_status && !formal_phase_active && !formal_phase_prepared) ||
                        (shift_active_status && formal_phase_active && !formal_phase_prepared && matching));
    wire sample_valid = sample_word && shape_valid && matching && formal_phase_active &&
                        formal_phase_prepared && shift_active_status;
    wire [15:0] delay_count = instruction[18:3];
    wire drive = rst_n && ena && run && instruction_valid && drive_valid;
    wire issue_sample = rst_n && ena && run && instruction_valid && sample_valid;
    wire pending = waiting && shift_period_status == 16'd1;
    wire capture = (issue_sample && delay_count == 16'd0) ||
                   (rst_n && ena && pending && wait_left == 16'd1 &&
                    formal_phase_active && formal_phase_prepared && shift_active_status);
    wire legacy_shape = op_shift && instruction[27:25] != instruction[24:22] &&
                        ((!instruction[21] && instruction[20:0] == 21'd0) ||
                         (instruction[21] && instruction[20:5] >= 16'd2 && instruction[4:0] == 5'd0));
    wire legacy_finish = rst_n && ena && !formal_phase_active && shift_active_status &&
                         shift_bits_done_status == 3'd7 &&
                         ((run && instruction_valid && legacy_shape && matching) ||
                          (waiting && shift_period_status >= 16'd2 && wait_left == 16'd1));
    wire expected_write = legacy_finish || (capture && shift_bits_done_status == 3'd7);
    wire [7:0] rx_next = shift_msb_first_status ?
                        {shift_rx_data_status[6:0], sampled_inputs[shift_rx_pin_status]} :
                        {sampled_inputs[shift_rx_pin_status], shift_rx_data_status[7:1]};
    wire [7:0] tx_source = shift_active_status ? shift_tx_data_status : tx_payload;
    wire tx_order = shift_active_status ? shift_msb_first_status : instruction[28];
    wire tx_bit = tx_order ? tx_source[7] : tx_source[0];
    wire [7:0] tx_next = tx_order ? {tx_source[6:0],1'b0} : {1'b0,tx_source[7:1]};
    wire halt_family_valid = (instruction == 32'h80000000 && !loop_active_status && !shift_active_status) ||
                             drive_valid || sample_valid ||
                             (legacy_shape && !formal_phase_active && (!shift_active_status || matching));
    wire rejected = rst_n && ena && run && instruction_valid &&
                    instruction[31:30] == 2'd2 && !halt_family_valid;

    task assert_advance;
        begin
            if ($past(loop_active_status) && ($past(pc) + 5'd1 == $past(loop_end_status))) begin
                if ($past(loop_remaining_status) > 8'd1) begin
                    assert(pc == $past(loop_start_status));
                    assert(loop_active_status && loop_remaining_status == $past(loop_remaining_status) - 8'd1);
                end else begin
                    assert(pc == $past(loop_end_status));
                    assert(!loop_active_status && loop_remaining_status == 8'd0);
                end
            end else assert(pc == $past(pc) + 5'd1);
        end
    endtask

    always @(*) if (past_valid) begin
        assert(!formal_phase_prepared || formal_phase_active);
        assert(!formal_phase_active || shift_active_status);
        assert(!formal_phase_active || shift_period_status <= 16'd1);
        assert(shift_period_status == 16'd0 || waiting);
        if (pending) begin
            assert(formal_phase_active && formal_phase_prepared && shift_active_status);
            assert(wait_left > 16'd0);
        end
        assert(shift_result_write == expected_write);
        if (capture) begin
            assert(shift_result_data == rx_next);
            assert(!shift_burst_status);
        end
    end

    reg saw_frozen_pending = 1'b0;
    reg saw_max_pending = 1'b0;
    reg saw_phase_byte = 1'b0;
    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!rst_n) begin
            saw_frozen_pending <= 1'b0;
            saw_max_pending <= 1'b0;
            saw_phase_byte <= 1'b0;
        end else begin
            if (pending && !ena) saw_frozen_pending <= 1'b1;
            if (pending && wait_left == 16'hffff) saw_max_pending <= 1'b1;
            if (capture && shift_bits_done_status == 3'd7) saw_phase_byte <= 1'b1;
        end
        if (past_valid) begin
            if (!$past(rst_n)) begin
                assert(all_state == 110'd0);
                assert(!formal_phase_active && !formal_phase_prepared && !shift_active_status);
                assert(pc == 5'd0 && state == 2'd0 && wait_left == 16'd0);
                assert(gpio_value == 8'd0 && gpio_oe == 8'd0);
                assert(shift_bits_done_status == 3'd0 && shift_period_status == 16'd0);
                assert(shift_tx_data_status == 8'd0 && shift_rx_data_status == 8'd0);
                assert(!shift_tx_slot_status);
            end else if (!$past(ena) || $past(state[1])) begin
                assert(all_state == $past(all_state));
            end else begin
                if ($past(drive)) begin
                    assert(state == 2'd0 && wait_left == 16'd0 && shift_period_status == 16'd0);
                    assert(formal_phase_active && formal_phase_prepared && shift_active_status);
                    assert(gpio_value == (($past(gpio_value) & ~$past(aux_mask) & ~$past(tx_mask)) |
                           ($past(aux_value) & $past(aux_mask)) | ($past(tx_bit) ? $past(tx_mask) : 8'd0)));
                    assert(gpio_oe == (($past(gpio_oe) | $past(aux_mask) | $past(tx_mask)) & ~$past(rx_mask)));
                    assert(shift_tx_data_status == $past(tx_next));
                    assert(shift_tx_slot_status == $past(shift_tx_slot_status));
                    if (!$past(shift_active_status)) begin
                        assert(shift_bits_done_status == 3'd0 && shift_rx_data_status == 8'd0);
                        assert(shift_tx_pin_status == $past(instruction[27:25]));
                        assert(shift_rx_pin_status == $past(instruction[24:22]));
                        assert(shift_msb_first_status == $past(instruction[28]));
                    end else begin
                        assert(shift_bits_done_status == $past(shift_bits_done_status));
                        assert(shift_rx_data_status == $past(shift_rx_data_status));
                    end
                    assert_advance();
                end
                if ($past(issue_sample) && $past(delay_count) != 16'd0) begin
                    assert(state == 2'd1 && wait_left == $past(delay_count) && shift_period_status == 16'd1);
                    assert(pc == $past(pc) && formal_phase_active && formal_phase_prepared);
                    assert(gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    assert(shift_tx_data_status == $past(shift_tx_data_status));
                    assert(shift_rx_data_status == $past(shift_rx_data_status));
                end
                if ($past(pending) && $past(wait_left) > 16'd1) begin
                    assert(state == 2'd1 && pc == $past(pc));
                    assert(wait_left == $past(wait_left) - 16'd1);
                    assert(phase_latched_state == $past(phase_latched_state));
                end
                if ($past(capture)) begin
                    assert(state == 2'd0 && wait_left == 16'd0 && shift_period_status == 16'd0);
                    assert(!formal_phase_prepared);
                    assert(shift_rx_data_status == $past(rx_next));
                    assert(gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    assert(shift_tx_data_status == $past(shift_tx_data_status));
                    assert(shift_tx_slot_status == $past(shift_tx_slot_status));
                    if ($past(shift_bits_done_status) == 3'd7) begin
                        assert(!formal_phase_active && !shift_active_status && shift_bits_done_status == 3'd0);
                    end else begin
                        assert(formal_phase_active && shift_active_status);
                        assert(shift_bits_done_status == $past(shift_bits_done_status) + 3'd1);
                    end
                    assert_advance();
                end
                if ($past(rejected)) begin
                    assert(state == 2'd3 && pc == $past(pc) && wait_left == 16'd0);
                    assert(gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    assert(shift_rx_data_status == $past(shift_rx_data_status));
                    assert(shift_tx_data_status == $past(shift_tx_data_status));
                    assert(shift_bits_done_status == $past(shift_bits_done_status));
                    assert(formal_phase_active == $past(formal_phase_active));
                    assert(formal_phase_prepared == $past(formal_phase_prepared));
                end
                if ($past(formal_phase_active) && !$past(capture)) begin
                    assert(shift_bits_done_status == $past(shift_bits_done_status));
                    assert(shift_rx_data_status == $past(shift_rx_data_status));
                end
                if ($past(formal_phase_active)) begin
                    assert(shift_tx_slot_status == $past(shift_tx_slot_status));
                    assert(shift_msb_first_status == $past(shift_msb_first_status));
                    assert(shift_tx_pin_status == $past(shift_tx_pin_status));
                    assert(shift_rx_pin_status == $past(shift_rx_pin_status));
                    if (!$past(drive)) assert(shift_tx_data_status == $past(shift_tx_data_status));
                end
            end
        end
    end
endmodule
`default_nettype wire
