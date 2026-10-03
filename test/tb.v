// Modified 2026-10-02: instantiate the M1 top and a directly driven engine.
`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Normal regression uses compact FST. The learning target requests readable
  // VCD so a source-controlled walkthrough can explain selected clock edges.
  initial begin
`ifdef LEARNING_VCD
    $dumpfile("../build/m0-learning.vcd");
`else
    $dumpfile("tb.fst");
`endif
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

`ifndef GL_TEST
`ifndef M0_LEARNING
  reg [31:0] engine_instruction;
  reg engine_instruction_valid;
  reg [7:0] engine_sampled_inputs;
  wire [4:0] engine_pc;
  wire [1:0] engine_state;
  wire [15:0] engine_wait_left;
  wire [7:0] engine_gpio_value;
  wire [7:0] engine_gpio_oe;
  wire engine_wait_is_input_status;
  wire [2:0] engine_wait_pin_status;
  wire engine_wait_level_status;
  wire engine_wait_timeout_skip_status;
`endif
`endif

  // Replace tt_um_khangelani_protocol_emulator with your module name:
  tt_um_khangelani_protocol_emulator user_project (
      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

`ifndef GL_TEST
`ifndef M0_LEARNING
  m1_engine directly_driven_engine (
      .clk(clk),
      .rst_n(rst_n),
      .ena(ena),
      .instruction(engine_instruction),
      .instruction_valid(engine_instruction_valid),
      .sampled_inputs(engine_sampled_inputs),
      .pc(engine_pc),
      .state(engine_state),
      .wait_left(engine_wait_left),
    .gpio_value(engine_gpio_value),
    .gpio_oe(engine_gpio_oe),
    .wait_is_input_status(engine_wait_is_input_status),
    .wait_pin_status(engine_wait_pin_status),
    .wait_level_status(engine_wait_level_status),
    .wait_timeout_skip_status(engine_wait_timeout_skip_status)
  );
`endif
`endif

endmodule
