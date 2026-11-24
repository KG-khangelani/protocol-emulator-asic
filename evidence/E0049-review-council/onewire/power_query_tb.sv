// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none

module power_query_tb;
    reg clk = 0;
    reg rst_n, ena;
    reg [7:0] ui, host_value;
    reg host_drives = 0;
    reg target_low = 0;
    wire [7:0] uo, chip_value, chip_oe;
    tri [7:0] pins;
    assign pins = host_drives ? host_value : 8'bz;
    assign pins[0] = target_low ? 1'b0 : 1'bz;
    pullup(pins[0]);
    genvar pin;
    generate
        for (pin = 0; pin < 8; pin = pin + 1) begin : io_cell
            assign pins[pin] = chip_oe[pin] ? chip_value[pin] : 1'bz;
            if (pin > 0) pulldown(pins[pin]);
        end
    endgenerate
    tt_um_khangelani_protocol_emulator dut (
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui), .uo_out(uo),
        .uio_in(pins), .uio_out(chip_value), .uio_oe(chip_oe)
    );

    // Return one nanosecond after each rising edge. The interval is 20 ns.
    task tick;
        begin
            #9 clk = 0;
            #10 clk = 1;
            #1;
        end
    endtask

    string plan_path;
    integer file, records, step, fields;
    integer check_pins, check_uo;
    reg [7:0] expected_oe, expected_pins, expected_uo;
    integer start_us, width_us, stuck, parasite;
    integer n, pulse, pulse_start, reset_release, age;
    reg previous_drive;
    reg [15:0] received_commands;

    initial begin
        if (!$value$plusargs("plan=%s", plan_path) ||
            !$value$plusargs("steps=%d", records) ||
            !$value$plusargs("delay=%d", start_us) ||
            !$value$plusargs("width=%d", width_us) ||
            !$value$plusargs("stuck=%d", stuck) ||
            !$value$plusargs("parasite=%d", parasite)) $fatal(1, "missing fixture arguments");
        file = $fopen(plan_path, "r");
        if (file == 0) $fatal(1, "could not open plan");
        for (step = 0; step < records; step = step + 1) begin
            fields = $fscanf(file, "%d %d %d %h %h %h %d %h %d %h",
                rst_n, ena, host_drives, ui, host_value, expected_oe,
                check_pins, expected_pins, check_uo, expected_uo);
            if (fields != 10) $fatal(1, "malformed loader row %d", step);
            tick;
            if (chip_oe !== expected_oe ||
                (check_pins != 0 && pins !== expected_pins) ||
                (check_uo != 0 && uo !== expected_uo))
                $fatal(1, "loader row %d oe=%h pins=%h uo=%h", step,chip_oe,pins,uo);
        end
        $fclose(file);
        $display("LOAD %0d", records);
        rst_n = 1;
        ena = 1;
        ui = 0;
        host_drives = 0;
        previous_drive = 0;
        pulse = -1;
        pulse_start = -1;
        reset_release = -1;
        received_commands = 0;

        for (n = 1; n <= 125000; n = n + 1) begin
            tick;
            if ((chip_oe[0] !== 0 && chip_oe[0] !== 1) ||
                (chip_oe[0] && chip_value[0] !== 0)) $fatal(1, "DQ drive violation at %d", n);
            if (chip_oe[0] != previous_drive) begin
                $display("DRIVE %0d %0d", n, chip_oe[0]);
                if (chip_oe[0]) begin
                    pulse = pulse + 1;
                    pulse_start = n;
                end else if (pulse == 0) reset_release = n;
                previous_drive = chip_oe[0];
            end

            // Device input uses the resolved bus at 30 us in each write slot.
            if (pulse >= 1 && pulse <= 16 && n - pulse_start == 1500) begin
                received_commands[pulse - 1] = pins[0];
                $display("WIREBIT %0d %0b", pulse - 1, pins[0]);
            end

            // Changes follow the observed DUT edge, then hold through the next sample.
            if (reset_release >= 0 && pulse == 0) begin
                age = n - reset_release;
                target_low = stuck != 0 ||
                    (age >= start_us * 50 && age < (start_us + width_us) * 50);
            end else if (pulse == 17 && received_commands === 16'hb4cc) begin
                age = n - pulse_start;
                target_low = parasite != 0 && age >= 500 && age < 2250;
            end else target_low = 0;

            if (uo[7:6] === 2'b11) $fatal(1, "FAULT at %d", n);
            if (uo[7:6] === 2'b10) begin
                if (uo[5] !== 1 || chip_oe[2:0] !== 3'b110)
                    $fatal(1, "bad terminal direction/status at %d", n);
                $display("HALT %0d %0d", n, pins[2:1]);
                $finish;
            end
        end
        $fatal(1, "runtime cap exceeded");
    end
endmodule
`default_nettype wire
