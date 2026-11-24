// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none
module uart_period_tb;
    reg clk = 0;
    always #10 clk = ~clk;

    reg rst_n = 0, ena = 0, host_drive = 0, source_on = 0, rx = 1;
    reg [7:0] ui = 0, host_data = 0;
    wire [7:0] uo, out_byte, oe;
    tri0 [7:0] pins;
    assign pins = host_drive ? host_data : 8'hzz;
    assign pins[1] = source_on ? rx : 1'bz;
    genvar bit_index;
    for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
        assign pins[bit_index] = oe[bit_index] ? out_byte[bit_index] : 1'bz;
    end
    tt_um_khangelani_protocol_emulator dut(
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui), .uo_out(uo),
        .uio_in(pins), .uio_out(out_byte), .uio_oe(oe)
    );

    reg [7:0] image [0:31];
    task tick;
        begin @(posedge clk); #1; end
    endtask
    task write_byte(input [7:0] select_byte, input [7:0] value);
        begin
            ui = select_byte; host_data = value; host_drive = 1;
            tick();
            if (oe !== 0) $fatal(1, "loader write owns shared pins");
        end
    endtask
    task load_rx;
        integer address;
        begin
            source_on = 0; host_drive = 0; ena = 0; rst_n = 0; ui = 0;
            tick();
            rst_n = 1; ui = 8'h67; #1;
            if (uo !== 8'h22) $fatal(1, "wrong interface id");
            ena = 1;
            write_byte(8'he5, 0);
            for (address = 0; address < 32; address = address + 1)
                write_byte(8'hc0 | address[4:0], image[address]);
            write_byte(8'he5, 0);
            host_drive = 0;
            for (address = 0; address < 32; address = address + 1) begin
                ui = 8'h80 | address[4:0]; tick();
                if (oe !== 8'hff || pins !== image[address])
                    $fatal(1, "program readback mismatch at %0d", address);
            end
            write_byte(8'he0, 8);
            write_byte(8'he1, 8'hff);
            write_byte(8'he4, 8'hff);
            host_drive = 0; ena = 0; ui = 0; source_on = 1; rx = 1;
            tick(); tick(); ui = 8'h63; #1;
            if (uo !== 0 || oe !== 0) $fatal(1, "bad handoff");
            ui = 0; ena = 1;
        end
    endtask

    // Integer quotients put each transition on its first eligible raw clock.
    // The transmitter clock and phase stay independent of the receiver state.
    function automatic reg line_level(input integer edge_number, percent, phase);
        integer delta, wire_cell, frame_cell;
        reg [7:0] payload;
        begin
            delta = edge_number * 4 - (16 + phase);
            line_level = 1;
            if (delta >= 0) begin
                wire_cell = (delta * percent) / (4 * 43400);
                frame_cell = wire_cell % 10;
                payload = (wire_cell < 10) ? 8'h55 : 8'haa;
                if (wire_cell < 20 && frame_cell == 0) line_level = 0;
                if (wire_cell < 20 && frame_cell > 0 && frame_cell < 9)
                    line_level = payload[frame_cell - 1];
            end
        end
    endfunction

    task run_case(input integer percent, phase);
        integer num, capture1, capture2, halt_edge, first_poll;
        integer old_h, safe_h, safe_sum, prior_valid, old_poll, safe_poll;
        integer old_copy, safe_copy, weakened_copy, old_terminal;
        reg [7:0] status, raw_byte, valid_byte;
        begin
            load_rx();
            capture1 = -1; capture2 = -1; halt_edge = -1;
            prior_valid = -1; old_poll = -1; safe_poll = -1;
            old_copy = -1; safe_copy = -1; weakened_copy = -1; old_terminal = -1;
            // Worst polling residue: the first scheduled poll is one edge
            // before the predicted first capture. L=2 for every schedule.
            first_poll = ((16 + phase + 3) / 4) + 2 + 3689 - 1;
            old_h = 4338;
            safe_sum = 434000 / percent;
            safe_h = safe_sum - 2;
            for (num = 1; num <= 13000; num = num + 1) begin
                ui = 0;
                rx = line_level(num, percent, phase);
                tick(); status = uo;
                if (oe[1] !== 0 || status[5] !== 1 || status[7:6] === 2'b11)
                    $fatal(1, "unexpected RX ownership/status %0d %0d %0d %h", percent, phase, num, status);
                if (halt_edge < 0 && status === 8'ha7) halt_edge = num;
                ui = 8'h63; #1; valid_byte = uo;
                ui = 8'h62; #1; raw_byte = uo;
                if (valid_byte === 8'h01) begin
                    if (capture1 < 0) begin
                        capture1 = num;
                        if (raw_byte !== 8'h55) $fatal(1, "incorrect first capture");
                    end
                    if (capture2 < 0 && raw_byte === 8'haa) capture2 = num;
                    if (raw_byte !== 8'h55 && raw_byte !== 8'haa)
                        $fatal(1, "unexpected captured byte");
                end
                if (num == first_poll) prior_valid = valid_byte;
                if (num == first_poll + old_h) old_poll = valid_byte;
                if (num == first_poll + safe_h) safe_poll = valid_byte;
                if (num == first_poll + old_h + 2) old_copy = raw_byte;
                if (num == first_poll + safe_h + 2) safe_copy = raw_byte;
                if (num == first_poll + safe_h + 3) weakened_copy = raw_byte;
                if (num == first_poll + old_h * 2 + 2 && status === 8'ha7 && valid_byte === 1)
                    old_terminal = raw_byte;
            end
            if (prior_valid != 0 || old_poll != 1 || safe_poll != 1)
                $fatal(1, "invalid polling residue");
            $display("RESULT %0d %0d %0d %0d %0d %0d %0d %0d %0d",
                     percent, phase, capture1, capture2, halt_edge, old_copy,
                     safe_copy, weakened_copy, old_terminal);
        end
    endtask

    integer rate, quarter_phase;
    initial begin
        $readmemh("program.hex", image);
        for (rate = 98; rate <= 102; rate = rate + 1)
            for (quarter_phase = 0; quarter_phase < 4; quarter_phase = quarter_phase + 1)
                run_case(rate, quarter_phase);
        $finish;
    end
endmodule
`default_nettype wire
