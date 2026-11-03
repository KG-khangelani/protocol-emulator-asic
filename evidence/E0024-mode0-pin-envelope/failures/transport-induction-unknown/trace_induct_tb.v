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
  transport UUT (
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
    // UUT.$auto$async2sync.\cc:107:execute$275  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$281  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$287  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$293  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$299  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$305  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$311  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$317  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$323  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$329  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$335  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$279  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$285  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$291  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$297  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$303  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$309  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$315  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$321  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$327  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$333  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$339  = 1'b0;
    UUT._witness_.anyinit_procdff_268 = 1'b0;
    UUT._witness_.anyinit_procdff_269 = 1'b0;
    UUT._witness_.anyinit_procdff_270 = 1'b0;
    UUT._witness_.anyinit_procdff_271 = 1'b0;
    UUT._witness_.anyinit_procdff_272 = 8'b00000000;
    UUT._witness_.anyinit_procdff_273 = 8'b00000000;
    UUT.actual_sync.metastability_stage = 8'b00001000;
    UUT.actual_sync.sampled_in = 8'b00000010;
    UUT.cycle = 9'b101110101;
    UUT.observed = 8'b00011110;
    UUT.past2_valid = 1'b0;
    UUT.past_valid = 1'b0;
    UUT.msb_first = 1'b0;
    UUT.rx_byte = 8'b10100001;

    // state 0
    UUT.raw_miso = 1'b1;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 2
    if (cycle == 1) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 3
    if (cycle == 2) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 4
    if (cycle == 3) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 5
    if (cycle == 4) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 6
    if (cycle == 5) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 7
    if (cycle == 6) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 8
    if (cycle == 7) begin
      UUT.raw_miso <= 1'b0;
    end

    genclock <= cycle < 8;
    cycle <= cycle + 1;
  end
endmodule
