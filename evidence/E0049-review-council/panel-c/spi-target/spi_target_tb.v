`timescale 1ns/1ps
`default_nettype none

module spi_target_tb;
    reg clk, rst_n, mcu_drive, attached, sck, mosi, cs_n;
    reg [7:0] ui, mcu_data;
    wire [7:0] chip_out, chip_oe, uo;
    tri [7:0] pads;
    assign (weak0,weak1) pads = 8'h00;
    assign pads = mcu_drive ? mcu_data : 8'bz;
    assign pads[2:0] = attached ? {cs_n,mosi,sck} : 3'bz;
    genvar p;
    for (p=0;p<8;p=p+1) begin : pins
        assign pads[p] = chip_oe[p] ? chip_out[p] : 1'bz;
    end
    tt_um_khangelani_protocol_emulator chip (.clk(clk),.rst_n(rst_n),.ena(1'b1),
        .ui_in(ui),.uo_out(uo),.uio_in(pads),.uio_out(chip_out),.uio_oe(chip_oe));

    integer runtime=0, shown_terminal=0, idx, opcode, phase, half, kind;
    integer fh, result, rows, i, rst, drive, sel, data, want_oe, ck_uio, val_uio, ck_uo, val_uo, flush;
    integer low_ns,high_ns,launch;
    string plan;

    always @(chip_out or chip_oe) begin
        if (runtime) begin
            $display("O %0d %02h %02h",$time-launch,chip_oe,chip_out);
            if ((chip_oe & 8'hc7) !== 0) $fatal(1,"target drove requester or reserved pin");
        end
    end
    always @(posedge clk) begin
        if (runtime) begin
            #1;
            if (uo[7:6] == 3) $fatal(1,"VM FAULT");
            if (uo[7:6] == 2 && !shown_terminal) begin
                shown_terminal=1;
                $display("TERM %0d %0d %02h",$time-launch,pads[5:4],uo);
            end
            if (ui !== 0 || mcu_drive || !attached) $fatal(1,"loader intervention after launch");
        end
    end

    task release_cs;
        begin cs_n=1; #0; $display("CS %0d 1",$time-launch); end
    endtask

    task request;
        begin : transaction
            #(200+phase);
            cs_n=0;
            $display("CS %0d 0",$time-launch);
            for (idx=0;idx<16;idx=idx+1) begin
                mosi=(idx<8) ? ((opcode >> (7-idx)) & 1) : ((8'h69 >> (15-idx)) & 1);
                low_ns=half; high_ns=half;
                if (kind==5) begin
                    low_ns=250+((idx*3+1)%13)*50;
                    high_ns=250+((idx*5+2)%13)*50;
                end
                if (idx==0) low_ns=(kind==2) ? 3000 : 300;
                #(low_ns);
                sck=1; #0;
                $display("R %0d %0d %0d %02h %02h",$time-launch,idx,mosi,chip_oe,pads);
                if (kind==4 && idx==8) begin
                    #140;
                    release_cs;
                    #2600;
                    disable transaction;
                end
                if (kind==3 && idx==3) begin
                    #140;
                    release_cs;
                    #(high_ns-140);
                end else #(high_ns);
                sck=0; #0;
                $display("F %0d %0d",$time-launch,idx);
                if (kind==1 && idx==3) begin
                    $display("MISSING %0d",$time-launch);
                    #3000;
                end
            end
            #300;
            if (!cs_n) release_cs;
            #2600;
        end
    endtask

    initial begin
        if (!$value$plusargs("plan=%s",plan) || !$value$plusargs("rows=%d",rows) ||
            !$value$plusargs("opcode=%d",opcode) || !$value$plusargs("phase=%d",phase) ||
            !$value$plusargs("half=%d",half) || !$value$plusargs("kind=%d",kind)) $fatal(1,"arguments");
        #1;
        clk=0; rst_n=0; ui=0; mcu_drive=0; mcu_data=0; attached=0; sck=0; mosi=0; cs_n=1;
        #2;
        fh=$fopen(plan,"r");
        if (!fh) $fatal(1,"no plan");
        for (i=0;i<rows;i=i+1) begin
            result=$fscanf(fh,"%d %d %h %h %h %d %h %d %h %d",rst,drive,sel,data,want_oe,
                ck_uio,val_uio,ck_uo,val_uo,flush);
            if (result!=10) $fatal(1,"plan records");
            rst_n=rst; 
            if (!drive) begin mcu_drive=0; #2; end
            ui=sel; #2;
            if (drive) begin
                if (chip_oe!==0 || attached) $fatal(1,"contended write");
                mcu_data=data; #2; mcu_drive=1; #2;
            end
            if (flush) begin
                if (chip_oe!==0 || mcu_drive || ui!=8'he7) $fatal(1,"unsafe attach");
                attached=1; #2;
            end
            #10 clk=1; #10 clk=0; #1;
            if (chip_oe !== want_oe[7:0] || (ck_uio && pads !== val_uio[7:0]) ||
                (ck_uo && uo !== val_uo[7:0])) $fatal(1,"load/readback mismatch at %0d",i);
        end
        $fclose(fh);
        ui=8'h67; #2;
        if (chip_oe!==0 || uo!==8'h22) $fatal(1,"handoff");
        ui=0; #2;
        if (uo!==8'h20 || pads[2:0]!==3'b100 || !attached || mcu_drive) $fatal(1,"launch");
        launch=$time; runtime=1;
        $display("LOAD %0d",rows);
        $display("O 0 %02h %02h",chip_oe,chip_out);
        fork
            begin forever #10 clk=~clk; end
            begin
                request;
                $display("END %0d %02h %02h %02h",$time-launch,uo,chip_oe,pads);
                $finish;
            end
        join
    end
endmodule
`default_nettype wire
