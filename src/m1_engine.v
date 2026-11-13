/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_engine #(parameter reg [0:0] COMPACT_PHASE = 1'b1) (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs, input wire [7:0] tx_payload,
    input wire [7:0] tx_payload_alt,
    output reg [7:0] pc, output reg [1:0] state,
    output reg [15:0] wait_left,
    output reg [7:0] gpio_value, output reg [7:0] gpio_oe,
    output wire wait_is_input_status, output wire [2:0] wait_pin_status,
    output wire wait_level_status, output wire wait_timeout_skip_status,
    output wire wait_is_shift_status,
    output wire loop_active_status, output wire [7:0] loop_remaining_status,
    output wire [7:0] loop_start_status, output wire [7:0] loop_end_status,
    output wire shift_active_status, output wire [2:0] shift_bits_done_status,
    output wire shift_msb_first_status, output wire [2:0] shift_tx_pin_status,
    output wire [2:0] shift_rx_pin_status, output wire [7:0] shift_tx_data_status,
    output wire [7:0] shift_rx_data_status,
    output wire shift_burst_status, output wire [15:0] shift_period_status,
    output wire shift_tx_slot_status,
    output wire shift_result_write, output wire [7:0] shift_result_data,
    output wire [7:0] prefetch_pc
);
    localparam reg [1:0] Run=2'b00, Waiting=2'b01, Halted=2'b10, Faulted=2'b11;
    localparam reg [1:0] OpSet=2'b00, OpWait=2'b01, OpHalt=2'b10, OpWaitPin=2'b11;
    reg wait_is_input;
    reg [2:0] wait_pin;
    reg wait_level;
    reg wait_timeout_skip;
    reg wait_timeout_jump;
    reg [7:0] wait_failure_pc;
    reg loop_active;
    reg [7:0] loop_start;
    reg [7:0] loop_end;
    reg [7:0] loop_remaining;
    reg shift_active;
    reg [2:0] shift_bits_done;
    reg shift_msb_first;
    reg [2:0] shift_tx_pin;
    reg [2:0] shift_rx_pin;
    reg [7:0] shift_tx_data;
    reg [7:0] shift_rx_data;
    reg [15:0] shift_period;
    reg shift_tx_slot;
    wire [1:0] opcode = instruction[31:30];
    wire set_valid = (instruction[29:24] == 6'b0);
    wire wait_valid = (instruction[29:16] == 14'b0);
    wire loop_valid = instruction[29] && (instruction[28:24] != 5'd0) &&
                      (instruction[23:8] == 16'd0);
    wire [8:0] loop_target_wide = {1'b0, pc} + 9'd1 +
                                  {4'd0, instruction[28:24]};
    wire loop_target_valid = !loop_target_wide[8];
    wire halt_valid = (instruction[29:0] == 30'b0);
    wire instruction_shift_burst = instruction[21];
    wire [15:0] instruction_shift_period = instruction[20:5];
    wire shift_manual_valid = !instruction_shift_burst &&
                              (instruction[20:2] == 19'd0);
    wire shift_burst_valid = instruction_shift_burst &&
                             (instruction_shift_period >= 16'd2) &&
                             (instruction[4:0] == 5'd0);
    wire shift_valid = instruction[29] &&
                       (instruction[27:25] != instruction[24:22]) &&
                       (shift_manual_valid || shift_burst_valid);
    wire shift_config_matches = (instruction[28] == shift_msb_first) &&
                                (instruction[27:25] == shift_tx_pin) &&
                                (instruction[24:22] == shift_rx_pin) &&
                                !instruction_shift_burst;
    wire selected_shift_order = shift_active ? shift_msb_first : instruction[28];
    wire [2:0] selected_shift_tx_pin = shift_active ? shift_tx_pin : instruction[27:25];
    wire [2:0] selected_shift_rx_pin = shift_active ? shift_rx_pin : instruction[24:22];
    wire serial_open_drain = !instruction_shift_burst && instruction[0];
    wire [7:0] selected_payload = (instruction_shift_burst ? shift_tx_slot : instruction[1]) ?
                                  tx_payload_alt : tx_payload;
    wire selected_shift_tx_bit = shift_active ?
                                 (shift_msb_first ? shift_tx_data[7] : shift_tx_data[0]) :
                                 (instruction[28] ? selected_payload[7] :
                                                    selected_payload[0]);
    wire selected_shift_rx_bit = sampled_inputs[selected_shift_rx_pin];
    wire [7:0] shift_tx_mask = 8'b00000001 << selected_shift_tx_pin;
    wire [7:0] shift_rx_mask = 8'b00000001 << selected_shift_rx_pin;
    wire [7:0] shift_rx_base = shift_active ? shift_rx_data : 8'd0;
    wire [7:0] shift_rx_next = selected_shift_order ?
                               {shift_rx_base[6:0], selected_shift_rx_bit} :
                               {selected_shift_rx_bit, shift_rx_base[7:1]};
    wire wait_pin_valid = instruction[24] ? !instruction[25] :
                          (instruction[23:16] == 8'd0);
    wire selected_input = sampled_inputs[instruction[29:27]];
    wire latched_input = sampled_inputs[wait_pin];
    assign wait_is_input_status = wait_is_input;
    assign wait_pin_status = wait_pin;
    assign wait_level_status = wait_level;
    assign wait_timeout_skip_status = wait_timeout_skip;
    // Zero period denotes ordinary execution; these are derived status bits.
    assign wait_is_shift_status = (shift_period != 16'd0);
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
    assign shift_burst_status = (shift_period >= 16'd2);
    assign shift_period_status = shift_period;
    assign shift_tx_slot_status = shift_tx_slot;

    reg phase_active;
    reg phase_prepared;
    wire phase_drive_word = instruction[29] && !instruction[21] &&
                            (instruction[20:19] == 2'b01);
    wire phase_sample_word = instruction[29] && !instruction[21] &&
                             (instruction[20:19] == 2'b10);
    wire [7:0] phase_aux_mask = COMPACT_PHASE ? instruction[18:11] : 8'd0;
    wire [7:0] phase_aux_value = COMPACT_PHASE ? instruction[10:3] : 8'd0;
    wire [15:0] phase_delay = instruction[18:3];
    wire phase_pins_valid = (instruction[27:25] != instruction[24:22]);
    wire phase_drive_valid = phase_drive_word && phase_pins_valid &&
                             !instruction[2] &&
                             (COMPACT_PHASE || (instruction[18:0] == 19'd0)) &&
                             ((phase_aux_mask & (shift_tx_mask | shift_rx_mask)) == 8'd0) &&
                             (!shift_active ? (!phase_active && !phase_prepared) :
                              (phase_active && !phase_prepared && shift_config_matches));
    wire phase_sample_valid = phase_sample_word && phase_pins_valid &&
                              (instruction[2:0] == 3'd0) &&
                              (COMPACT_PHASE || (instruction[18:0] == 19'd0)) &&
                              phase_active && phase_prepared && shift_active &&
                              shift_config_matches;
    assign shift_result_write = rst_n && ena &&
        (((state == Run) && instruction_valid && (opcode == OpHalt) &&
          ((shift_valid && !phase_active && shift_active && shift_config_matches &&
            (shift_bits_done == 3'd7)) ||
           (phase_sample_valid && (phase_delay == 16'd0) && (shift_bits_done == 3'd7)))) ||
         ((state == Waiting) && (wait_left == 16'd1) && shift_active &&
          (shift_bits_done == 3'd7) &&
          (((shift_period >= 16'd2) && !phase_active) ||
           ((shift_period == 16'd1) && phase_active && phase_prepared))));
    assign shift_result_data = rst_n ? shift_rx_next : 8'd0;

    wire [7:0] serial_drive_value =
        (selected_shift_tx_bit && !serial_open_drain) ? shift_tx_mask : 8'd0;
    wire [7:0] serial_drive_oe =
        (!serial_open_drain || !selected_shift_tx_bit) ? shift_tx_mask : 8'd0;

    reg [7:0] gpio_oe_next;
    reg [7:0] gpio_value_next;
    reg loop_active_next;
    reg [7:0] loop_end_next;
    reg [7:0] loop_remaining_next;
    reg [7:0] loop_start_next;
    reg [7:0] pc_next;
    reg phase_active_next;
    reg phase_prepared_next;
    reg shift_active_next;
    reg [2:0] shift_bits_done_next;
    reg shift_msb_first_next;
    reg [15:0] shift_period_next;
    reg [7:0] shift_rx_data_next;
    reg [2:0] shift_rx_pin_next;
    reg [7:0] shift_tx_data_next;
    reg [2:0] shift_tx_pin_next;
    reg shift_tx_slot_next;
    reg [1:0] state_next;
    reg [7:0] wait_failure_pc_next;
    reg wait_is_input_next;
    reg [15:0] wait_left_next;
    reg wait_level_next;
    reg [2:0] wait_pin_next;
    reg wait_timeout_jump_next;
    reg wait_timeout_skip_next;
    assign prefetch_pc = pc_next;

    task automatic abort_to(input reg [7:0] destination);
        begin
            pc_next = destination;
            state_next = Run;
            wait_left_next = 16'd0;
            wait_is_input_next = 1'b0;
            wait_timeout_skip_next = 1'b0;
            wait_timeout_jump_next = 1'b0;
            wait_failure_pc_next = 8'd0;
            loop_active_next = 1'b0;
            loop_remaining_next = 8'd0;
            loop_start_next = 8'd0;
            loop_end_next = 8'd0;
            shift_active_next = 1'b0;
            shift_bits_done_next = 3'd0;
            shift_period_next = 16'd0;
            phase_active_next = 1'b0;
            phase_prepared_next = 1'b0;
        end
    endtask

    task automatic advance_pc;
        begin
            if (loop_active && ((pc + 8'd1) == loop_end)) begin
                if (loop_remaining > 8'd1) begin
                    pc_next = loop_start;
                    loop_remaining_next = loop_remaining - 8'd1;
                end else begin
                    pc_next = loop_end;
                    loop_remaining_next = 8'd0;
                    loop_active_next = 1'b0;
                end
            end else
                pc_next = pc + 8'd1;
        end
    endtask


    task automatic capture_phase_sample;
        begin
            shift_rx_data_next = shift_rx_next;
            phase_prepared_next = 1'b0;
            if (shift_bits_done == 3'd7) begin
                shift_active_next = 1'b0;
                shift_bits_done_next = 3'd0;
                phase_active_next = 1'b0;
            end else
                shift_bits_done_next = shift_bits_done + 3'd1;
            shift_period_next = 16'd0;
            wait_left_next = 16'd0;
            advance_pc();
            state_next = Run;
        end
    endtask

    always @* begin
        gpio_oe_next = gpio_oe;
        gpio_value_next = gpio_value;
        loop_active_next = loop_active;
        loop_end_next = loop_end;
        loop_remaining_next = loop_remaining;
        loop_start_next = loop_start;
        pc_next = pc;
        phase_active_next = phase_active;
        phase_prepared_next = phase_prepared;
        shift_active_next = shift_active;
        shift_bits_done_next = shift_bits_done;
        shift_msb_first_next = shift_msb_first;
        shift_period_next = shift_period;
        shift_rx_data_next = shift_rx_data;
        shift_rx_pin_next = shift_rx_pin;
        shift_tx_data_next = shift_tx_data;
        shift_tx_pin_next = shift_tx_pin;
        shift_tx_slot_next = shift_tx_slot;
        state_next = state;
        wait_failure_pc_next = wait_failure_pc;
        wait_is_input_next = wait_is_input;
        wait_left_next = wait_left;
        wait_level_next = wait_level;
        wait_pin_next = wait_pin;
        wait_timeout_jump_next = wait_timeout_jump;
        wait_timeout_skip_next = wait_timeout_skip;
        if (!rst_n) begin
            pc_next = 8'd0; state_next = Run; wait_left_next = 16'd0;
            gpio_value_next = 8'd0; gpio_oe_next = 8'd0;
            wait_is_input_next = 1'b0; wait_pin_next = 3'd0; wait_level_next = 1'b0;
            wait_timeout_skip_next = 1'b0;
            wait_timeout_jump_next = 1'b0; wait_failure_pc_next = 8'd0;
            loop_active_next = 1'b0; loop_start_next = 8'd0; loop_end_next = 8'd0;
            loop_remaining_next = 8'd0;
            shift_active_next = 1'b0; shift_bits_done_next = 3'd0;
            shift_msb_first_next = 1'b0; shift_tx_pin_next = 3'd0; shift_rx_pin_next = 3'd0;
            shift_tx_data_next = 8'd0; shift_rx_data_next = 8'd0;
            shift_period_next = 16'd0; shift_tx_slot_next = 1'b0;
            phase_active_next = 1'b0; phase_prepared_next = 1'b0;
        end else begin
            if (ena) begin
                case (state)
                Halted: begin end
                Faulted: begin end
                Waiting: begin
                    if (shift_period == 16'd1) begin
                        if (!phase_active || !phase_prepared || !shift_active) begin
                            state_next = Faulted; wait_left_next = 16'd0;
                        end else if (wait_left > 16'd1)
                            wait_left_next = wait_left - 16'd1;
                        else
                            capture_phase_sample();
                    end else if (shift_period >= 16'd2) begin
                        if (wait_left > 16'd1) begin
                            wait_left_next = wait_left - 16'd1;
                        end else if (shift_active) begin
                            gpio_value_next = (gpio_value & ~shift_tx_mask) |
                                          (selected_shift_tx_bit ? shift_tx_mask : 8'd0);
                            gpio_oe_next = (gpio_oe | shift_tx_mask) & ~shift_rx_mask;
                            shift_rx_data_next = shift_rx_next;
                            shift_tx_data_next = shift_msb_first ?
                                             {shift_tx_data[6:0], 1'b0} :
                                             {1'b0, shift_tx_data[7:1]};
                            if (shift_bits_done == 3'd7) begin
                                shift_active_next = 1'b0;
                                shift_bits_done_next = 3'd0;
                                shift_tx_slot_next = ~shift_tx_slot;
                                wait_left_next = shift_period - 16'd1;
                            end else begin
                                shift_bits_done_next = shift_bits_done + 3'd1;
                                wait_left_next = shift_period;
                            end
                        end else begin
                            wait_left_next = 16'd0;
                            shift_period_next = 16'd0;
                            advance_pc();
                            state_next = Run;
                        end
                    end else if (wait_is_input && (latched_input == wait_level)) begin
                        wait_left_next = 16'd0; advance_pc(); state_next = Run;
                        wait_is_input_next = 1'b0;
                    end else if (wait_is_input && (wait_left == 16'd1)) begin
                        wait_left_next = 16'd0; wait_is_input_next = 1'b0;
                        if (wait_timeout_jump) begin
                            abort_to(wait_failure_pc);
                        end else if (wait_timeout_skip && !loop_active && (pc <= 8'd253)) begin
                            pc_next = pc + 8'd2; state_next = Run;
                        end else
                            state_next = Faulted;
                    end else if (wait_left > 16'd1)
                        wait_left_next = wait_left - 16'd1;
                    else begin
                        wait_left_next = 16'd0; advance_pc(); state_next = Run;
                    end
                end
                default: begin
                    if (!instruction_valid) begin
                        state_next = Faulted; wait_left_next = 16'd0;
                    end else begin
                        case (opcode)
                            OpSet: begin
                                if (!set_valid) begin
                                    state_next = Faulted; wait_left_next = 16'd0;
                                end else begin
                                    gpio_value_next = (gpio_value & ~instruction[23:16]) |
                                                  (instruction[7:0] & instruction[23:16]);
                                    gpio_oe_next = (gpio_oe & ~instruction[23:16]) |
                                               (instruction[15:8] & instruction[23:16]);
                                    advance_pc(); wait_left_next = 16'd0;
                                end
                            end
                            OpWait: begin
                                wait_is_input_next = 1'b0;
                                if (instruction[29]) begin
                                    if (!loop_valid || !loop_target_valid || loop_active) begin
                                        state_next = Faulted; wait_left_next = 16'd0;
                                    end else if (instruction[7:0] == 8'd0) begin
                                        pc_next = loop_target_wide[7:0];
                                        wait_left_next = 16'd0;
                                    end else begin
                                        loop_active_next = 1'b1;
                                        loop_start_next = pc + 8'd1;
                                        loop_end_next = loop_target_wide[7:0];
                                        loop_remaining_next = instruction[7:0];
                                        pc_next = pc + 8'd1;
                                        wait_left_next = 16'd0;
                                    end
                                end else if (!wait_valid) begin
                                    state_next = Faulted; wait_left_next = 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    advance_pc(); wait_left_next = 16'd0;
                                end else begin
                                    state_next = Waiting; wait_left_next = instruction[15:0];
                                end
                            end
                            OpHalt: begin
                                wait_is_input_next = 1'b0;
                                wait_left_next = 16'd0;
                                if (!instruction[29]) begin
                                    state_next = (halt_valid && !loop_active && !shift_active) ?
                                             Halted : Faulted;
                                end else if (phase_drive_word) begin
                                    if (!phase_drive_valid) begin
                                        state_next = Faulted;
                                    end else begin
                                        gpio_value_next =
                                            (gpio_value & ~phase_aux_mask & ~shift_tx_mask) |
                                            (phase_aux_value & phase_aux_mask) |
                                            serial_drive_value;
                                        gpio_oe_next = ((gpio_oe | phase_aux_mask) &
                                                  ~shift_tx_mask & ~shift_rx_mask) |
                                                  serial_drive_oe;
                                        phase_active_next = 1'b1;
                                        phase_prepared_next = 1'b1;
                                        shift_period_next = 16'd0;
                                        if (!shift_active) begin
                                            shift_active_next = 1'b1;
                                            shift_bits_done_next = 3'd0;
                                            shift_rx_data_next = 8'd0;
                                            shift_msb_first_next = instruction[28];
                                            shift_tx_pin_next = instruction[27:25];
                                            shift_rx_pin_next = instruction[24:22];
                                            shift_tx_data_next = instruction[28] ?
                                                             {selected_payload[6:0], 1'b0} :
                                                             {1'b0, selected_payload[7:1]};
                                        end else
                                            shift_tx_data_next = shift_msb_first ?
                                                             {shift_tx_data[6:0], 1'b0} :
                                                             {1'b0, shift_tx_data[7:1]};
                                        advance_pc();
                                    end
                                end else if (phase_sample_word) begin
                                    if (!phase_sample_valid) begin
                                        state_next = Faulted;
                                    end else if (phase_delay == 16'd0) begin
                                        capture_phase_sample();
                                    end else begin
                                        state_next = Waiting;
                                        wait_left_next = phase_delay;
                                        shift_period_next = 16'd1;
                                    end
                                end else if (!shift_valid || phase_active ||
                                             (shift_active && !shift_config_matches)) begin
                                    state_next = Faulted;
                                end else begin
                                    gpio_value_next = (gpio_value & ~shift_tx_mask) |
                                                  serial_drive_value;
                                    gpio_oe_next = (gpio_oe & ~shift_tx_mask & ~shift_rx_mask) |
                                              serial_drive_oe;
                                    shift_rx_data_next = shift_rx_next;
                                    if (!shift_active) begin
                                        shift_active_next = 1'b1;
                                        shift_bits_done_next = 3'd1;
                                        shift_msb_first_next = instruction[28];
                                        shift_tx_pin_next = instruction[27:25];
                                        shift_rx_pin_next = instruction[24:22];
                                        shift_period_next = instruction_shift_burst ?
                                                        instruction_shift_period : 16'd0;
                                        shift_tx_data_next = instruction[28] ?
                                                         {selected_payload[6:0], 1'b0} :
                                                         {1'b0, selected_payload[7:1]};
                                    end else begin
                                        shift_tx_data_next = shift_msb_first ?
                                                         {shift_tx_data[6:0], 1'b0} :
                                                         {1'b0, shift_tx_data[7:1]};
                                        if (shift_bits_done == 3'd7) begin
                                            shift_active_next = 1'b0;
                                            shift_bits_done_next = 3'd0;
                                        end else
                                            shift_bits_done_next = shift_bits_done + 3'd1;
                                    end
                                    if (instruction_shift_burst) begin
                                        state_next = Waiting;
                                        wait_left_next = instruction_shift_period;
                                    end else
                                        advance_pc();
                                end
                            end
                            OpWaitPin: begin
                                if (!wait_pin_valid) begin
                                    state_next = Faulted; wait_left_next = 16'd0;
                                end else if (selected_input == instruction[26]) begin
                                    advance_pc(); wait_left_next = 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    wait_left_next = 16'd0;
                                    if (instruction[24])
                                        abort_to(instruction[23:16]);
                                    else if (instruction[25] && !loop_active && (pc <= 8'd253))
                                        pc_next = pc + 8'd2;
                                    else
                                        state_next = Faulted;
                                end else begin
                                    state_next = Waiting; wait_left_next = instruction[15:0];
                                    wait_is_input_next = 1'b1;
                                    wait_pin_next = instruction[29:27];
                                    wait_level_next = instruction[26];
                                    wait_timeout_skip_next = instruction[25];
                                    wait_timeout_jump_next = instruction[24];
                                    wait_failure_pc_next = instruction[23:16];
                                end
                            end
                            default: begin
                                state_next = Faulted; wait_left_next = 16'd0;
                                wait_is_input_next = 1'b0;
                            end
                        endcase
                    end
                end
                endcase
            end
        end
    end
    always @(posedge clk) begin
        gpio_oe <= gpio_oe_next;
        gpio_value <= gpio_value_next;
        loop_active <= loop_active_next;
        loop_end <= loop_end_next;
        loop_remaining <= loop_remaining_next;
        loop_start <= loop_start_next;
        pc <= pc_next;
        phase_active <= phase_active_next;
        phase_prepared <= phase_prepared_next;
        shift_active <= shift_active_next;
        shift_bits_done <= shift_bits_done_next;
        shift_msb_first <= shift_msb_first_next;
        shift_period <= shift_period_next;
        shift_rx_data <= shift_rx_data_next;
        shift_rx_pin <= shift_rx_pin_next;
        shift_tx_data <= shift_tx_data_next;
        shift_tx_pin <= shift_tx_pin_next;
        shift_tx_slot <= shift_tx_slot_next;
        state <= state_next;
        wait_failure_pc <= wait_failure_pc_next;
        wait_is_input <= wait_is_input_next;
        wait_left <= wait_left_next;
        wait_level <= wait_level_next;
        wait_pin <= wait_pin_next;
        wait_timeout_jump <= wait_timeout_jump_next;
        wait_timeout_skip <= wait_timeout_skip_next;
    end
endmodule

`default_nettype wire
