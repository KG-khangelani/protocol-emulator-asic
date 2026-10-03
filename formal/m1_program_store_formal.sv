/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_program_store_formal (
    input wire clk, input wire rst_n, input wire ena,
    input wire load_mode, input wire load_write, input wire load_length,
    input wire [4:0] byte_address, input wire [7:0] data_in,
    input wire [4:0] pc
);
    wire [7:0] data_out;
    wire [3:0] program_length;
    wire program_ready;
    wire [31:0] instruction;
    wire instruction_valid;
    reg past_valid = 1'b0;
    reg reset_seen = 1'b0;

    m1_program_store dut (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .load_mode(load_mode), .load_write(load_write), .load_length(load_length),
        .byte_address(byte_address), .data_in(data_in), .pc(pc),
        .data_out(data_out), .program_length(program_length),
        .program_ready(program_ready), .instruction(instruction),
        .instruction_valid(instruction_valid)
    );

    always @(*) begin
        assert (instruction_valid ==
                (program_ready && (pc < {1'b0, program_length}) && (pc < 5'd8)));
        if (load_length)
            assert (data_out == {4'd0, program_length});
    end

    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!rst_n)
            reset_seen <= 1'b1;
        if (past_valid) begin
            if (!$past(rst_n)) begin
                assert (!program_ready && program_length == 4'd0);
                assert (instruction == 32'd0);
            end else if ($past(reset_seen)) begin
                if ($past(ena && load_mode && load_write && load_length)) begin
                    if ($past(data_in[7:4]) == 4'd0 &&
                        $past(data_in[3:0]) >= 4'd1 && $past(data_in[3:0]) <= 4'd8) begin
                        assert (program_ready);
                        assert (program_length == $past(data_in[3:0]));
                    end else begin
                        assert (!program_ready && program_length == 4'd0);
                    end
                end else if ($past(ena && load_mode && load_write && !load_length)) begin
                    assert (!program_ready);
                    assert (program_length == $past(program_length));
                    if (!load_length && byte_address == $past(byte_address))
                        assert (data_out == $past(data_in));
                end else begin
                    assert (program_ready == $past(program_ready));
                    assert (program_length == $past(program_length));
                end
            end
        end
        cover (reset_seen && program_ready && program_length == 4'd8);
        cover (reset_seen && !program_ready && program_length == 4'd0);
    end
endmodule

`default_nettype wire
