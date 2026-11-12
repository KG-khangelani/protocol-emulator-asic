wire [4:0] pc;
wire [1:0] state;
wire [15:0] wait_left;
wire [7:0] gpio_value;
wire [7:0] gpio_oe;
wire wait_is_input_status;
wire [2:0] wait_pin_status;
wire wait_level_status;
wire wait_timeout_skip_status;
wire wait_is_shift_status;
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
wire shift_burst_status;
wire [15:0] shift_period_status;
wire shift_tx_slot_status;
wire shift_result_write;
wire [7:0] shift_result_data;
wire formal_phase_active;
wire formal_phase_prepared;
wire formal_gpio_pending;
wire [7:0] formal_gpio_pending_value;
wire [7:0] formal_gpio_pending_oe;
phase_engine dut(.clk(clk),
.rst_n(rst_n),
.ena(ena),
.instruction(instruction),
.instruction_valid(instruction_valid),
.sampled_inputs(sampled_inputs),
.tx_payload(tx_payload),
.tx_payload_alt(tx_payload_alt),
.pc(pc),
.state(state),
.wait_left(wait_left),
.gpio_value(gpio_value),
.gpio_oe(gpio_oe),
.wait_is_input_status(wait_is_input_status),
.wait_pin_status(wait_pin_status),
.wait_level_status(wait_level_status),
.wait_timeout_skip_status(wait_timeout_skip_status),
.wait_is_shift_status(wait_is_shift_status),
.loop_active_status(loop_active_status),
.loop_remaining_status(loop_remaining_status),
.loop_start_status(loop_start_status),
.loop_end_status(loop_end_status),
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
.shift_result_data(shift_result_data),
.formal_phase_active(formal_phase_active),
.formal_phase_prepared(formal_phase_prepared),
.formal_gpio_pending(formal_gpio_pending),
.formal_gpio_pending_value(formal_gpio_pending_value),
.formal_gpio_pending_oe(formal_gpio_pending_oe));
wire [126:0] all_state = {pc,state,wait_left,gpio_value,gpio_oe,wait_is_input_status,wait_pin_status,wait_level_status,wait_timeout_skip_status,loop_active_status,loop_remaining_status,loop_start_status,loop_end_status,shift_active_status,shift_bits_done_status,shift_msb_first_status,shift_tx_pin_status,shift_rx_pin_status,shift_tx_data_status,shift_rx_data_status,shift_period_status,shift_tx_slot_status,formal_phase_active,formal_phase_prepared,formal_gpio_pending,formal_gpio_pending_value,formal_gpio_pending_oe};
wire [103:0] phase_latched_state = {gpio_value,gpio_oe,wait_is_input_status,wait_pin_status,wait_level_status,wait_timeout_skip_status,loop_active_status,loop_remaining_status,loop_start_status,loop_end_status,shift_active_status,shift_bits_done_status,shift_msb_first_status,shift_tx_pin_status,shift_rx_pin_status,shift_tx_data_status,shift_rx_data_status,shift_period_status,shift_tx_slot_status,formal_phase_active,formal_phase_prepared,formal_gpio_pending,formal_gpio_pending_value,formal_gpio_pending_oe};
wire [29:0] gpio_phase_state = {shift_active_status,shift_bits_done_status,shift_msb_first_status,shift_tx_pin_status,shift_rx_pin_status,shift_tx_data_status,shift_rx_data_status,shift_tx_slot_status,formal_phase_active,formal_phase_prepared};
