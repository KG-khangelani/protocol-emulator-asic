`ifndef VERILATOR
module testbench;
  reg [4095:0] vcdfile;
  reg clock;
`else
module testbench(input clock, output reg genclock);
  initial genclock = 1;
`endif
  reg genclock = 1;
  reg [31:0] cycle = 0;
  wire [0:0] PI_clk = clock;
  reg [0:0] PI_ena;
  reg [7:0] PI_tx_payload_alt;
  reg [7:0] PI_sampled_inputs;
  reg [31:0] PI_instruction;
  reg [7:0] PI_tx_payload;
  reg [0:0] PI_instruction_valid;
  reg [0:0] PI_rst_n;
  phase_properties UUT (
    .clk(PI_clk),
    .ena(PI_ena),
    .tx_payload_alt(PI_tx_payload_alt),
    .sampled_inputs(PI_sampled_inputs),
    .instruction(PI_instruction),
    .tx_payload(PI_tx_payload),
    .instruction_valid(PI_instruction_valid),
    .rst_n(PI_rst_n)
  );
`ifndef VERILATOR
  initial begin
    if ($value$plusargs("vcd=%s", vcdfile)) begin
      $dumpfile(vcdfile);
      $dumpvars(0, testbench);
    end
    #5 clock = 0;
    while (genclock) begin
      #5 clock = 0;
      #5 clock = 1;
    end
  end
`endif
  initial begin
`ifndef VERILATOR
    #1;
