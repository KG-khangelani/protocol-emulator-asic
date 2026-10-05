/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_engine_formal (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs, input wire [7:0] tx_payload
);
    wire [4:0] pc;
    wire [1:0] state;
    wire [15:0] wait_left;
    wire [7:0] gpio_value;
    wire [7:0] gpio_oe;
    wire wait_is_input_status;
    wire [2:0] wait_pin_status;
    wire wait_level_status;
    wire wait_timeout_skip_status;
    wire loop_active_status;
    wire [7:0] loop_remaining_status;
    wire [4:0] loop_start_status;
    wire [4:0] loop_end_status;
    wire shift_active_status;
    wire [2:0] shift_bits_done_status;
    wire shift_msb_first_status;
    wire [2:0] shift_tx_pin_status;
    wire [2:0] shift_rx_pin_status;
    wire [7:0] shift_tx_data_status;
    wire [7:0] shift_rx_data_status;
    wire shift_result_write;
    wire [7:0] shift_result_data;
    wire instruction_input = sampled_inputs[instruction[29:27]];
    wire [5:0] instruction_loop_target_wide = {1'b0, pc} + 6'd1 +
                                              {1'b0, instruction[28:24]};
    wire instruction_shift_valid = instruction[29] &&
                                   (instruction[21:0] == 22'd0) &&
                                   (instruction[27:25] != instruction[24:22]);
    wire shift_config_matches = (instruction[28] == shift_msb_first_status) &&
                                (instruction[27:25] == shift_tx_pin_status) &&
                                (instruction[24:22] == shift_rx_pin_status);
    wire selected_shift_order = shift_active_status ?
                                shift_msb_first_status : instruction[28];
    wire [2:0] selected_shift_tx_pin = shift_active_status ?
                                         shift_tx_pin_status : instruction[27:25];
    wire [2:0] selected_shift_rx_pin = shift_active_status ?
                                         shift_rx_pin_status : instruction[24:22];
    wire [7:0] selected_shift_tx_data = shift_active_status ?
                                        shift_tx_data_status : tx_payload;
    wire selected_shift_tx_bit = selected_shift_order ?
                                 selected_shift_tx_data[7] : selected_shift_tx_data[0];
    wire selected_shift_rx_bit = sampled_inputs[selected_shift_rx_pin];
    wire [7:0] selected_shift_tx_mask = 8'b00000001 << selected_shift_tx_pin;
    wire [7:0] selected_shift_rx_mask = 8'b00000001 << selected_shift_rx_pin;
    wire [7:0] selected_shift_rx_base = shift_active_status ?
                                        shift_rx_data_status : 8'd0;
    wire [7:0] selected_shift_tx_next = selected_shift_order ?
                                        {selected_shift_tx_data[6:0], 1'b0} :
                                        {1'b0, selected_shift_tx_data[7:1]};
    wire [7:0] selected_shift_rx_next = selected_shift_order ?
                                        {selected_shift_rx_base[6:0], selected_shift_rx_bit} :
                                        {selected_shift_rx_bit, selected_shift_rx_base[7:1]};
    wire shift_completion = rst_n && ena && (state == 2'b00) && instruction_valid &&
                            (instruction[31:30] == 2'b10) &&
                            instruction_shift_valid && shift_active_status &&
                            shift_config_matches && (shift_bits_done_status == 3'd7);
    reg past_valid = 1'b0;
    reg reset_seen = 1'b0;
    wire latched_input = sampled_inputs[wait_pin_status];

    m1_engine dut (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .instruction(instruction), .instruction_valid(instruction_valid),
        .sampled_inputs(sampled_inputs), .tx_payload(tx_payload),
        .pc(pc), .state(state), .wait_left(wait_left),
        .gpio_value(gpio_value), .gpio_oe(gpio_oe),
        .wait_is_input_status(wait_is_input_status),
        .wait_pin_status(wait_pin_status), .wait_level_status(wait_level_status),
        .wait_timeout_skip_status(wait_timeout_skip_status),
        .loop_active_status(loop_active_status),
        .loop_remaining_status(loop_remaining_status),
        .loop_start_status(loop_start_status), .loop_end_status(loop_end_status),
        .shift_active_status(shift_active_status),
        .shift_bits_done_status(shift_bits_done_status),
        .shift_msb_first_status(shift_msb_first_status),
        .shift_tx_pin_status(shift_tx_pin_status),
        .shift_rx_pin_status(shift_rx_pin_status),
        .shift_tx_data_status(shift_tx_data_status),
        .shift_rx_data_status(shift_rx_data_status),
        .shift_result_write(shift_result_write),
        .shift_result_data(shift_result_data)
    );

    always @(*) begin
        assert (shift_result_write == shift_completion);
        assert (shift_result_data == (rst_n ? selected_shift_rx_next : 8'd0));
    end

    task assert_advance;
        begin
            if ($past(loop_active_status) &&
                (($past(pc) + 5'd1) == $past(loop_end_status))) begin
                if ($past(loop_remaining_status) > 8'd1) begin
                    assert (pc == $past(loop_start_status));
                    assert (loop_active_status);
                    assert (loop_remaining_status == $past(loop_remaining_status) - 8'd1);
                end else begin
                    assert (pc == $past(loop_end_status));
                    assert (!loop_active_status && loop_remaining_status == 8'd0);
                end
            end else begin
                assert (pc == $past(pc) + 5'd1);
            end
        end
    endtask

    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!rst_n)
            reset_seen <= 1'b1;
        if (past_valid) begin
            if (!$past(rst_n)) begin
                assert (pc == 5'd0 && state == 2'b00 && wait_left == 16'd0);
                assert (gpio_value == 8'd0 && gpio_oe == 8'd0);
                assert (!loop_active_status && loop_remaining_status == 8'd0);
                assert (!shift_active_status && shift_bits_done_status == 3'd0);
                assert (!shift_result_write);
            end else if ($past(reset_seen)) begin
                if (!$past(ena) || $past(state) == 2'b10 || $past(state) == 2'b11) begin
                    assert (pc == $past(pc) && state == $past(state));
                    assert (wait_left == $past(wait_left));
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    assert (loop_active_status == $past(loop_active_status));
                    assert (loop_remaining_status == $past(loop_remaining_status));
                    assert (shift_active_status == $past(shift_active_status));
                    assert (shift_bits_done_status == $past(shift_bits_done_status));
                    assert (shift_tx_data_status == $past(shift_tx_data_status));
                    assert (shift_rx_data_status == $past(shift_rx_data_status));
                end else if ($past(state) == 2'b01) begin
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    if ($past(wait_is_input_status) &&
                        ($past(latched_input) == $past(wait_level_status))) begin
                        assert (wait_left == 16'd0);
                        assert_advance();
                        assert (state == 2'b00);
                    end else if ($past(wait_is_input_status) && $past(wait_left) == 16'd1) begin
                        assert (wait_left == 16'd0);
                        if ($past(wait_timeout_skip_status) && !$past(loop_active_status)) begin
                            assert (pc == $past(pc) + 5'd2 && state == 2'b00);
                        end else begin
                            assert (pc == $past(pc) && state == 2'b11);
                        end
                    end else if ($past(wait_left) > 16'd1) begin
`ifdef M1_MUTANT
                        assert (wait_left == $past(wait_left) - 16'd2);
`else
                        assert (wait_left == $past(wait_left) - 16'd1);
`endif
                        assert (pc == $past(pc) && state == 2'b01);
                    end else begin
                        assert (wait_left == 16'd0);
                        assert_advance();
                        assert (state == 2'b00);
                    end
                end else if (!$past(instruction_valid)) begin
                    assert (state == 2'b11 && pc == $past(pc));
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                end else if ($past(instruction[31:30]) == 2'b00 &&
                             $past(instruction[29:24]) == 6'd0) begin
                    assert (state == 2'b00);
                    assert_advance();
                    assert (gpio_value == (($past(gpio_value) & ~$past(instruction[23:16])) |
                                           ($past(instruction[7:0]) & $past(instruction[23:16]))));
                    assert (gpio_oe == (($past(gpio_oe) & ~$past(instruction[23:16])) |
                                        ($past(instruction[15:8]) & $past(instruction[23:16]))));
                end else if ($past(instruction[31:30]) == 2'b01 &&
                             $past(instruction[29:16]) == 14'd0) begin
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    if ($past(instruction[15:0]) == 16'd0) begin
                        assert (state == 2'b00 && wait_left == 16'd0);
                        assert_advance();
                    end
                    else
                        assert (state == 2'b01 && pc == $past(pc) &&
                                wait_left == $past(instruction[15:0]));
                end else if ($past(instruction[31:30]) == 2'b01 &&
                             $past(instruction[29]) &&
                             $past(instruction[28:24]) != 5'd0 &&
                             $past(instruction[23:8]) == 16'd0) begin
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    if ($past(instruction_loop_target_wide[5])) begin
                        assert (state == 2'b11 && pc == $past(pc));
                    end else if ($past(loop_active_status)) begin
                        assert (state == 2'b11 && pc == $past(pc));
                    end else if ($past(instruction[7:0]) == 8'd0) begin
                        assert (state == 2'b00 &&
                                pc == $past(instruction_loop_target_wide[4:0]));
                        assert (!loop_active_status);
                    end else begin
                        assert (state == 2'b00 && pc == $past(pc) + 5'd1);
                        assert (loop_active_status);
                        assert (loop_remaining_status == $past(instruction[7:0]));
                        assert (loop_start_status == $past(pc) + 5'd1);
                        assert (loop_end_status == $past(instruction_loop_target_wide[4:0]));
                    end
                end else if ($past(instruction[31:30]) == 2'b10) begin
                    assert (wait_left == 16'd0);
                    if (!$past(instruction[29])) begin
                        assert (state == (($past(instruction) == 32'h80000000) &&
                                          !$past(loop_active_status) &&
                                          !$past(shift_active_status) ? 2'b10 : 2'b11));
                        assert (pc == $past(pc));
                        assert (gpio_value == $past(gpio_value) &&
                                gpio_oe == $past(gpio_oe));
                    end else if (!$past(instruction_shift_valid) ||
                                 ($past(shift_active_status) &&
                                  !$past(shift_config_matches))) begin
                        assert (state == 2'b11 && pc == $past(pc));
                        assert (gpio_value == $past(gpio_value) &&
                                gpio_oe == $past(gpio_oe));
                    end else begin
                        assert (state == 2'b00);
                        assert_advance();
                        assert (gpio_value == (($past(gpio_value) &
                                               ~$past(selected_shift_tx_mask)) |
                                              ($past(selected_shift_tx_bit) ?
                                               $past(selected_shift_tx_mask) : 8'd0)));
                        assert (gpio_oe == (($past(gpio_oe) |
                                            $past(selected_shift_tx_mask)) &
                                           ~$past(selected_shift_rx_mask)));
                        assert (shift_tx_data_status ==
                                $past(selected_shift_tx_next));
                        assert (shift_rx_data_status ==
                                $past(selected_shift_rx_next));
                        if (!$past(shift_active_status)) begin
                            assert (shift_active_status &&
                                    shift_bits_done_status == 3'd1);
                            assert (shift_msb_first_status == $past(instruction[28]));
                            assert (shift_tx_pin_status == $past(instruction[27:25]));
                            assert (shift_rx_pin_status == $past(instruction[24:22]));
                        end else if ($past(shift_bits_done_status) == 3'd7) begin
                            assert (!shift_active_status &&
                                    shift_bits_done_status == 3'd0);
                        end else begin
                            assert (shift_active_status);
                            assert (shift_bits_done_status ==
                                    $past(shift_bits_done_status) + 3'd1);
                        end
                    end
                end else if ($past(instruction[31:30]) == 2'b11 &&
                             $past(instruction[24:16]) == 9'd0) begin
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    if ($past(instruction_input) == $past(instruction[26])) begin
                        assert (state == 2'b00 && wait_left == 16'd0);
                        assert_advance();
                    end else if ($past(instruction[15:0]) == 16'd0) begin
                        assert (wait_left == 16'd0);
                        if ($past(instruction[25]) && !$past(loop_active_status))
                            assert (state == 2'b00 && pc == $past(pc) + 5'd2);
                        else
                            assert (state == 2'b11 && pc == $past(pc));
                    end else begin
                        assert (state == 2'b01 && pc == $past(pc));
                        assert (wait_left == $past(instruction[15:0]) && wait_is_input_status);
                        assert (wait_pin_status == $past(instruction[29:27]));
                        assert (wait_level_status == $past(instruction[26]));
                        assert (wait_timeout_skip_status == $past(instruction[25]));
                    end
                end else begin
                    assert (state == 2'b11 && pc == $past(pc) && wait_left == 16'd0);
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                end
            end
        end
        cover (reset_seen && state == 2'b01 && wait_left == 16'd2);
        cover (reset_seen && state == 2'b10);
        cover (reset_seen && state == 2'b11);
        cover (reset_seen && state == 2'b01 && wait_is_input_status);
        cover (reset_seen && loop_active_status && loop_remaining_status == 8'd2);
        cover (reset_seen && shift_active_status && shift_bits_done_status == 3'd7);
        cover (reset_seen && shift_completion);
    end
endmodule

`default_nettype wire
