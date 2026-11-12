module length_check(input [7:0] value, output equal);
assign equal = ((value >= 8'd1) && (value <= 8'd255)) == (value != 8'd0);
endmodule
