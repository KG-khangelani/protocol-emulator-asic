// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none

module launch_tb;
    reg clk = 0;
    reg rst_n;
    reg ref_ena = 0;
    reg [7:0] ref_ui = 0, sel_ui = 0;
    reg [7:0] ref_env = 0, sel_env = 0;
    wire [7:0] ref_status, ref_out, ref_oe, sel_status, sel_out, sel_oe;
    wire [7:0] ref_pins = (ref_out & ref_oe) | (ref_env & ~ref_oe);
    wire [7:0] sel_pins = (sel_out & sel_oe) | (sel_env & ~sel_oe);

    tt_um_khangelani_protocol_emulator reference_device(
        .clk(clk), .rst_n(rst_n), .ena(ref_ena), .ui_in(ref_ui),
        .uio_in(ref_pins), .uio_out(ref_out), .uio_oe(ref_oe), .uo_out(ref_status)
    );
    tt_um_khangelani_protocol_emulator selected_device(
        .clk(clk), .rst_n(rst_n), .ena(1'b1), .ui_in(sel_ui),
        .uio_in(sel_pins), .uio_out(sel_out), .uio_oe(sel_oe), .uo_out(sel_status)
    );

    string plan;
    integer file_id, fields, line_count, idle_edges, run_edge, selector;
    integer flush, reset_value, enable_value, ui, external_byte, host_owns;
    integer expect_oe, expect_out, expect_status, mode, witness;
    localparam NORMAL = 0, SHORT_IDLE = 1, BAD_BANK = 2, BAD_TURN = 3;

    task tick;
        #3 clk = 1;
        #4 clk = 0;
        #3;
    endtask

    task compare_public;
        begin
            if ((ref_status !== sel_status) || (ref_oe !== sel_oe) ||
                ((ref_out & ref_oe) !== (sel_out & sel_oe)) ||
                $isunknown(ref_status) || $isunknown(ref_oe) || $isunknown(ref_out & ref_oe))
                $fatal(1, "Public mismatch or X at execution edge %0d selector %h", run_edge, sel_ui);
        end
    endtask

    initial begin
        if (!$value$plusargs("PLAN=%s", plan) || !$value$plusargs("MODE=%d", mode) ||
            !$value$plusargs("WITNESS=%d", witness)) $fatal(1, "missing arguments");
        file_id = $fopen(plan, "r");
        if (!file_id) $fatal(1, "cannot open plan");
        // Apply reset after simulated time begins so combinational next-state
        // processes observe the X-to-zero transition before the first clock.
        #1;
        line_count = 0;
        idle_edges = 0;
        while (!$feof(file_id)) begin
            fields = $fscanf(file_id, "%d %d %d %d %d %d %d %d %d\n",
                flush, reset_value, enable_value, ui, external_byte, host_owns,
                expect_oe, expect_out, expect_status);
            if (fields != 9) $fatal(1, "bad plan at step %0d", line_count);
            rst_n = reset_value[0];
            ref_ena = enable_value[0];
            ref_ui = ui[7:0];
            sel_ui = flush ? 8'he7 : ui[7:0];
            ref_env = external_byte[7:0];
            sel_env = external_byte[7:0];
            if (flush) begin
                idle_edges = idle_edges + 1;
                if (mode == SHORT_IDLE && idle_edges == 1) sel_env = 8'h00;
                if (mode == BAD_BANK && idle_edges == 1) sel_ui = 8'he5;
            end
            #1;
            if (host_owns && (ref_oe !== 0 || sel_oe !== 0))
                $fatal(1, "host/ASIC contention at step %0d", line_count);
            if (flush && (sel_oe !== 0 || ref_oe !== 0))
                $fatal(1, "project drives during settled handoff at step %0d", line_count);
            tick;
            if ((ref_oe !== expect_oe[7:0]) || (sel_oe !== expect_oe[7:0]))
                $fatal(1, "wrong direction at step %0d: ref=%h selected=%h expected=%h",
                       line_count, ref_oe, sel_oe, expect_oe[7:0]);
            if (expect_out >= 0 &&
                (ref_out !== expect_out[7:0] || sel_out !== expect_out[7:0]))
                $fatal(1, "readback mismatch at step %0d", line_count);
            if (expect_status >= 0 && ref_status !== expect_status[7:0])
                $fatal(1, "reference status at step %0d", line_count);
            if (expect_status >= 0 && !(mode == BAD_BANK && flush) &&
                sel_status !== expect_status[7:0])
                $fatal(1, "selected status at step %0d", line_count);
            line_count = line_count + 1;
        end
        $fclose(file_id);
        if (idle_edges != 2) $fatal(1, "wrong warm-up length");
        if (mode == BAD_BANK) begin
            if (sel_status !== 8'h00 || ref_status !== 8'h20) $fatal(1, "missed bank invalidation");
            $display("CONTROL invalidating_bank selected=%h reference=%h", sel_status, ref_status);
            $finish;
        end
        if (mode == BAD_TURN) begin
            sel_ui = 8'ha7;
            #1;
            if (sel_oe !== 8'hff || sel_out !== 8'h22) $fatal(1, "missed all-driver exposure");
            $display("CONTROL intermediate_read oe=%h driven=%h", sel_oe, sel_out);
            $finish;
        end
        // Single-bit exit while clock is low, then select normal status.
        sel_ui = 8'h67;
        #1;
        if (sel_oe !== 0 || sel_status !== 8'h22) $fatal(1, "unreleased transition or wrong identity");
        sel_ui = 0;
        ref_ui = 0;
        ref_ena = 1;
        #1;
        for (run_edge = 1; run_edge <= 64; run_edge = run_edge + 1) begin
            tick;
            if (mode == SHORT_IDLE) begin
                if (sel_status !== 8'he0 || ref_status !== 8'h21) $fatal(1, "missed stale-input fault");
                $display("CONTROL stale_idle selected=%h reference=%h", sel_status, ref_status);
                $finish;
            end
            compare_public;
            if (witness && run_edge == 1 && sel_status !== 8'h21) $fatal(1, "first WAIT failed");
            if (witness && run_edge == 2 && (sel_oe !== 1 || sel_out !== 1 || sel_status !== 8'h22))
                $fatal(1, "literal SET did not execute");
            if (witness && run_edge == 3 && sel_status !== 8'ha2) $fatal(1, "literal HALT missing");
            for (selector = 1; selector <= 7; selector = selector + 1) begin
                ref_ui = 8'h60 + selector;
                sel_ui = ref_ui;
                #1;
                compare_public;
            end
            ref_ui = 0;
            sel_ui = 0;
            #1;
        end
        $display("MATCH loader_steps=%0d edges=64 status=%h driven=%h oe=%h",
                 line_count, sel_status, (sel_oe & sel_out), sel_oe);
        $finish;
    end
endmodule
`default_nettype wire
