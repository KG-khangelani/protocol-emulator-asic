/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_engine (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs, input wire [7:0] tx_payload,
    output reg [4:0] pc, output reg [1:0] state,
    output reg [15:0] wait_left,
    output reg [7:0] gpio_value, output reg [7:0] gpio_oe,
    output wire wait_is_input_status, output wire [2:0] wait_pin_status,
    output wire wait_level_status, output wire wait_timeout_skip_status,
    output wire loop_active_status, output wire [7:0] loop_remaining_status,
    output wire [4:0] loop_start_status, output wire [4:0] loop_end_status,
    output wire shift_active_status, output wire [2:0] shift_bits_done_status,
    output wire shift_msb_first_status, output wire [2:0] shift_tx_pin_status,
    output wire [2:0] shift_rx_pin_status, output wire [7:0] shift_tx_data_status,
    output wire [7:0] shift_rx_data_status,
    output wire shift_result_write, output wire [7:0] shift_result_data
);
    localparam reg [1:0] Run=2'b00, Waiting=2'b01, Halted=2'b10, Faulted=2'b11;
    localparam reg [1:0] OpSet=2'b00, OpWait=2'b01, OpHalt=2'b10, OpWaitPin=2'b11;
    reg wait_is_input;
    reg [2:0] wait_pin;
    reg wait_level;
    reg wait_timeout_skip;
    reg loop_active;
    reg [4:0] loop_start;
    reg [4:0] loop_end;
    reg [7:0] loop_remaining;
    reg shift_active;
    reg [2:0] shift_bits_done;
    reg shift_msb_first;
    reg [2:0] shift_tx_pin;
    reg [2:0] shift_rx_pin;
    reg [7:0] shift_tx_data;
    reg [7:0] shift_rx_data;
    wire [1:0] opcode = instruction[31:30];
    wire set_valid = (instruction[29:24] == 6'b0);
    wire wait_valid = (instruction[29:16] == 14'b0);
    wire loop_valid = instruction[29] && (instruction[28:24] != 5'd0) &&
                      (instruction[23:8] == 16'd0);
    wire [5:0] loop_target_wide = {1'b0, pc} + 6'd1 +
                                  {1'b0, instruction[28:24]};
    wire loop_target_valid = !loop_target_wide[5];
    wire halt_valid = (instruction[29:0] == 30'b0);
    wire shift_valid = instruction[29] && (instruction[21:0] == 22'd0) &&
                       (instruction[27:25] != instruction[24:22]);
    wire shift_config_matches = (instruction[28] == shift_msb_first) &&
                                (instruction[27:25] == shift_tx_pin) &&
                                (instruction[24:22] == shift_rx_pin);
    wire selected_shift_order = shift_active ? shift_msb_first : instruction[28];
    wire [2:0] selected_shift_tx_pin = shift_active ? shift_tx_pin : instruction[27:25];
    wire [2:0] selected_shift_rx_pin = shift_active ? shift_rx_pin : instruction[24:22];
    wire selected_shift_tx_bit = shift_active ?
                                 (shift_msb_first ? shift_tx_data[7] : shift_tx_data[0]) :
                                 (instruction[28] ? tx_payload[7] : tx_payload[0]);
    wire selected_shift_rx_bit = sampled_inputs[selected_shift_rx_pin];
    wire [7:0] shift_tx_mask = 8'b00000001 << selected_shift_tx_pin;
    wire [7:0] shift_rx_mask = 8'b00000001 << selected_shift_rx_pin;
    wire [7:0] shift_rx_base = shift_active ? shift_rx_data : 8'd0;
    wire [7:0] shift_rx_next = selected_shift_order ?
                               {shift_rx_base[6:0], selected_shift_rx_bit} :
                               {selected_shift_rx_bit, shift_rx_base[7:1]};
    wire wait_pin_valid = (instruction[24:16] == 9'b0);
    wire selected_input = sampled_inputs[instruction[29:27]];
    wire latched_input = sampled_inputs[wait_pin];
    assign wait_is_input_status = wait_is_input;
    assign wait_pin_status = wait_pin;
    assign wait_level_status = wait_level;
    assign wait_timeout_skip_status = wait_timeout_skip;
    assign loop_active_status = loop_active;
    assign loop_remaining_status = loop_remaining;
    assign loop_start_status = loop_start;
    assign loop_end_status = loop_end;
    assign shift_active_status = shift_active;
    assign shift_bits_done_status = shift_bits_done;
    assign shift_msb_first_status = shift_msb_first;
    assign shift_tx_pin_status = shift_tx_pin;
    assign shift_rx_pin_status = shift_rx_pin;
    assign shift_tx_data_status = shift_tx_data;
    assign shift_rx_data_status = shift_rx_data;
    assign shift_result_write = rst_n && ena && (state == Run) &&
                                instruction_valid && (opcode == OpHalt) &&
                                shift_valid && shift_active &&
                                shift_config_matches && (shift_bits_done == 3'd7);
    assign shift_result_data = rst_n ? shift_rx_next : 8'd0;

    task automatic advance_pc;
        begin
            if (loop_active && ((pc + 5'd1) == loop_end)) begin
                if (loop_remaining > 8'd1) begin
                    pc <= loop_start;
                    loop_remaining <= loop_remaining - 8'd1;
                end else begin
                    pc <= loop_end;
                    loop_remaining <= 8'd0;
                    loop_active <= 1'b0;
                end
            end else
                pc <= pc + 5'd1;
        end
    endtask

    always @(posedge clk) begin
        if (!rst_n) begin
            pc <= 5'd0; state <= Run; wait_left <= 16'd0;
            gpio_value <= 8'd0; gpio_oe <= 8'd0;
            wait_is_input <= 1'b0; wait_pin <= 3'd0; wait_level <= 1'b0;
            wait_timeout_skip <= 1'b0;
            loop_active <= 1'b0; loop_start <= 5'd0; loop_end <= 5'd0;
            loop_remaining <= 8'd0;
            shift_active <= 1'b0; shift_bits_done <= 3'd0;
            shift_msb_first <= 1'b0; shift_tx_pin <= 3'd0; shift_rx_pin <= 3'd0;
            shift_tx_data <= 8'd0; shift_rx_data <= 8'd0;
        end else begin
            if (ena) begin
                case (state)
                Halted: begin end
                Faulted: begin end
                Waiting: begin
                    if (wait_is_input && (latched_input == wait_level)) begin
                        wait_left <= 16'd0; advance_pc(); state <= Run;
                        wait_is_input <= 1'b0;
                    end else if (wait_is_input && (wait_left == 16'd1)) begin
                        wait_left <= 16'd0; wait_is_input <= 1'b0;
                        if (wait_timeout_skip && !loop_active) begin
                            pc <= pc + 5'd2; state <= Run;
                        end else
                            state <= Faulted;
                    end else if (wait_left > 16'd1)
                        wait_left <= wait_left - 16'd1;
                    else begin
                        wait_left <= 16'd0; advance_pc(); state <= Run;
                    end
                end
                default: begin
                    if (!instruction_valid) begin
                        state <= Faulted; wait_left <= 16'd0;
                    end else begin
                        case (opcode)
                            OpSet: begin
                                if (!set_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else begin
                                    gpio_value <= (gpio_value & ~instruction[23:16]) |
                                                  (instruction[7:0] & instruction[23:16]);
                                    gpio_oe <= (gpio_oe & ~instruction[23:16]) |
                                               (instruction[15:8] & instruction[23:16]);
                                    advance_pc(); wait_left <= 16'd0;
                                end
                            end
                            OpWait: begin
                                wait_is_input <= 1'b0;
                                if (instruction[29]) begin
                                    if (!loop_valid || !loop_target_valid || loop_active) begin
                                        state <= Faulted; wait_left <= 16'd0;
                                    end else if (instruction[7:0] == 8'd0) begin
                                        pc <= loop_target_wide[4:0];
                                        wait_left <= 16'd0;
                                    end else begin
                                        loop_active <= 1'b1;
                                        loop_start <= pc + 5'd1;
                                        loop_end <= loop_target_wide[4:0];
                                        loop_remaining <= instruction[7:0];
                                        pc <= pc + 5'd1;
                                        wait_left <= 16'd0;
                                    end
                                end else if (!wait_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    advance_pc(); wait_left <= 16'd0;
                                end else begin
                                    state <= Waiting; wait_left <= instruction[15:0];
                                end
                            end
                            OpHalt: begin
                                wait_is_input <= 1'b0;
                                wait_left <= 16'd0;
                                if (!instruction[29]) begin
                                    state <= (halt_valid && !loop_active && !shift_active) ?
                                             Halted : Faulted;
                                end else if (!shift_valid ||
                                             (shift_active && !shift_config_matches)) begin
                                    state <= Faulted;
                                end else begin
                                    gpio_value <= (gpio_value & ~shift_tx_mask) |
                                                  (selected_shift_tx_bit ? shift_tx_mask : 8'd0);
                                    gpio_oe <= (gpio_oe | shift_tx_mask) & ~shift_rx_mask;
                                    shift_rx_data <= shift_rx_next;
                                    if (!shift_active) begin
                                        shift_active <= 1'b1;
                                        shift_bits_done <= 3'd1;
                                        shift_msb_first <= instruction[28];
                                        shift_tx_pin <= instruction[27:25];
                                        shift_rx_pin <= instruction[24:22];
                                        shift_tx_data <= instruction[28] ?
                                                         {tx_payload[6:0], 1'b0} :
                                                         {1'b0, tx_payload[7:1]};
                                    end else begin
                                        shift_tx_data <= shift_msb_first ?
                                                         {shift_tx_data[6:0], 1'b0} :
                                                         {1'b0, shift_tx_data[7:1]};
                                        if (shift_bits_done == 3'd7) begin
                                            shift_active <= 1'b0;
                                            shift_bits_done <= 3'd0;
                                        end else begin
                                            shift_bits_done <= shift_bits_done + 3'd1;
                                        end
                                    end
                                    advance_pc();
                                end
                            end
                            OpWaitPin: begin
                                if (!wait_pin_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else if (selected_input == instruction[26]) begin
                                    advance_pc(); wait_left <= 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    wait_left <= 16'd0;
                                    if (instruction[25] && !loop_active)
                                        pc <= pc + 5'd2;
                                    else
                                        state <= Faulted;
                                end else begin
                                    state <= Waiting; wait_left <= instruction[15:0];
                                    wait_is_input <= 1'b1;
                                    wait_pin <= instruction[29:27];
                                    wait_level <= instruction[26];
                                    wait_timeout_skip <= instruction[25];
                                end
                            end
                            default: begin
                                state <= Faulted; wait_left <= 16'd0;
                                wait_is_input <= 1'b0;
                            end
                        endcase
                    end
                end
                endcase
            end
        end
    end
endmodule

`default_nettype wire
