/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out,
    output wire [7:0] uio_oe, input wire ena, input wire clk, input wire rst_n,
    output wire f_formal_gpio_pending,
    output wire [7:0] f_formal_gpio_pending_value,
    output wire [7:0] f_formal_gpio_pending_oe,
    output wire [4:0] f_pc,
    output wire [1:0] f_state,
    output wire [15:0] f_wait_left,
    output wire [7:0] f_gpio_value,
    output wire [7:0] f_gpio_oe,
    output wire f_wait_is_input_status,
    output wire [2:0] f_wait_pin_status,
    output wire f_wait_level_status,
    output wire f_wait_timeout_skip_status,
    output wire f_wait_is_shift_status,
    output wire f_loop_active_status,
    output wire [7:0] f_loop_remaining_status,
    output wire [4:0] f_loop_start_status,
    output wire [4:0] f_loop_end_status,
    output wire f_shift_active_status,
    output wire [2:0] f_shift_bits_done_status,
    output wire f_shift_msb_first_status,
    output wire [2:0] f_shift_tx_pin_status,
    output wire [2:0] f_shift_rx_pin_status,
    output wire [7:0] f_shift_tx_data_status,
    output wire [7:0] f_shift_rx_data_status,
    output wire f_shift_burst_status,
    output wire [15:0] f_shift_period_status,
    output wire f_shift_tx_slot_status,
    output wire f_shift_result_write,
    output wire [7:0] f_shift_result_data,
    output wire f_formal_phase_active,
    output wire f_formal_phase_prepared,
    output wire [255:0] f_formal_program_bits,
    output wire [7:0] f_formal_sync_meta,
    output wire [7:0] f_sampled_inputs,
    output wire [7:0] f_tx_payload,
    output wire [7:0] f_tx_payload_alt,
    output wire [7:0] f_rx_result,
    output wire f_rx_valid,
    output wire [3:0] f_program_length,
    output wire f_program_ready,
    output wire [31:0] f_instruction,
    output wire f_instruction_valid
);
    wire load_mode = ui_in[7];
    wire load_write = ui_in[6];
    wire load_register = ui_in[5];
    wire [4:0] byte_address = ui_in[4:0];
    wire [4:0] pc;
    wire [1:0] state;
    wire [15:0] wait_left;
    wire [7:0] gpio_value;
    wire [7:0] gpio_oe;
    wire [7:0] program_loader_data_out;
    wire [7:0] register_data_out;
    wire [7:0] loader_data_out;
    wire [3:0] program_length;
    wire program_ready;
    wire [31:0] instruction;
    wire instruction_valid;
    wire [7:0] sampled_inputs;
    wire wait_is_input_status;
    wire [2:0] wait_pin_status;
    wire wait_level_status;
    wire wait_timeout_skip_status;
    wire wait_is_shift_status;
    wire loop_active_status;
    wire [7:0] loop_remaining_status;
    wire [4:0] loop_start_status;
    wire [4:0] loop_end_status;
    wire [7:0] tx_payload;
    wire [7:0] tx_payload_alt;
    wire [7:0] rx_result;
    wire rx_valid;
    wire shift_active_status;
    wire [2:0] shift_bits_done_status;
    wire shift_msb_first_status;
    wire [2:0] shift_tx_pin_status;
    wire [2:0] shift_rx_pin_status;
    wire [7:0] shift_tx_data_status;
    wire [7:0] shift_rx_data_status;
    wire shift_burst_status;
    wire [15:0] shift_period_status;
    wire shift_tx_slot_status;
    wire shift_result_write;
    wire [7:0] shift_result_data;
    wire formal_phase_active,formal_phase_prepared;
    wire [255:0] formal_program_bits;
    wire [7:0] formal_sync_meta;
    wire formal_gpio_pending;
    wire [7:0] formal_gpio_pending_value;
    wire [7:0] formal_gpio_pending_oe;
    wire engine_rst_n = rst_n && program_ready && !load_mode;
    wire program_store_selected = load_mode &&
                                  (!load_register || (byte_address == 5'd0));
    wire data_store_selected = load_mode && load_register;
    wire runtime_read = !load_mode && load_write && load_register;

    m1_program_store store (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .load_mode(program_store_selected), .load_write(load_write),
        .load_length(load_register),
        .byte_address(byte_address), .data_in(uio_in), .pc(pc),
        .data_out(program_loader_data_out), .program_length(program_length),
        .program_ready(program_ready), .instruction(instruction),
        .instruction_valid(instruction_valid), .formal_program_bits(formal_program_bits)
    );

    m1_data_store data_store (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .register_select(data_store_selected),
        .register_write(load_write), .register_address(byte_address),
        .data_in(uio_in), .shift_result_write(shift_result_write),
        .shift_result_data(shift_result_data), .data_out(register_data_out),
        .tx_payload(tx_payload), .tx_payload_alt(tx_payload_alt),
        .rx_result(rx_result), .rx_valid(rx_valid)
    );

    m1_input_sync input_sync (
        .clk(clk), .rst_n(rst_n), .async_in(uio_in), .sampled_in(sampled_inputs), .formal_meta(formal_sync_meta)
    );

    phase_engine engine (
        .clk(clk), .rst_n(engine_rst_n), .ena(ena),
        .instruction(instruction), .instruction_valid(instruction_valid),
        .sampled_inputs(sampled_inputs), .tx_payload(tx_payload),
        .tx_payload_alt(tx_payload_alt),
        .pc(pc), .state(state), .wait_left(wait_left),
        .gpio_value(gpio_value), .gpio_oe(gpio_oe),
        .wait_is_input_status(wait_is_input_status),
        .wait_pin_status(wait_pin_status), .wait_level_status(wait_level_status),
        .wait_timeout_skip_status(wait_timeout_skip_status),
        .wait_is_shift_status(wait_is_shift_status),
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
        .shift_burst_status(shift_burst_status),
        .shift_period_status(shift_period_status),
        .shift_tx_slot_status(shift_tx_slot_status),
        .shift_result_write(shift_result_write),
        .shift_result_data(shift_result_data), .formal_phase_active(formal_phase_active), .formal_phase_prepared(formal_phase_prepared), .formal_gpio_pending(formal_gpio_pending), .formal_gpio_pending_value(formal_gpio_pending_value), .formal_gpio_pending_oe(formal_gpio_pending_oe)
    );

    assign loader_data_out = (load_register && (byte_address != 5'd0)) ?
                             register_data_out : program_loader_data_out;
    assign uio_out = load_mode ? loader_data_out : gpio_value;
    assign uio_oe = load_mode ? (load_write ? 8'h00 : 8'hff) : gpio_oe;
    assign uo_out = runtime_read ? register_data_out : {state, program_ready, pc};
`ifdef FORMAL
    // Check public decode/ownership against pins, not the runtime_read alias.
    always_comb begin
        if (ui_in[7:5] == 3'b011) begin
            case (ui_in[4:0])
                5'd1: assert (uo_out == tx_payload);
                5'd2: assert (uo_out == rx_result);
                5'd3: assert (uo_out == {7'b0, rx_valid});
                5'd4: assert (uo_out == tx_payload_alt);
                default: assert (uo_out == 8'b0);
            endcase
        end else begin
            assert (uo_out == {state, program_ready, pc});
        end
        if (!ui_in[7]) begin
            assert (uio_out == gpio_value);
            assert (uio_oe == gpio_oe);
            assert (!program_store_selected && !data_store_selected);
            assert (engine_rst_n == (rst_n && program_ready));
        end else begin
            assert (uio_out == loader_data_out);
            assert (uio_oe == (ui_in[6] ? 8'h00 : 8'hff));
            assert (!engine_rst_n);
        end
    end
`endif
    wire _unused = &{wait_left, program_length, wait_is_input_status,
                     wait_pin_status, wait_level_status,
                     wait_timeout_skip_status, loop_active_status,
                     loop_remaining_status, loop_start_status, loop_end_status,
                     rx_result, rx_valid, shift_active_status,
                     shift_bits_done_status, shift_msb_first_status,
                     shift_tx_pin_status, shift_rx_pin_status,
                     shift_tx_data_status, shift_rx_data_status,
                     wait_is_shift_status, shift_burst_status,
                     shift_period_status, shift_tx_slot_status, 1'b0};
    assign f_pc=pc;
    assign f_state=state;
    assign f_wait_left=wait_left;
    assign f_gpio_value=gpio_value;
    assign f_gpio_oe=gpio_oe;
    assign f_wait_is_input_status=wait_is_input_status;
    assign f_wait_pin_status=wait_pin_status;
    assign f_wait_level_status=wait_level_status;
    assign f_wait_timeout_skip_status=wait_timeout_skip_status;
    assign f_wait_is_shift_status=wait_is_shift_status;
    assign f_loop_active_status=loop_active_status;
    assign f_loop_remaining_status=loop_remaining_status;
    assign f_loop_start_status=loop_start_status;
    assign f_loop_end_status=loop_end_status;
    assign f_shift_active_status=shift_active_status;
    assign f_shift_bits_done_status=shift_bits_done_status;
    assign f_shift_msb_first_status=shift_msb_first_status;
    assign f_shift_tx_pin_status=shift_tx_pin_status;
    assign f_shift_rx_pin_status=shift_rx_pin_status;
    assign f_shift_tx_data_status=shift_tx_data_status;
    assign f_shift_rx_data_status=shift_rx_data_status;
    assign f_shift_burst_status=shift_burst_status;
    assign f_shift_period_status=shift_period_status;
    assign f_shift_tx_slot_status=shift_tx_slot_status;
    assign f_shift_result_write=shift_result_write;
    assign f_shift_result_data=shift_result_data;
    assign f_formal_phase_active=formal_phase_active;
    assign f_formal_phase_prepared=formal_phase_prepared;
    assign f_formal_program_bits=formal_program_bits;
    assign f_formal_sync_meta=formal_sync_meta;
    assign f_sampled_inputs=sampled_inputs;
    assign f_tx_payload=tx_payload;
    assign f_tx_payload_alt=tx_payload_alt;
    assign f_rx_result=rx_result;
    assign f_rx_valid=rx_valid;
    assign f_program_length=program_length;
    assign f_program_ready=program_ready;
    assign f_instruction=instruction;
    assign f_instruction_valid=instruction_valid;

    assign f_formal_gpio_pending=formal_gpio_pending;
    assign f_formal_gpio_pending_value=formal_gpio_pending_value;
    assign f_formal_gpio_pending_oe=formal_gpio_pending_oe;
endmodule

`default_nettype wire
