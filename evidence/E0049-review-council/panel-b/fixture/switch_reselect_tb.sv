`timescale 1ns/1ps
`default_nettype none

module switch_reselect_tb;
    localparam DIRECT = 0, BUFFER = 1, SWITCH = 2, DISARMED = 3;
    localparam NORMAL = 0, STOPPED_HIGH = 1, RETURN_IDLE = 2;
    reg clk, rst_n, mcu_drive, attached, sck, mosi, cs_n, peer_on, peer_value, permit;
    reg [7:0] ui, mcu_data;
    wire [7:0] chip_out, chip_oe, uo;
    tri [7:0] pads;
    tri shared_miso;
    integer mode, schedule, same_peer, start_time, abort_time;
    wire selected = attached && !cs_n && (mode != DISARMED || permit);
    wire pass = (mode == DIRECT && attached) || ((mode == SWITCH || mode == DISARMED) && selected);
    wire internal_drive = chip_oe[3];
    wire driving_branch = (mode == BUFFER && selected) || (pass && internal_drive);
    assign (weak0,weak1) pads[2:0] = 3'b000;
    assign (weak0,weak1) pads[7:4] = 4'b0000;
    assign (weak0,weak1) pads[3] = (!attached || mode == BUFFER) ? 1'b0 : 1'bz;
    assign (weak0,weak1) shared_miso = 1'b0;
    assign shared_miso = peer_on ? peer_value : 1'bz;
    tranif1 series_switch(shared_miso, pads[3], pass);
    bufif1 one_way(shared_miso, pads[3], (mode == BUFFER && selected));
    assign pads = mcu_drive ? mcu_data : 8'bz;
    assign pads[2:0] = attached ? {cs_n,mosi,sck} : 3'bz;
    for (genvar bitno=0; bitno<8; bitno=bitno+1) begin : chip_driver
        assign pads[bitno] = chip_oe[bitno] ? chip_out[bitno] : 1'bz;
    end
    tt_um_khangelani_protocol_emulator chip (.clk(clk), .rst_n(rst_n), .ena(1'b1),
        .ui_in(ui), .uo_out(uo), .uio_in(pads), .uio_out(chip_out), .uio_oe(chip_oe));

    task sample(input [8*28-1:0] tag);
        $display("SV %0s %0d %b %b %b %b %b %b %b %b %02h", tag, $time-start_time,
            cs_n, sck, internal_drive, chip_out[3], driving_branch, peer_on, peer_value,
            shared_miso, uo);
    endtask

    task frame(input [7:0] opcode, input integer first);
        integer i;
        begin : frame_body
            cs_n=0;
            for (i=0;i<16;i=i+1) begin
                mosi = i<8 ? opcode[7-i] : 1'b0;
                if (i==0) begin
                    #1;
                    sample(first ? "first_select" : "second_select");
                    if (first) begin
                        peer_on=1; peer_value=1; #1; sample("command_drive_control");
                        peer_on=0; #298;
                    end else begin
                        #299;
                    end
                end else begin
                    #250;
                end
                sck=1; #0;
                $display("EDGE %0d %0d %b %b %b %02h", first,i,internal_drive,driving_branch,shared_miso,uo);
                if (first && schedule != NORMAL && i==8) begin
                    #140;
                    cs_n=1; permit=0; peer_value=same_peer; peer_on=1;
                    abort_time=$time; #1; sample("abort_plus_1");
                    #79;
                    if (schedule==RETURN_IDLE) sck=0;
                    #79; sample("abort_plus_159");
                    #1; cs_n=0; #1; sample("reselect_with_peer");
                    peer_on=0;
                    if (schedule==STOPPED_HIGH) begin
                        #1800; sample("parked_end");
                        cs_n=1; #20;
                    end else begin
                        // The separate diagnostic consumed one ns. The second frame
                        // raises SCK 299 ns later, at reselect + 300 ns.
                        frame_second(opcode ^ 8'h01);
                    end
                    disable frame_body;
                end
                #250;
                sck=0; #0;
            end
            #300; cs_n=1; #200; sample("normal_end");
        end
    endtask

    task frame_second(input [7:0] opcode);
        integer i;
        begin
            for (i=0;i<16;i=i+1) begin
                mosi = (i<8) ? opcode[7-i] : 1'b0;
                if (i==0) #299; else #250;
                sck=1; #0;
                $display("EDGE 0 %0d %b %b %b %02h",i,internal_drive,driving_branch,shared_miso,uo);
                #250; sck=0;
            end
            #300; cs_n=1; #200; sample("second_end");
        end
    endtask

    integer fh, result, i, rst, host, sel, data, want_oe, ck_uio, val_uio, ck_uo, val_uo, flush;
    string plan;
    initial begin
        if (!$value$plusargs("mode=%d",mode) || !$value$plusargs("schedule=%d",schedule) ||
            !$value$plusargs("same_peer=%d",same_peer) || !$value$plusargs("plan=%s",plan))
            $fatal(1,"arguments");
        #1; clk=0; rst_n=0; mcu_drive=0; ui=0; mcu_data=0; attached=0;
        sck=0; mosi=0; cs_n=1; peer_on=0; peer_value=0; permit=0;
        #2; fh=$fopen(plan,"r"); if (!fh) $fatal(1,"plan missing");
        for (i=0;i<498;i=i+1) begin
            result=$fscanf(fh,"%d %d %h %h %h %d %h %d %h %d",rst,host,sel,data,want_oe,
                ck_uio,val_uio,ck_uo,val_uo,flush);
            if(result!=10) $fatal(1,"short plan");
            rst_n=rst;
            if(!host) begin mcu_drive=0; #2; end
            ui=sel; #2;
            if(host) begin
                if(chip_oe!==0 || attached) $fatal(1,"unsafe loader write");
                mcu_data=data; #2; mcu_drive=1; #2;
            end
            if(flush) begin
                if(chip_oe!==0 || mcu_drive || ui!=8'he7) $fatal(1,"unsafe attach");
                attached=1; #2;
            end
            #10 clk=1; #10 clk=0; #1;
            if(chip_oe!==want_oe[7:0] || (ck_uio && pads!==val_uio[7:0]) ||
                (ck_uo && uo!==val_uo[7:0])) $fatal(1,"loader/readback row %0d",i);
        end
        $fclose(fh); ui=8'h67; #2;
        if(chip_oe!==0 || uo!==8'h22) $fatal(1,"handoff identity");
        ui=0; #2;
        if(uo!==8'h20 || pads[2:0]!==3'b100) $fatal(1,"launch");
        start_time=$time; permit=1;
        fork
            begin forever #10 clk=~clk; end
            begin #207; frame(8'ha5,1); #2400; sample("terminal"); $finish; end
        join
    end
endmodule
`default_nettype wire
