/* SPDX-License-Identifier: Apache-2.0 */
(* anyconst *) reg [6:0] f_index;
wire [31:0] f_physical_word;
reg [31:0] f_expected;
reg [31:0] f_read_expected;
reg [7:0] f_read_address;
reg [1:0] f_read_lane;
reg f_past_valid = 1'b0;
reg f_reset_seen = 1'b0;
reg f_seen_write = 1'b0;
wire [7:0] f_program_address = {1'b0, program_bank, byte_address[4:2]};
wire f_write = ena && load_mode && load_write;
wire f_byte_write = f_write && !load_bank && !load_length;
wire [7:0] f_selected_address =
    (load_mode && !load_length && !load_bank) ? f_program_address : prefetch_pc;

always @* begin
    if (f_reset_seen) begin
        assert ((word_valid[f_index] ? f_physical_word : 32'd0) == f_expected);
        if (f_index == 0) assert (word_zero == f_expected);
        assert (read_address == f_read_address && read_lane == f_read_lane);
        if (read_address == {1'b0, f_index}) begin
            assert (read_word == f_read_expected);
            if (!load_length)
                assert (data_out == f_read_expected[8*f_read_lane +: 8]);
        end
        if (load_length) assert (data_out == program_length);
        if (pc == 0 && f_index == 0) assert (instruction == f_expected);
        if (pc != 0 && pc == {1'b0, f_index} && read_address == pc)
            assert (instruction == f_read_expected);
        if (pc >= 128 || (pc != 0 && read_address != pc))
            assert (instruction == 0);
        assert (instruction_valid == (program_ready && pc < program_length &&
            pc < 128 && (pc == 0 || read_address == pc)));
    end
end

always @(posedge clk) begin
    f_past_valid <= 1'b1;
    if (!f_past_valid) assume (!rst_n);
    if (!rst_n) begin
        f_expected <= 32'd0;
        f_read_expected <= 32'd0;
        f_read_address <= 8'd0;
        f_read_lane <= 2'd0;
        f_reset_seen <= 1'b1;
    end else begin
        f_read_expected <= f_expected;
        f_read_address <= f_selected_address;
        f_read_lane <= byte_address[1:0];
        if (f_byte_write && f_program_address == {1'b0, f_index}) begin
            f_expected[8*byte_address[1:0] +: 8] <= data_in;
            f_read_expected[8*byte_address[1:0] +: 8] <= data_in;
            f_seen_write <= 1'b1;
        end
    end
    if (f_past_valid) begin
        if (!$past(rst_n)) begin
            assert (program_length == 0 && !program_ready && program_bank == 0);
        end else if ($past(f_write && load_bank)) begin
            assert (program_length == 0 && !program_ready);
            assert (program_bank == ($past(data_in) < 16 ? $past(data_in[3:0]) : 0));
        end else if ($past(f_write && load_length)) begin
            assert (program_bank == 0);
            assert (program_ready == ($past(data_in) >= 1 && $past(data_in) <= 128));
            assert (program_length == (($past(data_in) >= 1 && $past(data_in) <= 128) ? $past(data_in) : 0));
        end else begin
            assert (program_length == $past(program_length) && program_bank == $past(program_bank));
            assert (program_ready == ($past(f_write) ? 0 : $past(program_ready)));
        end
    end
    cover (f_reset_seen && f_index == 127 && program_ready && program_length == 128 &&
           pc == 127 && instruction_valid && instruction != 0);
    cover (f_reset_seen && f_index == 0 && word_zero[31:24] != 0 && instruction_valid && pc == 0);
    cover (f_reset_seen && f_seen_write && !word_valid[f_index] && f_physical_word != 0 && f_expected == 0);
    cover (f_reset_seen && !ena && read_address == {1'b0, f_index} && read_word != 0);
end
