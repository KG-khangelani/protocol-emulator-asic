`timescale 1ns/1ps
`default_nettype none
module target_tb;
    reg clk = 0, rst_n = 0, host_drive = 0, attached = 0, running = 0;
    reg [7:0] ui = 0, host_data = 0;
    reg [2:0] requester = 4;
    tri [7:0] pads;
    wire [7:0] chip_oe, chip_out, uo;
    assign (weak0,weak1) pads = 8'h00;
    assign pads = host_drive ? host_data : 8'bz;
    assign pads[2:0] = attached ? requester : 3'bz;
    for (genvar p = 0; p < 8; p = p + 1)
        assign pads[p] = chip_oe[p] ? chip_out[p] : 1'bz;
    tt_um_khangelani_protocol_emulator chip (.clk(clk), .rst_n(rst_n), .ena(1'b1),
        .ui_in(ui), .uo_out(uo), .uio_in(pads), .uio_out(chip_out), .uio_oe(chip_oe));

    integer start_ns, rows, fin, count, pf, ef, i, n, t, last_t, raw, rst, host, sel;
    integer data, want_oe, check_pad, want_pad, check_uo, want_uo, flush;
    string plan, events;
    task pins;
        $display("PIN %0d %02h %b %d %d", $time-start_ns, chip_oe, pads[3], pads[5:4], uo[7:6] == 2);
    endtask
    always @(chip_oe or pads[3] or pads[5:4] or uo[7:6]) if (running) begin
        #0;
        if ((chip_oe & 8'hc7) !== 0 || host_drive || ui !== 0 || uo[7:6] === 3)
            $fatal(1, "drive, service or VM fault during frame");
        pins;
    end
    initial begin
        if (!$value$plusargs("plan=%s",plan) || !$value$plusargs("events=%s",events)
            || !$value$plusargs("rows=%d",rows) || !$value$plusargs("count=%d",count)
            || !$value$plusargs("finish=%d",fin)) $fatal(1,"test arguments");
        #3;
        pf = $fopen(plan,"r");
        ef = $fopen(events,"r");
        if (!pf || !ef) $fatal(1,"test input unavailable");
        for (i = 0; i < rows; i = i + 1) begin
            n = $fscanf(pf,"%d %d %h %h %h %d %h %d %h %d",rst,host,sel,data,
                        want_oe,check_pad,want_pad,check_uo,want_uo,flush);
            if (n != 10) $fatal(1,"short cold plan");
            rst_n = rst;
            if (!host) begin host_drive = 0; #2; end
            ui = sel; #2;
            if (host) begin
                if (chip_oe !== 0 || attached) $fatal(1,"cold-load contention");
                host_data = data; #2; host_drive = 1; #2;
            end
            if (flush) begin
                if (chip_oe !== 0 || host_drive || ui != 8'he7) $fatal(1,"cold attach");
                attached = 1; #2;
            end
            #10 clk = 1; #10 clk = 0; #1;
            if (chip_oe !== want_oe[7:0] || (check_pad && pads !== want_pad[7:0])
                || (check_uo && uo !== want_uo[7:0])) $fatal(1,"readback at %0d",i);
        end
        $fclose(pf);
        ui = 8'h67; #2;
        if (chip_oe !== 0 || uo !== 8'h22) $fatal(1,"identity");
        ui = 0; #2;
        if (uo !== 8'h20 || pads[2:0] !== 4 || host_drive || !attached) $fatal(1,"launch");
        start_ns = $time; running = 1; last_t = 0;
        $display("LOAD %0d", rows);
        pins;
        fork
            begin forever #10 clk = ~clk; end
            begin
                for (i = 0; i < count; i = i + 1) begin
                    n = $fscanf(ef,"%d %d",t,raw);
                    if (n != 2 || t < last_t) $fatal(1,"bad requester schedule");
                    #(t-last_t); requester = raw; #0;
                    if (pads[2:0] !== requester) $fatal(1,"requester pin mismatch");
                    $display("IN %0d %0d",$time-start_ns,pads[2:0]);
                    last_t = t;
                end
                #(fin-last_t); $display("END %0d",$time-start_ns); $finish;
            end
        join
    end
endmodule
`default_nettype wire
