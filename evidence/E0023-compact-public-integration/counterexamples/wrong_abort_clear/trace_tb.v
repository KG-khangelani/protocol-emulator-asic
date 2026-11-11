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
    // UUT.$auto$async2sync.\cc:107:execute$5574  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5580  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5586  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5592  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5598  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5604  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5610  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5616  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5622  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$5628  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$5572  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5578  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5584  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5590  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5596  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5602  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5608  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$5626  = 1'b1;
    UUT.cycle = 7'b0000000;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5664  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5676  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5682  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5694  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:107:execute$5700  = 1'b0;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5662  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5668  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5674  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5680  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5686  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5692  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5698  = 1'b1;
    // UUT.dut.$auto$async2sync.\cc:116:execute$5704  = 1'b1;
    // UUT.dut.$past$integration_properties.\vh:79$131$0  = 1'b0;
    // UUT.dut.$past$integration_properties.\vh:82$132$0  = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5111 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5112 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5113 = 4'b1000;
    UUT.dut._witness_.anyinit_procdff_5114 = 4'b0000;
    UUT.dut._witness_.anyinit_procdff_5115 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5116 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5117 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5118 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5119 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5120 = 1'b1;
    UUT.dut._witness_.anyinit_procdff_5121 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5122 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5123 = 1'b0;
    UUT.dut._witness_.anyinit_procdff_5124 = 8'b00000000;
    UUT.dut._witness_.anyinit_procdff_5125 = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5202  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5208  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5250  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5256  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5292  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5316  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5328  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5358  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5376  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5412  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5418  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5430  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5442  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5484  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5508  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5514  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5520  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5526  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5544  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:107:execute$5562  = 1'b0;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5206  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5212  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5218  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5224  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5230  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5236  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5242  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5248  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5254  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5260  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5272  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5278  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5284  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5290  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5296  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5302  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5308  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5314  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5320  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5326  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5332  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5338  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5344  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5350  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5356  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5362  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5368  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5374  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5380  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5386  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5392  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5398  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5404  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5410  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5416  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5422  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5428  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5434  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5440  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5446  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5452  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5458  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5464  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5470  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5476  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5482  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5488  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5494  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5500  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5506  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5512  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5518  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5524  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5530  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5536  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5542  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5548  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5554  = 1'b1;
    // UUT.dut.actual_engine_observer.$auto$async2sync.\cc:116:execute$5560  = 1'b1;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:136$387$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:147$391$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:155$405$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:178$433$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:193$450$0  = 1'b0;
    // UUT.dut.actual_engine_observer.$past$phase_observer.\sv:206$463$0  = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5021 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5022 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5023 = 110'b00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5025 = 8'b01111011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5026 = 8'b00010000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5027 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5028 = 8'b10100001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5029 = 8'b10100001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5030 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5031 = 8'b01000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5032 = 8'b00110111;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5033 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5034 = 8'b00001000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5035 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5036 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5037 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5039 = 3'b100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5040 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5041 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5042 = 3'b010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5043 = 8'b00100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5044 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5045 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5046 = 5'b00011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5047 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5048 = 5'b01000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5049 = 8'b00100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5050 = 5'b10000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5051 = 5'b01101;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5052 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5053 = 16'b0000000000000011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5054 = 16'b0000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5055 = 5'b10000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5056 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5057 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5058 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5059 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5060 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5061 = 16'b0000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5062 = 5'b00000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5063 = 16'b0000001000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5064 = 87'b000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5066 = 8'b00100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5067 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5068 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5069 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5070 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5071 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5072 = 3'b001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5073 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5074 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5075 = 5'b00011;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5076 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5077 = 5'b00000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5078 = 8'b00000010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5079 = 5'b00010;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5080 = 5'b10101;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5082 = 5'b00001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5083 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5084 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5085 = 8'b00100000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5086 = 8'b00000000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5087 = 3'b001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5088 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5089 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5090 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5091 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5092 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5093 = 8'b00000100;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5095 = 1'b0;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5096 = 1'b1;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5097 = 3'b001;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5098 = 3'b000;
    UUT.dut.actual_engine_observer._witness_.anyinit_procdff_5100 = 8'b00000000;
    UUT.dut.actual_engine_observer.past_valid = 1'b0;
    UUT.dut.data_store.rx_result = 8'b00010000;
    UUT.dut.data_store.rx_valid = 1'b1;
    UUT.dut.data_store.tx_payload = 8'b00001000;
    UUT.dut.data_store.tx_payload_alt = 8'b00000010;
    UUT.dut.engine.gpio_oe = 8'b01000000;
    UUT.dut.engine.gpio_value = 8'b00110100;
    UUT.dut.engine.loop_active = 1'b0;
    UUT.dut.engine.loop_end = 5'b00000;
    UUT.dut.engine.loop_remaining = 8'b00000000;
    UUT.dut.engine.loop_start = 5'b01000;
    UUT.dut.engine.pc = 5'b00000;
    UUT.dut.engine.phase_active = 1'b1;
    UUT.dut.engine.phase_prepared = 1'b0;
    UUT.dut.engine.shift_active = 1'b0;
    UUT.dut.engine.shift_bits_done = 3'b000;
    UUT.dut.engine.shift_msb_first = 1'b0;
    UUT.dut.engine.shift_period = 16'b0000001000000000;
    UUT.dut.engine.shift_rx_data = 8'b00000000;
    UUT.dut.engine.shift_rx_pin = 3'b010;
    UUT.dut.engine.shift_tx_data = 8'b00100000;
    UUT.dut.engine.shift_tx_pin = 3'b000;
    UUT.dut.engine.shift_tx_slot = 1'b0;
    UUT.dut.engine.state = 2'b00;
    UUT.dut.engine.wait_is_input = 1'b0;
    UUT.dut.engine.wait_left = 16'b0000000000000000;
    UUT.dut.engine.wait_level = 1'b0;
    UUT.dut.engine.wait_pin = 3'b000;
    UUT.dut.engine.wait_timeout_skip = 1'b0;
    UUT.dut.input_sync.metastability_stage = 8'b00000000;
    UUT.dut.input_sync.sampled_in = 8'b00000000;
    UUT.dut.integration_past_valid = 1'b0;
    UUT.dut.reference_alt = 8'b00000000;
    UUT.dut.reference_rx = 8'b00000000;
    UUT.dut.reference_sync0 = 8'b00000000;
    UUT.dut.reference_sync1 = 8'b00000000;
    UUT.dut.reference_tx = 8'b01000000;
    UUT.dut.reference_valid = 1'b0;
    UUT.dut.store.program_length = 4'b0101;
    UUT.dut.store.program_ready = 1'b1;
    UUT.dut.store.word0 = 32'b00001000100000000000101000000000;
    UUT.dut.store.word1 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word2 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word3 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word4 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word5 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word6 = 32'b00000000000000000000000000000000;
    UUT.dut.store.word7 = 32'b00000000000000000000000011010110;
    UUT.dut.watched_byte = 8'b00001000;
    UUT.past_valid = 1'b0;
    UUT.msb_first = 1'b0;
    UUT.tx_byte = 8'b01000000;
    UUT.rx_byte = 8'b00000000;
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

    // state 63
    if (cycle == 62) begin
    end

    // state 64
    if (cycle == 63) begin
    end

    // state 65
    if (cycle == 64) begin
    end

    // state 66
    if (cycle == 65) begin
    end

    // state 67
    if (cycle == 66) begin
    end

    genclock <= cycle < 67;
    cycle <= cycle + 1;
  end
endmodule
