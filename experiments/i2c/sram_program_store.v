/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_program_store (
    input wire clk, input wire rst_n, input wire ena,
    input wire load_mode, input wire load_write, input wire load_length,
    input wire load_bank, input wire [4:0] byte_address,
    input wire [7:0] data_in, input wire [7:0] pc,
    input wire [7:0] prefetch_pc,
    output reg [7:0] data_out, output reg [7:0] program_length,
    output reg program_ready, output reg [3:0] program_bank,
    output reg [31:0] instruction, output wire instruction_valid
);
    reg [127:0] word_valid;
    reg [31:0] word_zero;
    reg [7:0] read_address;
    reg [1:0] read_lane;
    reg read_present;

    wire program_access = load_mode && !load_length && !load_bank;
    wire program_write = rst_n && ena && program_access && load_write;
    wire [7:0] memory_address = program_access ?
        {1'b0, program_bank, byte_address[4:2]} : prefetch_pc;
    wire [4:0] byte_shift = {byte_address[1:0], 3'b000};
    wire [31:0] byte_mask = 32'h000000ff << byte_shift;
    wire [31:0] write_mask = word_valid[memory_address[6:0]] ?
        byte_mask : 32'hffffffff;
    wire [31:0] write_data = {24'd0, data_in} << byte_shift;
    wire [31:0] memory_data;
    wire [31:0] read_word = read_present ? memory_data : 32'd0;
    wire length_valid = (data_in >= 8'd1) && (data_in <= 8'd128);

    RM_IHPSG13_1P_256x32_c2_bm_bist program_memory (
        .A_CLK(clk), .A_MEN(rst_n), .A_WEN(program_write), .A_REN(1'b1),
        .A_ADDR(memory_address), .A_DIN(write_data), .A_BM(write_mask),
        .A_DLY(1'b1), .A_DOUT(memory_data),
        .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0),
        .A_BIST_WEN(1'b0), .A_BIST_REN(1'b0), .A_BIST_ADDR(8'd0),
        .A_BIST_DIN(32'd0), .A_BIST_BM(32'd0)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            word_valid <= 128'd0;
            word_zero <= 32'd0;
            program_length <= 8'd0;
            program_ready <= 1'b0;
            program_bank <= 4'd0;
            read_address <= 8'd0;
            read_lane <= 2'd0;
            read_present <= 1'b0;
        end else begin
            // Reads remain available while instruction execution is disabled.
            read_address <= memory_address;
            read_lane <= byte_address[1:0];
            read_present <= program_write ||
                (!memory_address[7] && word_valid[memory_address[6:0]]);
            if (program_write) begin
                word_valid[memory_address[6:0]] <= 1'b1;
                if (memory_address == 8'd0)
                    word_zero[byte_shift +: 8] <= data_in;
            end
            if (ena && load_mode && load_write) begin
                if (load_bank) begin
                    program_bank <= (data_in < 8'd16) ? data_in[3:0] : 4'd0;
                    program_length <= 8'd0;
                    program_ready <= 1'b0;
                end else if (load_length) begin
                    program_bank <= 4'd0;
                    program_length <= length_valid ? data_in : 8'd0;
                    program_ready <= length_valid;
                end else
                    program_ready <= 1'b0;
            end
        end
    end

    always @* begin
        case (read_lane)
            2'd0: data_out = read_word[7:0];
            2'd1: data_out = read_word[15:8];
            2'd2: data_out = read_word[23:16];
            2'd3: data_out = read_word[31:24];
            default: data_out = 8'd0;
        endcase
        if (load_length)
            data_out = program_length;
        instruction = 32'd0;
        if (pc == 8'd0)
            instruction = word_zero;
        else if (!pc[7] && (read_address == pc) && read_present)
            instruction = memory_data;
    end
    assign instruction_valid = program_ready && (pc < program_length) &&
        (pc < 8'd128) && ((pc == 8'd0) || (read_address == pc));
endmodule

`default_nettype wire
