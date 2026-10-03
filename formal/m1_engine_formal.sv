/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_engine_formal (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs
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
    wire instruction_input = sampled_inputs[instruction[29:27]];
    reg past_valid = 1'b0;
    reg reset_seen = 1'b0;
    wire latched_input = sampled_inputs[wait_pin_status];

    m1_engine dut (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .instruction(instruction), .instruction_valid(instruction_valid),
        .sampled_inputs(sampled_inputs),
        .pc(pc), .state(state), .wait_left(wait_left),
        .gpio_value(gpio_value), .gpio_oe(gpio_oe),
        .wait_is_input_status(wait_is_input_status),
        .wait_pin_status(wait_pin_status), .wait_level_status(wait_level_status),
        .wait_timeout_skip_status(wait_timeout_skip_status),
        .loop_active_status(loop_active_status),
        .loop_remaining_status(loop_remaining_status),
        .loop_start_status(loop_start_status), .loop_end_status(loop_end_status)
    );

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
            end else if ($past(reset_seen)) begin
                if (!$past(ena) || $past(state) == 2'b10 || $past(state) == 2'b11) begin
                    assert (pc == $past(pc) && state == $past(state));
                    assert (wait_left == $past(wait_left));
                    assert (gpio_value == $past(gpio_value) && gpio_oe == $past(gpio_oe));
                    assert (loop_active_status == $past(loop_active_status));
                    assert (loop_remaining_status == $past(loop_remaining_status));
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
                    if ($past(loop_active_status)) begin
                        assert (state == 2'b11 && pc == $past(pc));
                    end else if ($past(instruction[7:0]) == 8'd0) begin
                        assert (state == 2'b00 &&
                                pc == $past(pc) + 5'd1 + $past(instruction[28:24]));
                        assert (!loop_active_status);
                    end else begin
                        assert (state == 2'b00 && pc == $past(pc) + 5'd1);
                        assert (loop_active_status);
                        assert (loop_remaining_status == $past(instruction[7:0]));
                        assert (loop_start_status == $past(pc) + 5'd1);
                        assert (loop_end_status == $past(pc) + 5'd1 +
                                                           $past(instruction[28:24]));
                    end
                end else if ($past(instruction) == 32'h80000000) begin
                    assert (state == ($past(loop_active_status) ? 2'b11 : 2'b10));
                    assert (pc == $past(pc) && wait_left == 16'd0);
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
    end
endmodule

`default_nettype wire
