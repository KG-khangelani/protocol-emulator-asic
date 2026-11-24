// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none
module spi_trace_tb;
    reg clk = 0;
    always #10 clk = ~clk;
    reg rst_n, ena, host_drive, target_attached;
    reg [7:0] ui, external_value;
    wire [7:0] uo, out_byte, oe;
    tri [7:0] pins;
    assign pins = host_drive ? external_value : 8'hzz;
    assign pins[1] = target_attached ? external_value[1] : 1'bz;
    genvar i;
    for (i = 0; i < 8; i = i + 1) begin
        assign pins[i] = oe[i] ? out_byte[i] : 1'bz;
        if (i == 3) pullup(pins[i]);
        else pulldown(pins[i]);
    end
    tt_um_khangelani_protocol_emulator dut(
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui), .uo_out(uo),
        .uio_in(pins), .uio_out(out_byte), .uio_oe(oe)
    );
    integer stimulus, observations, count, ok;
    reg [20:0] command;
    reg [7:0] status, raw, valid_byte, saved_pins, saved_out, saved_oe;
    initial begin
        stimulus = $fopen("stimulus.hex", "r");
        observations = $fopen("observed.txt", "w");
        if (!stimulus || !observations) $fatal(1, "io open failed");
        count = 0;
        #1;
        while (!$feof(stimulus)) begin
            ok = $fscanf(stimulus, "%h\n", command);
            if (ok == 1) begin
                {rst_n, ena, target_attached, host_drive, external_value, ui} = command[19:0];
                @(posedge clk); #1;
                status = uo; saved_pins = pins; saved_out = out_byte; saved_oe = oe;
                if (host_drive && oe !== 0) $fatal(1, "loader contention at %0d", count);
                raw = 0; valid_byte = 0;
                if (command[20]) begin
                    ui = 8'h62; #1; raw = uo;
                    ui = 8'h63; #1; valid_byte = uo;
                    if (pins !== saved_pins || out_byte !== saved_out || oe !== saved_oe)
                        $fatal(1, "runtime selectors changed pin ownership");
                end
                $fdisplay(observations, "%02x %02x %02x %02x %02x %02x",
                          status, saved_out, saved_oe, saved_pins, raw, valid_byte);
                count = count + 1;
            end
        end
        $fclose(observations);
        $fclose(stimulus);
        $display("Observed %0d public edges", count);
        $finish;
    end
endmodule
`default_nettype wire
