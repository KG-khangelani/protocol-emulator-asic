/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_program_store (
    input wire clk, input wire rst_n, input wire ena,
    input wire load_mode, input wire load_write, input wire load_length, input wire load_bank,
    input wire [4:0] byte_address, input wire [7:0] data_in,
    input wire [4:0] pc,
    output reg [7:0] data_out, output reg [3:0] program_length,
    output reg program_ready, output reg program_bank, output reg [31:0] instruction,
    output wire instruction_valid
);
    reg [31:0] word0, word1, word2, word3;
    reg [31:0] word4, word5, word6, word7;
    reg [31:0] word8, word9;
    wire [5:0] bank_address = {program_bank, byte_address};
    wire length_valid = (data_in[7:4] == 4'd0) &&
                        (data_in[3:0] >= 4'd1) && (data_in[3:0] <= 4'd10);

    always @(posedge clk) begin
        if (!rst_n) begin
            word0 <= 32'd0; word1 <= 32'd0; word2 <= 32'd0; word3 <= 32'd0;
            word4 <= 32'd0; word5 <= 32'd0; word6 <= 32'd0; word7 <= 32'd0;
            word8 <= 32'd0; word9 <= 32'd0; program_bank <= 1'b0;
            program_length <= 4'd0;
            program_ready <= 1'b0;
        end else if (ena && load_mode && load_write) begin
            if (load_bank) begin
                program_bank <= (data_in <= 8'd1) ? data_in[0] : 1'b0;
                program_length <= 4'd0;
                program_ready <= 1'b0;
            end else if (load_length) begin
                program_bank <= 1'b0;
                program_length <= length_valid ? data_in[3:0] : 4'd0;
                program_ready <= length_valid;
            end else begin
                program_ready <= 1'b0;
                case (bank_address[5:2])
                    4'd0: word0[8*byte_address[1:0] +: 8] <= data_in;
                    4'd1: word1[8*byte_address[1:0] +: 8] <= data_in;
                    4'd2: word2[8*byte_address[1:0] +: 8] <= data_in;
                    4'd3: word3[8*byte_address[1:0] +: 8] <= data_in;
                    4'd4: word4[8*byte_address[1:0] +: 8] <= data_in;
                    4'd5: word5[8*byte_address[1:0] +: 8] <= data_in;
                    4'd6: word6[8*byte_address[1:0] +: 8] <= data_in;
                    4'd7: word7[8*byte_address[1:0] +: 8] <= data_in;
                    4'd8: word8[8*byte_address[1:0] +: 8] <= data_in;
                    4'd9: word9[8*byte_address[1:0] +: 8] <= data_in;
                    default: begin end
                endcase
            end
        end
    end

    // verilog_lint: waive always-comb
    always @(*) begin
        case (bank_address[5:2])
            4'd0: data_out = word0[8*byte_address[1:0] +: 8];
            4'd1: data_out = word1[8*byte_address[1:0] +: 8];
            4'd2: data_out = word2[8*byte_address[1:0] +: 8];
            4'd3: data_out = word3[8*byte_address[1:0] +: 8];
            4'd4: data_out = word4[8*byte_address[1:0] +: 8];
            4'd5: data_out = word5[8*byte_address[1:0] +: 8];
            4'd6: data_out = word6[8*byte_address[1:0] +: 8];
            4'd7: data_out = word7[8*byte_address[1:0] +: 8];
            4'd8: data_out = word8[8*byte_address[1:0] +: 8];
            4'd9: data_out = word9[8*byte_address[1:0] +: 8];
            default: data_out = 8'd0;
        endcase
        if (load_length)
            data_out = {4'd0, program_length};
        case (pc[3:0])
            4'd0: instruction = word0;
            4'd1: instruction = word1;
            4'd2: instruction = word2;
            4'd3: instruction = word3;
            4'd4: instruction = word4;
            4'd5: instruction = word5;
            4'd6: instruction = word6;
            4'd7: instruction = word7;
            4'd8: instruction = word8;
            4'd9: instruction = word9;
            default: instruction = 32'd0;
        endcase
    end

    assign instruction_valid = program_ready && (pc < {1'b0, program_length}) && (pc < 5'd10);
endmodule

`default_nettype wire
