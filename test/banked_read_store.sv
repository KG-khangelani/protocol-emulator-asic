/* SPDX-License-Identifier: Apache-2.0 */
`timescale 1ns/1ps
`default_nettype none
module banked_read_store;
    reg clk = 0;
    reg rst_n = 0;
    reg ena = 1;
    reg load_mode = 0;
    reg load_write = 0;
    reg load_length = 0;
    reg load_bank = 0;
    reg [4:0] byte_address = 0;
    reg [7:0] data_in = 0;
    reg [7:0] pc = 0;
    wire [7:0] data_out, program_length;
    wire program_ready, instruction_valid;
    wire [3:0] program_bank;
    wire [31:0] instruction;
    reg [31:0] expected [0:127];
    reg [31:0] wanted;
    integer index, bank, lane, checks = 0, unknown_checks = 0;

    m1_program_store dut (.*);

    task tick;
        begin
            #5; clk = 1;
            #5; clk = 0;
            #1;
        end
    endtask

    task control(input reg bank_select, input reg [7:0] value);
        begin
            load_mode = 1;
            load_write = 1;
            load_bank = bank_select;
            load_length = !bank_select;
            data_in = value;
            tick;
            load_write = 0;
            load_bank = 0;
            load_length = 0;
            #1;
        end
    endtask

    task check(input reg condition, input string label);
        begin
            if (condition !== 1'b1) begin
                $display("CHECK_FAILED %s pc=%0d bank=%0d observed=%08x expected=%08x", label, pc, program_bank, instruction, wanted);
                $fatal(1, "PORT_CHECK_FAILED");
            end
            checks = checks + 1;
        end
    endtask

    initial begin
        tick;
        check(program_length === 0 && program_bank === 0 && program_ready === 0, "initial_reset");
        rst_n = 1;
        for (index = 0; index < 128; index = index + 1) begin
            expected[index] = 0;
            for (lane = 0; lane < 4; lane = lane + 1)
                expected[index][8*lane +: 8] = 8'((4*index+lane)*73 + ((4*index+lane)>>4)*19 + 41);
        end
        for (bank = 0; bank < 16; bank = bank + 1) begin
            control(1, 8'(bank));
            check(program_bank === 4'(bank) && program_ready === 0 && program_length === 0, "bank_select");
            for (index = 0; index < 32; index = index + 1) begin
                byte_address = 5'(index);
                data_in = expected[bank*8 + index/4][8*(index%4) +: 8];
                load_write = 1;
                tick;
            end
            load_write = 0;
        end
        // A disabled write must not corrupt the last loaded word.
        ena = 0;
        load_write = 1;
        data_in = 8'hff;
        tick;
        load_write = 0;
        ena = 1;
        control(0, 8'd128);
        check(program_length === 128 && program_ready === 1 && program_bank === 0, "length_commit");
        load_mode = 0;
        for (index = 0; index < 256; index = index + 1) begin
            pc = 8'(index);
            byte_address = 5'(index);
            wanted = (index < 128) ? expected[index] : 32'd0;
            #1;
            check(instruction === wanted && instruction_valid === (index < 128), "fetch");
            check(data_out === wanted[8*(index%4) +: 8], "inactive_byte_read");
        end
        for (bank = 0; bank < 16; bank = bank + 1) begin
            control(1, 8'(bank));
            pc = 8'd255;
            for (index = 0; index < 32; index = index + 1) begin
                byte_address = 5'(index);
                wanted = expected[bank*8 + index/4];
                #1;
                check(data_out === wanted[8*(index%4) +: 8] && instruction === wanted, "loader_readback");
            end
        end
        control(0, 8'd128);
        load_length = 1;
        #1;
        check(data_out === 128, "length_override");
        load_length = 0;
        control(1, 8'd16);
        check(program_bank === 0 && program_length === 0 && program_ready === 0, "invalid_bank");
        control(0, 8'd1);
        check(program_length === 1 && program_ready === 1, "short_length");
        control(0, 8'd129);
        check(program_length === 0 && program_ready === 0, "invalid_length");
        control(0, 8'd0);
        check(program_length === 0 && program_ready === 0, "zero_length");
        load_mode = 0;
`ifndef VERILATOR
        pc = 8'b00000x00;
        #1;
        check(instruction === 0, "unknown_low");
        unknown_checks = unknown_checks + 1;
        pc = 8'b0x000000;
        #1;
        check(instruction === 0, "unknown_high");
        unknown_checks = unknown_checks + 1;
`endif
        ena = 0;
        rst_n = 0;
        tick;
        check(program_bank === 0 && program_length === 0 && program_ready === 0, "reset_while_disabled");
        rst_n = 1;
        for (index = 0; index < 128; index = index + 1) begin
            pc = 8'(index);
            #1;
            wanted = 0;
            check(instruction === 0 && instruction_valid === 0, "full_reset_readback");
        end
        $display("PASS_STORE_PORT_TEST checks=%0d unknown_checks=%0d", checks, unknown_checks);
        $finish;
    end
endmodule
`default_nettype wire
