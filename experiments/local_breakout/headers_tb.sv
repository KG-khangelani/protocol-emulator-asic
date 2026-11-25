// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none
module headers_tb;
    tri [28:0] gp;
    `include "header_instance.vh"
    reg [7:0] ui = 0;
    reg reset = 0, stage = 0, clk = 0, run = 0, load = 1;
    reg [2:0] requester = 4;
    reg page = 0, valid_page = 0, data_sink = 0, dq_sink = 0;
    integer mode = 0, count, file, samples, check, want, row, selector;
    reg [1023:0] path;
    wire spi = mode == 1;
    assign gp[7:0] = ui;
    assign gp[27] = clk;
    assign gp[28] = reset;
    assign gp[16] = run;
    assign gp[22] = load ? stage : 1'bz;
    pulldown (weak0) rest_stage(gp[22]);
    assign gp[17] = spi ? requester[0] : page;
    assign gp[18] = spi ? requester[1] : data_sink ? 1'b0 : 1'bz;
    assign gp[19] = spi ? requester[2] : dq_sink ? 1'b0 : 1'bz;
    assign gp[20] = spi ? 1'bz : valid_page;
    assign (pull1, highz0) gp[18] = spi ? 1'bz : 1'b1;
    assign (pull1, highz0) gp[19] = spi ? 1'bz : 1'b1;
    wire [7:0] status = gp[15:8];

    initial begin
        if (!$value$plusargs("mode=%d", mode) || !$value$plusargs("journal=%s", path))
            $fatal(1, "missing operating mode or cold journal");
        file = $fopen(path, "r");
        if (!file) $fatal(1, "open journal");
        while (!$feof(file)) begin
            count = $fscanf(file, "%h %h %h %h %h %h %h %h", reset, stage, ui, clk, check, want, row, selector);
            if (count == 8) begin
                #40;
                if (check) begin
                    if (spi && gp[20] !== 1'bz) $fatal(1, "FPGA drove MISO during cold read");
                    if (status !== want[7:0]) $fatal(1, "COLD_MISMATCH %0d %02x %02x %02x", row, selector, want, status);
                    $display("CHECK %0d %02x %02x", row, selector, status);
                end
            end else if (!$feof(file)) $fatal(1, "bad journal row");
        end
        $fclose(file);
        load = 0;
        if (mode == 23) dq_sink = 1;
        #40; clk = 1; #40; clk = 0; #40; clk = 1; #40; clk = 0;
        #40; run = 1;
        forever begin #40; clk = !clk; end
    end
    initial begin #4500000; $fatal(1, "bench timeout"); end

    // A byte-oriented target sees only SDA/SCL. A nonmatching address stays released.
    task automatic get_byte(input [7:0] expected);
        integer n;
        reg [7:0] seen;
        for (n = 0; n < 8; n = n + 1) begin @(posedge gp[19]); seen = {seen[6:0], gp[18]}; end
        if (seen !== expected) $fatal(1, "target expected %02x, saw %02x", expected, seen);
        @(negedge gp[19]); #10; data_sink = 1;
        @(negedge gp[19]); #10; data_sink = 0;
    endtask
    initial begin : i2c_responder
        integer i;
        @(posedge run);
        if (mode == 10) begin
            @(negedge gp[18]);
            get_byte(8'h5c);
            get_byte(8'h96);
            @(negedge gp[18]); // repeated START
            get_byte(8'h5d);
            for (i = 7; i >= 0; i = i - 1) begin
                data_sink = i != 0; // send 01, MSB first
                @(negedge gp[19]); #10;
            end
            data_sink = 0;
        end
    end
    initial begin : i2c_capture
        integer n, last, v;
        reg [7:0] terminal, byte_rx;
        @(posedge run);
        if (mode == 10 || mode == 11) begin
            last = -1;
            #2;
            for (n = 0; n < 24000; n = n + 1) begin
                v = {2'b0, gp[22], gp[21], 1'b0, gp[19], gp[18], 1'b0};
                if (v != last) $display("D %0d %0d", n, v);
                last = v;
                #100;
            end
            terminal = status; page = 1; #20; byte_rx = status;
            valid_page = 1; #20;
            $display("I2C %0d %0d %0d", terminal, byte_rx, status);
            $finish;
        end
    end
    // A programmable one-device model independently supplies presence and the final slot.
    initial begin : sensor
        integer n;
        @(posedge run);
        if (mode == 20 || mode == 21) begin
            @(negedge gp[19]); @(posedge gp[19]); #25000;
            dq_sink = 1; #96000; dq_sink = 0;
            for (n = 0; n < 17; n = n + 1) @(negedge gp[19]);
            if (mode == 21) begin #1000; dq_sink = 1; #30000; dq_sink = 0; end
        end
    end
    initial begin : sensor_capture
        integer n, last, v;
        @(posedge run);
        if (mode >= 20) begin
            last = -1;
            #2;
            for (n = 0; n < 15000; n = n + 1) begin
                v = {1'b0, gp[22], 2'b0, gp[19], 9'b0, gp[9], 1'b0};
                if (v != last) $display("D %0d %0d", n, v);
                last = v;
                #200;
            end
            $display("ONEWIRE %0d", status);
            $finish;
        end
    end
    initial begin : spi_driver
        integer input_file, t, value, ret, current;
        reg [1023:0] events;
        @(posedge run);
        if (spi) begin
            if (!$value$plusargs("events=%s", events)) $fatal(1, "no events");
            input_file = $fopen(events, "r");
            current = 0;
            while (!$feof(input_file)) begin
                ret = $fscanf(input_file, "%d %d", t, value);
                if (ret == 2) begin
                    #(8*(t-current)); requester = value[2:0]; current = t;
                end else if (!$feof(input_file)) $fatal(1, "bad SPI event");
            end
            $fclose(input_file);
        end
    end
    initial begin : spi_capture
        integer n, v, last, high_count, low_count, released_count;
        @(posedge run);
        if (spi) begin
            if (!$value$plusargs("samples=%d", samples)) $fatal(1, "no capture length");
            last = -1;
            high_count = 0; low_count = 0; released_count = 0;
            #2;
            for (n = 0; n < samples; n = n + 1) begin
                case ({gp[21], gp[20]})
                    2'b0z: released_count = released_count + 1;
                    2'b10: low_count = low_count + 1;
                    2'b11: high_count = high_count + 1;
                    default: $fatal(1, "MISO pad drive disagrees with enable");
                endcase
                // The original digital scorer reads MISO only when its enable is asserted.
                v = {1'b0, gp[26], gp[22:21], (gp[20] === 1'b1), gp[19:17]};
                if (v != last) $display("D %0d %0d", n, v);
                last = v;
                #8;
            end
            $display("SPI %0d %0d %0d %0d", status, released_count, low_count, high_count);
            $finish;
        end
    end
endmodule
`default_nettype wire
