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
  reg [31:0] PI_instruction;
  reg [7:0] PI_tx_payload;
  wire [0:0] PI_clk = clock;
  reg [7:0] PI_tx_payload_alt;
  reg [0:0] PI_rst_n;
  reg [7:0] PI_sampled_inputs;
  reg [0:0] PI_instruction_valid;
  reg [0:0] PI_ena;
  phase_properties UUT (
    .instruction(PI_instruction),
    .tx_payload(PI_tx_payload),
    .clk(PI_clk),
    .tx_payload_alt(PI_tx_payload_alt),
    .rst_n(PI_rst_n),
    .sampled_inputs(PI_sampled_inputs),
    .instruction_valid(PI_instruction_valid),
    .ena(PI_ena)
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
    // UUT.$auto$async2sync.\cc:107:execute$3141  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3147  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3183  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3207  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3219  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3249  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3255  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3273  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3309  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3321  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3339  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3345  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3369  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3375  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3393  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3399  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3405  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3411  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3429  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$3435  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3109  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3115  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3121  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3127  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3133  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3139  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3145  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3151  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3157  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3163  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3169  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3175  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3181  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3187  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3193  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3199  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3205  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3211  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3217  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3223  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3229  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3235  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3241  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3247  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3253  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3259  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3265  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3271  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3283  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3289  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3295  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3301  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3307  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3313  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3319  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3325  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3331  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3337  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3343  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3349  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3355  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3361  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3367  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3373  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3379  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3385  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3391  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3397  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3403  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3409  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3415  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3421  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3433  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$3439  = 1'b0;
    // UUT.$past$phase_properties.\sv:110$5$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:118$19$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:141$47$0  = 1'b1;
    // UUT.$past$phase_properties.\sv:156$64$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:165$73$0  = 1'b0;
    // UUT.$past$phase_properties.\sv:99$1$0  = 1'b1;
    UUT._witness_.anyinit_procdff_2977 = 1'b0;
    UUT._witness_.anyinit_procdff_2978 = 1'b0;
    UUT._witness_.anyinit_procdff_2979 = 110'b00111000000000001000000001011010100000100001000000010000010000000100101001000000001000000010000000000000001000;
    UUT._witness_.anyinit_procdff_2981 = 8'b01111111;
    UUT._witness_.anyinit_procdff_2982 = 8'b01001001;
    UUT._witness_.anyinit_procdff_2983 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2984 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2985 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2986 = 1'b0;
    UUT._witness_.anyinit_procdff_2987 = 8'b00000001;
    UUT._witness_.anyinit_procdff_2988 = 8'b00000001;
    UUT._witness_.anyinit_procdff_2989 = 8'b00010000;
    UUT._witness_.anyinit_procdff_2990 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2991 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2992 = 8'b00000000;
    UUT._witness_.anyinit_procdff_2993 = 1'b1;
    UUT._witness_.anyinit_procdff_2995 = 3'b000;
    UUT._witness_.anyinit_procdff_2996 = 3'b000;
    UUT._witness_.anyinit_procdff_2997 = 1'b0;
    UUT._witness_.anyinit_procdff_2998 = 3'b100;
    UUT._witness_.anyinit_procdff_2999 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3000 = 1'b0;
    UUT._witness_.anyinit_procdff_3001 = 5'b00000;
    UUT._witness_.anyinit_procdff_3002 = 5'b00010;
    UUT._witness_.anyinit_procdff_3003 = 8'b01000000;
    UUT._witness_.anyinit_procdff_3004 = 5'b00000;
    UUT._witness_.anyinit_procdff_3005 = 8'b00000100;
    UUT._witness_.anyinit_procdff_3006 = 5'b00000;
    UUT._witness_.anyinit_procdff_3007 = 5'b01001;
    UUT._witness_.anyinit_procdff_3008 = 1'b0;
    UUT._witness_.anyinit_procdff_3009 = 16'b0000000001000000;
    UUT._witness_.anyinit_procdff_3010 = 16'b0000000000000000;
    UUT._witness_.anyinit_procdff_3011 = 5'b00000;
    UUT._witness_.anyinit_procdff_3012 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3013 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3014 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3015 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3016 = 1'b0;
    UUT._witness_.anyinit_procdff_3017 = 16'b0000000100000000;
    UUT._witness_.anyinit_procdff_3018 = 5'b00000;
    UUT._witness_.anyinit_procdff_3019 = 16'b0000000001000000;
    UUT._witness_.anyinit_procdff_3020 = 87'b000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
    UUT._witness_.anyinit_procdff_3022 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3023 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3024 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3025 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3026 = 1'b1;
    UUT._witness_.anyinit_procdff_3027 = 3'b000;
    UUT._witness_.anyinit_procdff_3028 = 3'b110;
    UUT._witness_.anyinit_procdff_3029 = 1'b0;
    UUT._witness_.anyinit_procdff_3030 = 5'b00000;
    UUT._witness_.anyinit_procdff_3031 = 5'b00000;
    UUT._witness_.anyinit_procdff_3032 = 8'b00001000;
    UUT._witness_.anyinit_procdff_3033 = 5'b00111;
    UUT._witness_.anyinit_procdff_3034 = 8'b00010000;
    UUT._witness_.anyinit_procdff_3035 = 5'b00111;
    UUT._witness_.anyinit_procdff_3036 = 5'b00100;
    UUT._witness_.anyinit_procdff_3038 = 5'b00000;
    UUT._witness_.anyinit_procdff_3039 = 8'b00101101;
    UUT._witness_.anyinit_procdff_3040 = 8'b01000001;
    UUT._witness_.anyinit_procdff_3041 = 8'b00000001;
    UUT._witness_.anyinit_procdff_3042 = 1'b0;
    UUT._witness_.anyinit_procdff_3043 = 1'b0;
    UUT._witness_.anyinit_procdff_3044 = 3'b100;
    UUT._witness_.anyinit_procdff_3045 = 8'b00000000;
    UUT._witness_.anyinit_procdff_3047 = 1'b0;
    UUT._witness_.anyinit_procdff_3048 = 3'b000;
    UUT._witness_.anyinit_procdff_3049 = 3'b000;
    UUT._witness_.anyinit_procdff_3051 = 8'b00000000;
    UUT.dut.gpio_oe = 8'b01000001;
    UUT.dut.gpio_value = 8'b00101101;
    UUT.dut.loop_active = 1'b0;
    UUT.dut.loop_end = 5'b00000;
    UUT.dut.loop_remaining = 8'b00000100;
    UUT.dut.loop_start = 5'b00010;
    UUT.dut.pc = 5'b00111;
    UUT.dut.phase_active = 1'b0;
    UUT.dut.phase_prepared = 1'b0;
    UUT.dut.shift_active = 1'b0;
    UUT.dut.shift_bits_done = 3'b100;
    UUT.dut.shift_msb_first = 1'b1;
    UUT.dut.shift_period = 16'b0000000000000001;
    UUT.dut.shift_rx_data = 8'b00000001;
    UUT.dut.shift_rx_pin = 3'b010;
    UUT.dut.shift_tx_data = 8'b00000001;
    UUT.dut.shift_tx_pin = 3'b010;
    UUT.dut.shift_tx_slot = 1'b0;
    UUT.dut.state = 2'b00;
    UUT.dut.wait_is_input = 1'b0;
    UUT.dut.wait_left = 16'b0000000001000000;
    UUT.dut.wait_level = 1'b1;
    UUT.dut.wait_pin = 3'b000;
    UUT.dut.wait_timeout_skip = 1'b0;
    UUT.past_valid = 1'b1;

    // state 0
    PI_instruction = 32'b10110000000010001110100010000000;
    PI_tx_payload = 8'b10000001;
    PI_tx_payload_alt = 8'b00000000;
    PI_rst_n = 1'b1;
    PI_sampled_inputs = 8'b00000000;
    PI_instruction_valid = 1'b1;
    PI_ena = 1'b0;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      PI_instruction <= 32'b10111101000000000000000000000000;
      PI_tx_payload <= 8'b00010000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000010;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 2
    if (cycle == 1) begin
      PI_instruction <= 32'b00100000010010000000000000000000;
      PI_tx_payload <= 8'b00100000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b01000000;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 3
    if (cycle == 2) begin
      PI_instruction <= 32'b00110100100100000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00100000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000001;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 4
    if (cycle == 3) begin
      PI_instruction <= 32'b10100000010010000000000000000000;
      PI_tx_payload <= 8'b00100001;
      PI_tx_payload_alt <= 8'b00001000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00010000;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 5
    if (cycle == 4) begin
      PI_instruction <= 32'b01000000000000000000000000000010;
      PI_tx_payload <= 8'b00001000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000001;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 6
    if (cycle == 5) begin
      PI_instruction <= 32'b11001001000000000000000000000001;
      PI_tx_payload <= 8'b00100000;
      PI_tx_payload_alt <= 8'b00001000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000101;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 7
    if (cycle == 6) begin
      PI_instruction <= 32'b01000000000000000000000001000000;
      PI_tx_payload <= 8'b00001000;
      PI_tx_payload_alt <= 8'b00001000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00001111;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 8
    if (cycle == 7) begin
      PI_instruction <= 32'b00000000000000000000000000000000;
      PI_tx_payload <= 8'b00001000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000001;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 9
    if (cycle == 8) begin
      PI_instruction <= 32'b00100000000010000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b01000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00010011;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 10
    if (cycle == 9) begin
      PI_instruction <= 32'b00000000000000001000000000000000;
      PI_tx_payload <= 8'b00100000;
      PI_tx_payload_alt <= 8'b01000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00010001;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 11
    if (cycle == 10) begin
      PI_instruction <= 32'b10100001000010000000000000000000;
      PI_tx_payload <= 8'b00001010;
      PI_tx_payload_alt <= 8'b00100000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00010000;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 12
    if (cycle == 11) begin
      PI_instruction <= 32'b00000000000000000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00001000;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 13
    if (cycle == 12) begin
      PI_instruction <= 32'b11000000000000000000000001000000;
      PI_tx_payload <= 8'b01000000;
      PI_tx_payload_alt <= 8'b10000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b01100001;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 14
    if (cycle == 13) begin
      PI_instruction <= 32'b11000000000000000000000000000001;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00000010;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000001;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 15
    if (cycle == 14) begin
      PI_instruction <= 32'b11010000000000000000000001000000;
      PI_tx_payload <= 8'b10000000;
      PI_tx_payload_alt <= 8'b10000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000111;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 16
    if (cycle == 15) begin
      PI_instruction <= 32'b10101010011000000000000010000000;
      PI_tx_payload <= 8'b01000000;
      PI_tx_payload_alt <= 8'b01000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00100011;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 17
    if (cycle == 16) begin
      PI_instruction <= 32'b10111000110010000000000000000000;
      PI_tx_payload <= 8'b10000001;
      PI_tx_payload_alt <= 8'b11000010;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b10101101;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 18
    if (cycle == 17) begin
      PI_instruction <= 32'b10110010100011011100000000000000;
      PI_tx_payload <= 8'b00100000;
      PI_tx_payload_alt <= 8'b00100000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b01000000;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 19
    if (cycle == 18) begin
      PI_instruction <= 32'b10100010010010011001000000000000;
      PI_tx_payload <= 8'b00010000;
      PI_tx_payload_alt <= 8'b00010001;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00111010;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 20
    if (cycle == 19) begin
      PI_instruction <= 32'b01000000000000000000100000000000;
      PI_tx_payload <= 8'b00001000;
      PI_tx_payload_alt <= 8'b00001000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000101;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    // state 21
    if (cycle == 20) begin
      PI_instruction <= 32'b10111100111000100000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b11111111;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 22
    if (cycle == 21) begin
      PI_instruction <= 32'b10110100010010000000000000000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b11001010;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b0;
    end

    // state 23
    if (cycle == 22) begin
      PI_instruction <= 32'b11000000000000000000100000000000;
      PI_tx_payload <= 8'b00010000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b1;
      PI_sampled_inputs <= 8'b00000001;
      PI_instruction_valid <= 1'b1;
      PI_ena <= 1'b1;
    end

    // state 24
    if (cycle == 23) begin
      PI_instruction <= 32'b00001000000001111111111110000000;
      PI_tx_payload <= 8'b00000000;
      PI_tx_payload_alt <= 8'b00000000;
      PI_rst_n <= 1'b0;
      PI_sampled_inputs <= 8'b00000000;
      PI_instruction_valid <= 1'b0;
      PI_ena <= 1'b0;
    end

    genclock <= cycle < 24;
    cycle <= cycle + 1;
  end
endmodule
