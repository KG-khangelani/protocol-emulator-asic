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
  public_scenario UUT (
    .clk(PI_clk)
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
    // UUT.$auto$async2sync.\cc:107:execute$5567  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5573  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5579  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5585  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5591  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5597  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5603  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5609  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5615  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$5565  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5571  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5577  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5583  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5589  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5595  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5601  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5619  = 1'b1;
    UUT.cycle = 7'b0000000;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5651  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5663  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5669  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5681  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5687  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5649  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5655  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5661  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5667  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5673  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5679  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5685  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5691  = 1'b1;
    // UUT.dut.$past$integration_properties.\vh:79$128$0  = 1'b0;
    // UUT.dut.$past$integration_properties.\vh:82$129$0  = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5104 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5105 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5106 = 4'b1000;
    UUT.dut._witness_.anyinit_procdff_5107 = 4'b1000;
    UUT.dut._witness_.anyinit_procdff_5108 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5109 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5110 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5111 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5112 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5113 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5114 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5115 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5116 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5117 = 8'b00000000;
    UUT.dut._witness_.anyinit_procdff_5118 = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5195  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5201  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5243  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5249  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5285  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5309  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5321  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5351  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5369  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5405  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5411  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5423  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5435  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5477  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5501  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5507  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5513  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5519  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5537  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5555  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5199  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5205  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5211  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5217  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5223  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5229  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5235  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5241  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5247  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5253  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5265  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5271  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5277  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5283  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5289  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5295  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5301  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5307  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5313  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5319  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5325  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5331  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5337  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5343  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5349  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5355  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5361  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5367  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5373  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5379  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5385  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5391  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5397  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5403  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5409  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5415  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5421  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5427  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5433  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5439  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5445  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5451  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5457  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5463  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5469  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5475  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5481  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5487  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5493  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5499  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5505  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5511  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5517  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5523  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5529  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5535  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5541  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5547  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5553  = 1'b1;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:136$384$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:147$388$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:155$402$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:178$430$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:193$447$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:206$460$0  = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5014 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5015 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5016 = 110'b00000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5018 = 8'b00101001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5019 = 8'b00101001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5020 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5021 = 8'b10000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5022 = 8'b10100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5023 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5024 = 8'b00000100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5025 = 8'b01111100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5026 = 8'b00000011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5027 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5028 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5029 = 8'b00010000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5030 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5032 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5033 = 3'b001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5034 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5035 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5036 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5037 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5038 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5039 = 5'b00011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5040 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5041 = 5'b00000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5042 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5043 = 5'b00100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5044 = 5'b01100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5045 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5046 = 16'b0000000000000011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5047 = 16'b0000010000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5048 = 5'b00001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5049 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5050 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5051 = 8'b00100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5052 = 8'b10000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5053 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5054 = 16'b0000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5055 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5056 = 16'b0000100000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5057 = 87'b000000000000000000000000000000000000000000000000000000000000000000000000000010000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5059 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5060 = 8'b00000100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5061 = 8'b01000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5062 = 8'b00000010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5063 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5064 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5065 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5066 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5067 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5068 = 5'b00011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5069 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5070 = 5'b00001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5071 = 8'b01000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5072 = 5'b00001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5073 = 5'b11011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5075 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5076 = 8'b00001000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5077 = 8'b00000010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5078 = 8'b00001000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5079 = 8'b00001000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5080 = 3'b100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5081 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5082 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5083 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5084 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5085 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5086 = 8'b00010000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5088 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5089 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5090 = 3'b100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5091 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5093 = 8'b01000000;
    UUT.dut.actual_engine_observer.past_valid = 1'b0;
    UUT.dut.data_store.rx_result = 8'b00000000;
    UUT.dut.data_store.rx_valid = 1'b1;
    UUT.dut.data_store.tx_payload = 8'b10000100;
    UUT.dut.data_store.tx_payload_alt = 8'b00000010;
    UUT.dut.engine.gpio_oe = 8'b00000000;
    UUT.dut.engine.gpio_value = 8'b00000000;
    UUT.dut.engine.loop_active = 1'b0;
    UUT.dut.engine.loop_end = 5'b00000;
    UUT.dut.engine.loop_remaining = 8'b00000000;
    UUT.dut.engine.loop_start = 5'b00000;
    UUT.dut.engine.pc = 5'b00000;
    UUT.dut.engine.phase_active = 1'b0;
    UUT.dut.engine.phase_prepared = 1'b0;
    UUT.dut.engine.shift_active = 1'b0;
    UUT.dut.engine.shift_bits_done = 3'b000;
    UUT.dut.engine.shift_msb_first = 1'b0;
    UUT.dut.engine.shift_period = 16'b0000000000000000;
    UUT.dut.engine.shift_rx_data = 8'b00000000;
    UUT.dut.engine.shift_rx_pin = 3'b000;
    UUT.dut.engine.shift_tx_data = 8'b00000000;
    UUT.dut.engine.shift_tx_pin = 3'b000;
    UUT.dut.engine.shift_tx_slot = 1'b0;
    UUT.dut.engine.state = 2'b00;
    UUT.dut.engine.wait_is_input = 1'b0;
    UUT.dut.engine.wait_left = 16'b0000000000000000;
    UUT.dut.engine.wait_level = 1'b0;
    UUT.dut.engine.wait_pin = 3'b000;
    UUT.dut.engine.wait_timeout_skip = 1'b0;
    UUT.dut.input_sync.metastability_stage = 8'b00000000;
    UUT.dut.input_sync.sampled_in = 8'b00000001;
    UUT.dut.integration_past_valid = 1'b0;
    UUT.dut.reference_alt = 8'b00000000;
    UUT.dut.reference_rx = 8'b00000000;
    UUT.dut.reference_sync0 = 8'b00000000;
    UUT.dut.reference_sync1 = 8'b00000000;
    UUT.dut.reference_tx = 8'b00000010;
    UUT.dut.reference_valid = 1'b0;
    UUT.dut.store.program_length = 4'b0000;
    UUT.dut.store.program_ready = 1'b0;
    UUT.dut.store.word0 = 32'b00001000100000000000000000000000;
    UUT.dut.store.word1 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word2 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word3 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word4 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word5 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word6 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word7 = 32'b00000000000000000000000000001000;
    UUT.dut.watched_byte = 8'b00001000;
    UUT.past_valid = 1'b0;
    UUT.msb_first = 1'b1;
    UUT.tx_byte = 8'b00000010;
    UUT.rx_byte = 8'b00000100;
    UUT.dut.watched_address = 5'b00000;

    // state 0
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
    end

    // state 2
    if (cycle == 1) begin
    end

    // state 3
    if (cycle == 2) begin
    end

    // state 4
    if (cycle == 3) begin
    end

    // state 5
    if (cycle == 4) begin
    end

    // state 6
    if (cycle == 5) begin
    end

    // state 7
    if (cycle == 6) begin
    end

    // state 8
    if (cycle == 7) begin
    end

    // state 9
    if (cycle == 8) begin
    end

    // state 10
    if (cycle == 9) begin
    end

    // state 11
    if (cycle == 10) begin
    end

    // state 12
    if (cycle == 11) begin
    end

    // state 13
    if (cycle == 12) begin
    end

    // state 14
    if (cycle == 13) begin
    end

    // state 15
    if (cycle == 14) begin
    end

    // state 16
    if (cycle == 15) begin
    end

    // state 17
    if (cycle == 16) begin
    end

    // state 18
    if (cycle == 17) begin
    end

    // state 19
    if (cycle == 18) begin
    end

    // state 20
    if (cycle == 19) begin
    end

    // state 21
    if (cycle == 20) begin
    end

    // state 22
    if (cycle == 21) begin
    end

    // state 23
    if (cycle == 22) begin
    end

    // state 24
    if (cycle == 23) begin
    end

    // state 25
    if (cycle == 24) begin
    end

    // state 26
    if (cycle == 25) begin
    end

    // state 27
    if (cycle == 26) begin
    end

    // state 28
    if (cycle == 27) begin
    end

    // state 29
    if (cycle == 28) begin
    end

    // state 30
    if (cycle == 29) begin
    end

    // state 31
    if (cycle == 30) begin
    end

    // state 32
    if (cycle == 31) begin
    end

    // state 33
    if (cycle == 32) begin
    end

    // state 34
    if (cycle == 33) begin
    end

    // state 35
    if (cycle == 34) begin
    end

    // state 36
    if (cycle == 35) begin
    end

    // state 37
    if (cycle == 36) begin
    end

    // state 38
    if (cycle == 37) begin
    end

    // state 39
    if (cycle == 38) begin
    end

    // state 40
    if (cycle == 39) begin
    end

    // state 41
    if (cycle == 40) begin
    end

    // state 42
    if (cycle == 41) begin
    end

    // state 43
    if (cycle == 42) begin
    end

    // state 44
    if (cycle == 43) begin
    end

    // state 45
    if (cycle == 44) begin
    end

    // state 46
    if (cycle == 45) begin
    end

    // state 47
    if (cycle == 46) begin
    end

    // state 48
    if (cycle == 47) begin
    end

    // state 49
    if (cycle == 48) begin
    end

    // state 50
    if (cycle == 49) begin
    end

    // state 51
    if (cycle == 50) begin
    end

    // state 52
    if (cycle == 51) begin
    end

    // state 53
    if (cycle == 52) begin
    end

    // state 54
    if (cycle == 53) begin
    end

    // state 55
    if (cycle == 54) begin
    end

    // state 56
    if (cycle == 55) begin
    end

    // state 57
    if (cycle == 56) begin
    end

    // state 58
    if (cycle == 57) begin
    end

    // state 59
    if (cycle == 58) begin
    end

    // state 60
    if (cycle == 59) begin
    end

    // state 61
    if (cycle == 60) begin
    end

    // state 62
    if (cycle == 61) begin
    end

    genclock <= cycle < 62;
    cycle <= cycle + 1;
  end
endmodule
