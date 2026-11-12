wire [4:0] c_pc;
wire [1:0] c_state;
wire [15:0] c_wait_left;
wire [7:0] c_gpio_value;
wire [7:0] c_gpio_oe;
wire c_wait_is_input_status;
wire [2:0] c_wait_pin_status;
wire c_wait_level_status;
wire c_wait_timeout_skip_status;
wire c_wait_is_shift_status;
wire c_loop_active_status;
wire [7:0] c_loop_remaining_status;
wire [4:0] c_loop_start_status;
wire [4:0] c_loop_end_status;
wire c_shift_active_status;
wire [2:0] c_shift_bits_done_status;
wire c_shift_msb_first_status;
wire [2:0] c_shift_tx_pin_status;
wire [2:0] c_shift_rx_pin_status;
wire [7:0] c_shift_tx_data_status;
wire [7:0] c_shift_rx_data_status;
wire c_shift_burst_status;
wire [15:0] c_shift_period_status;
wire c_shift_tx_slot_status;
wire c_shift_result_write;
wire [7:0] c_shift_result_data;
wire c_formal_phase_active;
wire c_formal_phase_prepared;
wire c_formal_gpio_pending;
wire [7:0] c_formal_gpio_pending_value;
wire [7:0] c_formal_gpio_pending_oe;
wire [4:0] l_pc;
wire [1:0] l_state;
wire [15:0] l_wait_left;
wire [7:0] l_gpio_value;
wire [7:0] l_gpio_oe;
wire l_wait_is_input_status;
wire [2:0] l_wait_pin_status;
wire l_wait_level_status;
wire l_wait_timeout_skip_status;
wire l_wait_is_shift_status;
wire l_loop_active_status;
wire [7:0] l_loop_remaining_status;
wire [4:0] l_loop_start_status;
wire [4:0] l_loop_end_status;
wire l_shift_active_status;
wire [2:0] l_shift_bits_done_status;
wire l_shift_msb_first_status;
wire [2:0] l_shift_tx_pin_status;
wire [2:0] l_shift_rx_pin_status;
wire [7:0] l_shift_tx_data_status;
wire [7:0] l_shift_rx_data_status;
wire l_shift_burst_status;
wire [15:0] l_shift_period_status;
wire l_shift_tx_slot_status;
wire l_shift_result_write;
wire [7:0] l_shift_result_data;
wire l_formal_phase_active;
wire l_formal_phase_prepared;
phase_engine candidate(.clk(clk),
.rst_n(rst_n),
.ena(ena),
.instruction(instruction),
.instruction_valid(instruction_valid),
.sampled_inputs(sampled_inputs),
.tx_payload(tx_payload),
.tx_payload_alt(tx_payload_alt),
.pc(c_pc),
.state(c_state),
.wait_left(c_wait_left),
.gpio_value(c_gpio_value),
.gpio_oe(c_gpio_oe),
.wait_is_input_status(c_wait_is_input_status),
.wait_pin_status(c_wait_pin_status),
.wait_level_status(c_wait_level_status),
.wait_timeout_skip_status(c_wait_timeout_skip_status),
.wait_is_shift_status(c_wait_is_shift_status),
.loop_active_status(c_loop_active_status),
.loop_remaining_status(c_loop_remaining_status),
.loop_start_status(c_loop_start_status),
.loop_end_status(c_loop_end_status),
.shift_active_status(c_shift_active_status),
.shift_bits_done_status(c_shift_bits_done_status),
.shift_msb_first_status(c_shift_msb_first_status),
.shift_tx_pin_status(c_shift_tx_pin_status),
.shift_rx_pin_status(c_shift_rx_pin_status),
.shift_tx_data_status(c_shift_tx_data_status),
.shift_rx_data_status(c_shift_rx_data_status),
.shift_burst_status(c_shift_burst_status),
.shift_period_status(c_shift_period_status),
.shift_tx_slot_status(c_shift_tx_slot_status),
.shift_result_write(c_shift_result_write),
.shift_result_data(c_shift_result_data),
.formal_phase_active(c_formal_phase_active),
.formal_phase_prepared(c_formal_phase_prepared),
.formal_gpio_pending(c_formal_gpio_pending),
.formal_gpio_pending_value(c_formal_gpio_pending_value),
.formal_gpio_pending_oe(c_formal_gpio_pending_oe));
compact_engine compact(.clk(clk),
.rst_n(rst_n),
.ena(ena),
.instruction(instruction),
.instruction_valid(instruction_valid),
.sampled_inputs(sampled_inputs),
.tx_payload(tx_payload),
.tx_payload_alt(tx_payload_alt),
.pc(l_pc),
.state(l_state),
.wait_left(l_wait_left),
.gpio_value(l_gpio_value),
.gpio_oe(l_gpio_oe),
.wait_is_input_status(l_wait_is_input_status),
.wait_pin_status(l_wait_pin_status),
.wait_level_status(l_wait_level_status),
.wait_timeout_skip_status(l_wait_timeout_skip_status),
.wait_is_shift_status(l_wait_is_shift_status),
.loop_active_status(l_loop_active_status),
.loop_remaining_status(l_loop_remaining_status),
.loop_start_status(l_loop_start_status),
.loop_end_status(l_loop_end_status),
.shift_active_status(l_shift_active_status),
.shift_bits_done_status(l_shift_bits_done_status),
.shift_msb_first_status(l_shift_msb_first_status),
.shift_tx_pin_status(l_shift_tx_pin_status),
.shift_rx_pin_status(l_shift_rx_pin_status),
.shift_tx_data_status(l_shift_tx_data_status),
.shift_rx_data_status(l_shift_rx_data_status),
.shift_burst_status(l_shift_burst_status),
.shift_period_status(l_shift_period_status),
.shift_tx_slot_status(l_shift_tx_slot_status),
.shift_result_write(l_shift_result_write),
.shift_result_data(l_shift_result_data),
.formal_phase_active(l_formal_phase_active),
.formal_phase_prepared(l_formal_phase_prepared));
wire [120:0] candidate_outputs = {c_pc,c_state,c_wait_left,c_gpio_value,c_gpio_oe,c_wait_is_input_status,c_wait_pin_status,c_wait_level_status,c_wait_timeout_skip_status,c_wait_is_shift_status,c_loop_active_status,c_loop_remaining_status,c_loop_start_status,c_loop_end_status,c_shift_active_status,c_shift_bits_done_status,c_shift_msb_first_status,c_shift_tx_pin_status,c_shift_rx_pin_status,c_shift_tx_data_status,c_shift_rx_data_status,c_shift_burst_status,c_shift_period_status,c_shift_tx_slot_status,c_shift_result_write,c_shift_result_data,c_formal_phase_active,c_formal_phase_prepared};
wire [120:0] compact_outputs = {l_pc,l_state,l_wait_left,l_gpio_value,l_gpio_oe,l_wait_is_input_status,l_wait_pin_status,l_wait_level_status,l_wait_timeout_skip_status,l_wait_is_shift_status,l_loop_active_status,l_loop_remaining_status,l_loop_start_status,l_loop_end_status,l_shift_active_status,l_shift_bits_done_status,l_shift_msb_first_status,l_shift_tx_pin_status,l_shift_rx_pin_status,l_shift_tx_data_status,l_shift_rx_data_status,l_shift_burst_status,l_shift_period_status,l_shift_tx_slot_status,l_shift_result_write,l_shift_result_data,l_formal_phase_active,l_formal_phase_prepared};