`endif
    // UUT.$auto$async2sync.\cc:107:execute$3242  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3248  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3284  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3308  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3320  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3350  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3362  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3374  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3410  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3416  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3446  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3470  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3500  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3506  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3524  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3530  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3536  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3542  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3560  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3566  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3210  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3216  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3222  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3228  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3234  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3240  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3246  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3252  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3258  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3264  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3270  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3276  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3282  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3288  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3294  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3300  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3306  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3312  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3318  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3324  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3330  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3336  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3342  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3348  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3354  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3360  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3366  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3372  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3384  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3390  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3396  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3402  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3408  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3414  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3420  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3426  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3432  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3438  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3444  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3450  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3456  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3462  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3468  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3474  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3480  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3486  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3492  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3498  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3504  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3510  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3516  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3522  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3528  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3534  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3540  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3546  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3552  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3564  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$3570  = 1'b1;
    // UUT.$past$phase_properties.\sv:103$1$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:114$5$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:122$19$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:145$47$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:160$64$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:173$77$0  = 1'b0;
    UUT._witness_.anyinit_procdff_3073 = 1'b1;
    UUT._witness_.anyinit_procdff_3074 = 1'b0;
    UUT._witness_.anyinit_procdff_3075 = 110'b00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
    UUT._witness_.anyinit_procdff_3077 = 8'b00100111;
    UUT._witness_.anyinit_procdff_3078 = 8'b00000100;
    UUT._witness_.anyinit_procdff_3079 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3080 = 8'b00000001;
    UUT._witness_.anyinit_procdff_3081 = 8'b00000001;
    UUT._witness_.anyinit_procdff_3082 = 1'b0;
    UUT._witness_.anyinit_procdff_3083 = 8'b00000001;
    UUT._witness_.anyinit_procdff_3084 = 8'b00000001;
    UUT._witness_.anyinit_procdff_3085 = 8'b00100000;
    UUT._witness_.anyinit_procdff_3086 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3087 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3088 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3089 = 1'b1;
    UUT._witness_.anyinit_procdff_3091 = 3'b000;
    UUT._witness_.anyinit_procdff_3092 = 3'b100;
    UUT._witness_.anyinit_procdff_3093 = 1'b0;
    UUT._witness_.anyinit_procdff_3094 = 3'b010;
    UUT._witness_.anyinit_procdff_3095 = 8'b00010000;
    UUT._witness_.anyinit_procdff_3096 = 1'b0;
    UUT._witness_.anyinit_procdff_3097 = 5'b00000;
    UUT._witness_.anyinit_procdff_3098 = 5'b00000;
    UUT._witness_.anyinit_procdff_3099 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3100 = 5'b10000;
    UUT._witness_.anyinit_procdff_3101 = 8'b10000000;
    UUT._witness_.anyinit_procdff_3102 = 5'b00010;
    UUT._witness_.anyinit_procdff_3103 = 5'b01111;
    UUT._witness_.anyinit_procdff_3104 = 1'b0;
    UUT._witness_.anyinit_procdff_3105 = 16'b0000000000000000;
    UUT._witness_.anyinit_procdff_3106 = 16'b0000000000000000;
    UUT._witness_.anyinit_procdff_3107 = 5'b00010;
    UUT._witness_.anyinit_procdff_3108 = 8'b11000000;
    UUT._witness_.anyinit_procdff_3109 = 8'b01000000;
    UUT._witness_.anyinit_procdff_3110 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3111 = 8'b00000010;
    UUT._witness_.anyinit_procdff_3112 = 1'b0;
    UUT._witness_.anyinit_procdff_3113 = 16'b0000000000000000;
    UUT._witness_.anyinit_procdff_3114 = 5'b00001;
    UUT._witness_.anyinit_procdff_3115 = 16'b0010000000000000;
    UUT._witness_.anyinit_procdff_3116 = 87'b000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
    UUT._witness_.anyinit_procdff_3118 = 8'b00001000;
    UUT._witness_.anyinit_procdff_3119 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3120 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3121 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3122 = 1'b0;
    UUT._witness_.anyinit_procdff_3123 = 3'b000;
    UUT._witness_.anyinit_procdff_3124 = 3'b011;
    UUT._witness_.anyinit_procdff_3125 = 1'b0;
    UUT._witness_.anyinit_procdff_3126 = 5'b00000;
    UUT._witness_.anyinit_procdff_3127 = 5'b00000;
    UUT._witness_.anyinit_procdff_3128 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3129 = 5'b10000;
    UUT._witness_.anyinit_procdff_3130 = 8'b00011000;
    UUT._witness_.anyinit_procdff_3131 = 5'b10000;
    UUT._witness_.anyinit_procdff_3132 = 5'b00010;
    UUT._witness_.anyinit_procdff_3134 = 5'b00010;
    UUT._witness_.anyinit_procdff_3135 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3136 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3137 = 8'b00000100;
    UUT._witness_.anyinit_procdff_3138 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3139 = 3'b100;
    UUT._witness_.anyinit_procdff_3140 = 1'b0;
    UUT._witness_.anyinit_procdff_3141 = 1'b0;
    UUT._witness_.anyinit_procdff_3142 = 1'b1;
    UUT._witness_.anyinit_procdff_3143 = 1'b0;
    UUT._witness_.anyinit_procdff_3144 = 3'b000;
    UUT._witness_.anyinit_procdff_3145 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3147 = 1'b1;
    UUT._witness_.anyinit_procdff_3148 = 1'b0;
    UUT._witness_.anyinit_procdff_3149 = 3'b000;
    UUT._witness_.anyinit_procdff_3150 = 3'b000;
    UUT._witness_.anyinit_procdff_3152 = 8'b00000000;
    UUT.dut.gpio_oe = 8'b01000000;
    UUT.dut.gpio_value = 8'b11000000;
    UUT.dut.loop_active = 1'b0;
    UUT.dut.loop_end = 5'b01000;
    UUT.dut.loop_remaining = 8'b00000000;
    UUT.dut.loop_start = 5'b10000;
    UUT.dut.pc = 5'b00000;
    UUT.dut.phase_active = 1'b1;
    UUT.dut.phase_prepared = 1'b1;
    UUT.dut.shift_active = 1'b0;
    UUT.dut.shift_bits_done = 3'b000;
    UUT.dut.shift_msb_first = 1'b0;
    UUT.dut.shift_period = 16'b0000000000000000;
    UUT.dut.shift_rx_data = 8'b00000000;
    UUT.dut.shift_rx_pin = 3'b000;
    UUT.dut.shift_tx_data = 8'b00001000;
    UUT.dut.shift_tx_pin = 3'b010;
    UUT.dut.shift_tx_slot = 1'b0;
    UUT.dut.state = 2'b00;
    UUT.dut.wait_is_input = 1'b0;
    UUT.dut.wait_left = 16'b0000100000000000;
    UUT.dut.wait_level = 1'b0;
    UUT.dut.wait_pin = 3'b000;
    UUT.dut.wait_timeout_skip = 1'b0;
    UUT.past_valid = 1'b0;

    // state 0
    PI_ena = 1'b0;
    PI_tx_payload_alt = 8'b00000000;
    PI_sampled_inputs = 8'b00000000;
    PI_instruction = 32'b00000000110000000100110000001000;
    PI_tx_payload = 8'b00000000;
    PI_instruction_valid = 1'b0;
    PI_rst_n = 1'b0;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b00010001;
      PI_instruction <= 32'b10100010000010101000000000000000;
      PI_tx_payload <= 8'b10100110;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 2
    if (cycle == 1) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b00110000;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 3
    if (cycle == 2) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000010;
      PI_sampled_inputs <= 8'b00110101;
      PI_instruction <= 32'b10100010000010000000000000000000;
      PI_tx_payload <= 8'b00000101;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 4
    if (cycle == 3) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000100;
      PI_sampled_inputs <= 8'b00000101;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00101001;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 5
    if (cycle == 4) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b10010101;
      PI_sampled_inputs <= 8'b00001001;
      PI_instruction <= 32'b10100010000010000000000000000000;
      PI_tx_payload <= 8'b00101000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 6
    if (cycle == 5) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b01010101;
      PI_sampled_inputs <= 8'b01111110;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 7
    if (cycle == 6) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b01000000;
      PI_sampled_inputs <= 8'b00110100;
      PI_instruction <= 32'b10100010000010000000000000001000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 8
    if (cycle == 7) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000010;
      PI_sampled_inputs <= 8'b01110010;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 9
    if (cycle == 8) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000010;
      PI_sampled_inputs <= 8'b00010101;
      PI_instruction <= 32'b10100010000010001000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 10
    if (cycle == 9) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b00000010;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 11
    if (cycle == 10) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b11010010;
      PI_instruction <= 32'b10100010000010000000000100000000;
      PI_tx_payload <= 8'b10000001;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 12
    if (cycle == 11) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b00010010;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000110;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 13
    if (cycle == 12) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000010;
      PI_sampled_inputs <= 8'b01000010;
      PI_instruction <= 32'b10100010000010000000000100000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    // state 14
    if (cycle == 13) begin
      PI_ena <= 1'b1;
      PI_tx_payload_alt <= 8'b00000000;
      PI_sampled_inputs <= 8'b00000000;
      PI_instruction <= 32'b10100010000100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_instruction_valid <= 1'b1;
      PI_rst_n <= 1'b1;
    end

    genclock <= cycle < 14;
    cycle <= cycle + 1;
  end
endmodule
