/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module public_spi(input wire clk);
`ifdef VARIANT_F
    localparam [31:0] DRIVE_DELAY=0, TRAILING_WORD=32'h38040400;
`else
    localparam [31:0] DRIVE_DELAY=6, TRAILING_WORD=32'h00040400;
`endif
    (* anyconst *) reg [7:0] tx_byte, rx_byte;
    (* anyconst *) reg msb_first, cpol;
    (* anyseq *) reg raw_miso, select_valid;
    reg [8:0] cycle = 9'd0;
    reg past_valid = 1'b0;
    reg rst_n, ena;
    reg [7:0] ui_in, uio_in;
    wire [7:0] uo_out, uio_out, uio_oe;
    wire [8:0] exec_edge = cycle - 9'd36;
    wire [8:0] previous_edge = cycle - 9'd37;
    wire [8:0] write_index = cycle - 9'd1;
    reg [31:0] load_word;
    reg expected_mosi, expected_sck;
    integer j;
    always @(*) begin
        case (write_index[4:2])
            3'd0: load_word = 32'h000c0c08 | (cpol ? 32'd4 : 32'd0);
            3'd1: load_word = 32'h170c0c00 | (cpol ? 32'd4 : 32'd0);
            3'd2: load_word = 32'h63000008;
            3'd3: load_word = 32'ha0486000 | (msb_first ? 32'h10000000 : 32'd0) | (cpol ? 32'd0 : 32'h20) | DRIVE_DELAY;
            3'd4: load_word = TRAILING_WORD | (cpol ? 32'd4 : 32'd0);
            3'd5: load_word = 32'ha05000b8 | (msb_first ? 32'h10000000 : 32'd0);
            3'd6: load_word = 32'h000c0c08 | (cpol ? 32'd4 : 32'd0);
            default: load_word = 32'h80000000;
        endcase
        rst_n = cycle != 9'd0 && cycle != 9'd466;
        ena = 1'b0; ui_in = 8'd0; uio_in = 8'd0;
        if (cycle >= 9'd1 && cycle <= 9'd32) begin
            ena = 1'b1; ui_in = 8'hc0 | {3'd0,write_index[4:0]};
            uio_in = load_word[8*write_index[1:0] +: 8];
        end else if (cycle == 9'd33) begin
            ena = 1'b1; ui_in = 8'he0; uio_in = 8'd8;
        end else if (cycle == 9'd34) begin
            ena = 1'b1; ui_in = 8'he1; uio_in = tx_byte;
        end else if (cycle == 9'd35 || cycle == 9'd36) uio_in = 8'd2;
        else if (cycle >= 9'd37 && cycle <= 9'd464) begin
            ena = 1'b1; ui_in = select_valid ? 8'h63 : 8'h62;
            uio_in = {6'd0,raw_miso,1'b0};
        end
        expected_mosi = 1'b0; expected_sck = cpol;
        for (integer k=0;k<8;k=k+1) begin
            if (previous_edge >= 27+50*k)
                expected_mosi = msb_first ? tx_byte[7-k] : tx_byte[k];
            if (previous_edge >= 27+50*k && previous_edge < 52+50*k)
                expected_sck = !cpol;
        end
    end
    `include "program_bindings.vh"
    tt_um_khangelani_protocol_emulator dut(.*);
    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (cycle < 9'd468) cycle <= cycle + 9'd1;
        // A consequence of HELD_RESPONSE, not an electrical aperture model.
        // Other raw ticks, bytes, order, polarity and readout selector are symbolic.
        for (j=0;j<8;j=j+1)
            if (cycle >= 9'd37 && cycle <= 9'd464 &&
                exec_edge >= 52+50*j && exec_edge <= 77+50*j)
                assume(raw_miso == (msb_first ? rx_byte[7-j] : rx_byte[j]));
        if (past_valid && cycle >= 9'd37 && cycle <= 9'd464) begin
            assert(uio_oe == (previous_edge >= 9'd27 ? 8'd13 : (previous_edge >= 9'd1 ? 8'd12 : 8'd0)));
            assert(uio_out == (previous_edge >= 9'd1 ?
                {4'd0,(previous_edge < 9'd2 || previous_edge >= 9'd427),expected_sck,1'b0,(previous_edge == 9'd27 ? ~expected_mosi : expected_mosi)} : 8'd0));
            assert(!uio_oe[1]);
            if (select_valid) assert(uo_out == (previous_edge >= 9'd426 ? 8'd1 : 8'd0));
            else assert(uo_out == (previous_edge >= 9'd426 ? rx_byte : 8'd0));
        end
        if (past_valid && cycle == 9'd465) begin
            assert(uo_out == 8'ha7);
            assert(uio_oe == 8'd13 && uio_out == {4'd0,1'b1,cpol,1'b0,expected_mosi});
        end
        if (past_valid && cycle == 9'd467)
            assert(uo_out == 8'd0 && uio_oe == 8'd0 && uio_out == 8'd0);
    end
    `include "program_invariants.vh"
endmodule
`default_nettype wire
