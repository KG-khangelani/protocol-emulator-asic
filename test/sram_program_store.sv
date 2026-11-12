/* SPDX-License-Identifier: Apache-2.0 */
`timescale 1ns/1ps
`default_nettype none
module sram_program_store;
    reg clk = 0, rst_n = 0, ena = 1;
    reg load_mode = 0, load_write = 0, load_length = 0, load_bank = 0;
    reg [4:0] byte_address = 0;
    reg [7:0] data_in = 0, pc = 0, prefetch_pc = 0;
    wire [7:0] data_out, program_length;
    wire [3:0] program_bank;
    wire program_ready, instruction_valid;
    wire [31:0] instruction;
    reg [31:0] expected [0:127];
    reg [31:0] wanted;
    reg [7:0] last_byte;
    integer checks = 0, bank, address, index, lane, unknown_checks = 0;
    m1_program_store dut (.*);

    task tick;
        begin
            #5; clk = 1;
            #5; clk = 0;
            #1;
        end
    endtask
    task check(input reg condition, input string label);
        begin
            if (condition !== 1'b1) begin
                $display("CHECK_FAILED %s pc=%0d bank=%0d address=%0d data=%02x instruction=%08x expected=%08x valid=%b", label, pc, program_bank, byte_address, data_out, instruction, wanted, instruction_valid);
                $fatal(1, "STORE_CHECK_FAILED");
            end
            checks = checks + 1;
        end
    endtask
    task control(input reg bank_select, input reg [7:0] value);
        begin
            load_mode = 1; load_write = 1;
            load_bank = bank_select; load_length = !bank_select;
            data_in = value;
            tick;
            load_write = 0; load_bank = 0; load_length = 0;
            #1;
        end
    endtask
    task byte_write(input integer offset, input reg [7:0] value);
        begin
            byte_address = 5'(offset); data_in = value; load_write = 1;
            tick;
            load_write = 0;
            if (ena)
                expected[8*program_bank+offset/4][8*(offset%4) +: 8] = value;
        end
    endtask
    task read_all(input string label);
        begin
            for (bank = 0; bank < 16; bank = bank + 1) begin
                control(1, 8'(bank));
                for (address = 0; address < 32; address = address + 1) begin
                    byte_address = 5'(address);
                    tick;
                    wanted = expected[8*bank+address/4];
                    check(data_out === wanted[8*(address%4) +: 8], label);
                end
            end
        end
    endtask
    initial begin
        for (index = 0; index < 128; index = index + 1) expected[index] = 0;
        wanted = 0;
        tick;
        check(program_length === 0 && program_bank === 0 && program_ready === 0, "initial_reset");
        rst_n = 1;
        read_all("zero_after_reset");
        for (bank = 0; bank < 16; bank = bank + 1) begin
            control(1, 8'(bank));
            check(program_bank === 4'(bank) && program_length === 0 && program_ready === 0, "bank_select");
            for (address = 0; address < 32; address = address + 1) begin
                index = 32*bank+address;
                byte_write(address, 8'(index*73+(index>>4)*19+41));
            end
        end
        // Disabled writes must preserve bytes; disabled reads still sample.
        ena = 0;
        byte_write(31, 8'hff);
        byte_address = 31; tick;
        wanted = expected[127];
        check(data_out === wanted[31:24], "disabled_write_and_read");
        ena = 1;
        read_all("all_byte_readback");

        control(0, 8'd128);
        check(program_length === 128 && program_bank === 0 && program_ready === 1, "length_commit");
        byte_address = 0; tick;
        last_byte = data_out;
        byte_address = 1; #2;
        check(data_out === last_byte, "clocked_read_holds_before_edge");
        tick;
        wanted = expected[0];
        check(data_out === wanted[15:8] && data_out !== last_byte, "clocked_read_updates_after_edge");
        // A program-byte read after commit must not disturb immediate PC0 entry.
        byte_address = 31; tick;
        load_mode = 0; pc = 0; prefetch_pc = 0; #1;
        wanted = expected[0];
        check(instruction === wanted && instruction_valid === 1, "word_zero_after_loader_read");
        for (index = 1; index < 256; index = index + 1) begin
            prefetch_pc = 8'(index);
            tick;
            pc = 8'(index); #1;
            wanted = (index < 128) ? expected[index] : 32'd0;
            check(instruction === wanted && instruction_valid === (index < 128), "lookahead_fetch");
        end
        // A stale nonzero fetch address must fail closed.
        pc = 120; prefetch_pc = 119; tick;
        wanted = 0;
        check(instruction === 0 && instruction_valid === 0, "stale_tag_rejected");
        prefetch_pc = 120; tick;
        wanted = expected[120];
        check(instruction === wanted && instruction_valid === 1, "stale_tag_recovery");
        control(1, 8'd16);
        check(program_bank === 0 && program_length === 0 && program_ready === 0, "invalid_bank");
        control(0, 8'd129);
        check(program_length === 0 && program_ready === 0, "invalid_length");
        control(0, 8'd0);
        check(program_length === 0 && program_ready === 0, "zero_length");

        // SRAM still contains nonzero bytes. Reset must hide all of them.
        rst_n = 0; ena = 0; load_write = 1; data_in = 8'hff; tick;
        for (index = 0; index < 128; index = index + 1) expected[index] = 0;
        wanted = 0;
        check(program_length === 0 && program_bank === 0 && program_ready === 0, "reset_wins_while_disabled");
        rst_n = 1; ena = 1; load_write = 0;
        read_all("zero_after_reset");
        // First partial writes must clear the other stale physical lanes.
        for (bank = 0; bank < 16; bank = bank + 1) begin
            control(1, 8'(bank));
            for (address = 0; address < 8; address = address + 1) begin
                index = 8*bank+address;
                lane = index%4;
                byte_write(4*address+lane, 8'(index*29+91));
            end
        end
        read_all("partial_first_write_zero_padding");
        control(0, 8'd128);
        load_mode = 0; pc = 0; #1;
        wanted = expected[0];
        check(instruction === wanted && instruction_valid === 1, "partial_word_zero_shadow");
        for (index = 0; index < 128; index = index + 1) begin
            prefetch_pc = 8'(index); tick; pc = 8'(index); #1;
            wanted = expected[index];
            check(instruction === wanted && instruction_valid === 1, "partial_word_fetch");
        end
`ifndef VERILATOR
        pc = 8'b00000x00; #1;
        check(instruction === 0, "unknown_low_fetch"); unknown_checks = unknown_checks + 1;
        pc = 8'b0x000000; #1;
        check(instruction === 0, "unknown_high_fetch"); unknown_checks = unknown_checks + 1;
`endif
        $display("PASS_SRAM_STORE_PORTS checks=%0d unknown_checks=%0d", checks, unknown_checks);
        $finish;
    end
endmodule
`default_nettype wire
