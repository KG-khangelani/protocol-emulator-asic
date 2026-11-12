/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out,
    output wire [7:0] uio_oe, input wire ena, input wire clk, input wire rst_n
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
        .instruction_valid(instruction_valid)
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
        .clk(clk), .rst_n(rst_n), .async_in(uio_in), .sampled_in(sampled_inputs)
    );

    m1_engine engine (
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
        .shift_result_data(shift_result_data)
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
endmodule

`default_nettype wire
