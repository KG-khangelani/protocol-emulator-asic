`timescale 1ns / 1ps
module sim; reg clk=0; public_spi dut(clk); initial begin repeat(445) begin #10 clk=1; #10 clk=0; end $display("PREFLIGHT_COMPLETE"); $finish; end endmodule
