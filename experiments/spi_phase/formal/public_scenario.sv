/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module public_scenario(input wire clk);
    (* anyconst *) reg [7:0] tx_byte, rx_byte;
    (* anyconst *) reg msb_first;
    (* anyconst *) reg [5:0] abort_edge;
    (* anyconst *) reg [1:0] abort_kind;
    (* anyconst *) reg abort_enable;
    reg [6:0] cycle = 7'd0;
    reg past_valid = 1'b0;
    reg rst_n, ena;
    reg [7:0] ui_in, uio_in;
    wire [7:0] uo_out, uio_out, uio_oe;
    wire [6:0] exec_edge = cycle - 7'd20;
    wire [6:0] bit_index_wide = exec_edge < 7'd2 ? 7'd0 : (exec_edge - 7'd2) / 7'd5;
    wire [2:0] bit_index = bit_index_wide > 7'd7 ? 3'd7 : bit_index_wide[2:0];
    wire serial_bit = msb_first ? rx_byte[3'd7-bit_index] : rx_byte[bit_index];
    wire [6:0] previous_exec_edge = cycle - 7'd21;
    wire [6:0] previous_bit_wide = previous_exec_edge < 7'd2 ? 7'd0 : (previous_exec_edge-7'd2)/7'd5;
    wire [2:0] previous_bit = previous_bit_wide > 7'd7 ? 3'd7 : previous_bit_wide[2:0];
    wire expected_tx = msb_first ? tx_byte[3'd7-previous_bit] : tx_byte[previous_bit];
    wire [31:0] drive_word = 32'ha0480000 | (msb_first ? 32'h10000000 : 32'd0);
    wire [31:0] sample_word = 32'ha0500018 | (msb_first ? 32'h10000000 : 32'd0);
    reg [31:0] load_word;
    wire [6:0] write_index = cycle - 7'd1;
    always @(*) begin
        case (write_index[3:2])
            2'd0: load_word = 32'h62000008;
            2'd1: load_word = drive_word;
            2'd2: load_word = sample_word;
            default: load_word = 32'h80000000;
        endcase
        rst_n = 1'b1; ena = 1'b0; ui_in = 8'd0; uio_in = 8'd0;
        if (cycle == 7'd0 || cycle >= 7'd70) rst_n = 1'b0;
        else if (cycle <= 7'd16) begin
            ena = 1'b1; ui_in = 8'hc0 | {3'd0,write_index[4:0]};
            uio_in = load_word[8*write_index[1:0] +: 8];
        end else if (cycle == 7'd17) begin
            ena = 1'b1; ui_in = 8'he0; uio_in = 8'd4;
        end else if (cycle == 7'd18) begin
            ena = 1'b1; ui_in = 8'he1; uio_in = tx_byte;
        end else if (cycle <= 7'd20) uio_in = {6'd0,(msb_first ? rx_byte[7] : rx_byte[0]),1'b0};
        else if (cycle <= 7'd62) begin
            ena = 1'b1; ui_in = 8'h62; uio_in = {6'd0,serial_bit,1'b0};
        end else if (cycle == 7'd63 || cycle == 7'd66 || cycle == 7'd69) ui_in = 8'h63;
        else if (cycle == 7'd65) ui_in = 8'ha2;
        else if (cycle == 7'd67) begin
            ena = 1'b1; ui_in = 8'he4; uio_in = ~tx_byte;
        end else if (cycle == 7'd68) ui_in = 8'h62;
`ifdef ABORT_SCENARIO
        if (cycle >= 7'd21) begin
            if (exec_edge == {1'b0,abort_edge}) begin
                ena = abort_enable;
                if (abort_kind == 2'd0) ui_in = 8'h80;
                else if (abort_kind == 2'd1) begin ui_in = 8'hc0; uio_in = 8'hff; end
                else rst_n = 1'b0;
            end else if (exec_edge > {1'b0,abort_edge}) begin
                ena = 1'b0; ui_in = 8'h63; rst_n = 1'b1; uio_in = 8'd0;
            end
        end
`endif
    end
    tt_um_khangelani_protocol_emulator dut(.*);
    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (cycle < 7'd75) cycle <= cycle + 7'd1;
        if (past_valid && cycle >= 7'd21 && cycle <= 7'd62 && !ui_in[7]
`ifdef ABORT_SCENARIO
            && exec_edge <= {1'b0,abort_edge}
`endif
            ) begin
            assert(uio_oe == (cycle >= 7'd23 ? 8'd1 : 8'd0));
            assert(uio_out == (cycle >= 7'd23 ? {7'd0,expected_tx} : 8'd0));
        end
`ifdef ABORT_SCENARIO
        assume(abort_edge == 6'd41);
        assume(abort_kind <= 2'd2);
        if (past_valid && cycle >= 7'd21 && exec_edge > {1'b0,abort_edge}) begin
            assert(uo_out == 8'd0); // Runtime raw-valid, no old result in this scenario.
            assert(uio_oe == 8'd0 && uio_out == 8'd0);
        end
        cover(past_valid && exec_edge == 7'd42 && abort_edge == 6'd41 && abort_kind == 2'd0 && !abort_enable && uo_out == 8'd0);
        cover(past_valid && exec_edge == 7'd42 && abort_edge == 6'd41 && abort_kind == 2'd0 && abort_enable && uo_out == 8'd0);
        cover(past_valid && exec_edge == 7'd42 && abort_edge == 6'd41 && abort_kind == 2'd1 && uo_out == 8'd0);
        cover(past_valid && exec_edge == 7'd42 && abort_edge == 6'd41 && abort_kind == 2'd2 && uo_out == 8'd0);
`else
        if (past_valid) begin
            if (cycle >= 7'd21 && cycle <= 7'd61) assert(uo_out == 8'd0);
            if (cycle == 7'd62) assert(uo_out == rx_byte);
            if (cycle == 7'd63 || cycle == 7'd66) assert(uo_out == 8'd1);
            if (cycle == 7'd64) assert(uo_out == 8'ha3);
            if (cycle == 7'd65) assert(uio_out == rx_byte && uio_oe == 8'hff);
            if (cycle == 7'd68) assert(uo_out == rx_byte);
            if (cycle == 7'd69) assert(uo_out == 8'd0);
            if (cycle >= 7'd71) assert(uo_out == 8'd0 && uio_oe == 8'd0);
`ifdef EXPECT_ABORT_CLEAR
            if (cycle == 7'd66) assert(uo_out == 8'd0);
`endif
        end
        cover(past_valid && cycle == 7'd63 && uo_out == 8'd1);
        cover(past_valid && cycle == 7'd66 && uo_out == 8'd1);
        cover(past_valid && cycle == 7'd69 && uo_out == 8'd0);
        cover(past_valid && cycle == 7'd71 && uio_oe == 8'd0);
`endif
    end
endmodule
`default_nettype wire
