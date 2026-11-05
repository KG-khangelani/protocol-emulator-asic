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
    // UUT.$auto$async2sync.\cc:107:execute$331  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$337  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$343  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$349  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$355  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$361  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$367  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$373  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$379  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$385  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$391  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$397  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$403  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$409  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$415  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$421  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$427  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$433  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$439  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$335  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$341  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$347  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$353  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$359  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$365  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$371  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$377  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$383  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$389  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$395  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$401  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$407  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$413  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$419  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$425  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$431  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$437  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$443  = 1'b1;
    UUT._witness_.anyinit_procdff_324 = 1'b1;
    UUT._witness_.anyinit_procdff_325 = 1'b1;
    UUT._witness_.anyinit_procdff_326 = 1'b0;
    UUT._witness_.anyinit_procdff_327 = 1'b1;
    UUT._witness_.anyinit_procdff_328 = 8'b00000001;
    UUT._witness_.anyinit_procdff_329 = 8'b00000000;
    UUT.actual_sync.metastability_stage = 8'b00000000;
    UUT.actual_sync.sampled_in = 8'b00000011;
    UUT.cycle = 9'b000000000;
    UUT.observed = 8'b00000000;
    UUT.past2_valid = 1'b0;
    UUT.past_valid = 1'b0;
    UUT.msb_first = 1'b0;
    UUT.rx_byte = 8'b11111111;

    // state 0
    UUT.raw_miso = 1'b1;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 2
    if (cycle == 1) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 3
    if (cycle == 2) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 4
    if (cycle == 3) begin
      UUT.raw_miso <= 1'b0;
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

    // state 9
    if (cycle == 8) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 10
    if (cycle == 9) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 11
    if (cycle == 10) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 12
    if (cycle == 11) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 13
    if (cycle == 12) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 14
    if (cycle == 13) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 15
    if (cycle == 14) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 16
    if (cycle == 15) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 17
    if (cycle == 16) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 18
    if (cycle == 17) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 19
    if (cycle == 18) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 20
    if (cycle == 19) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 21
    if (cycle == 20) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 22
    if (cycle == 21) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 23
    if (cycle == 22) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 24
    if (cycle == 23) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 25
    if (cycle == 24) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 26
    if (cycle == 25) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 27
    if (cycle == 26) begin
      UUT.raw_miso <= 1'b1;
    end

    // state 28
    if (cycle == 27) begin
      UUT.raw_miso <= 1'b0;
    end

    // state 29
    if (cycle == 28) begin
      UUT.raw_miso <= 1'b0;
    end

    genclock <= cycle < 29;
    cycle <= cycle + 1;
  end
endmodule
