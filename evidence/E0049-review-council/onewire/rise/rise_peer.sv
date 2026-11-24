// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none
module rise_peer;
    reg clk=0, rst_n, ena;
    reg [7:0] ui, host_data;
    reg host_drives=0, controller_senses_low=0;
    wire [7:0] uo, chip_data, chip_oe;
    tri [7:0] pins;
    assign pins=host_drives ? host_data : 8'bz;
    genvar i;
    generate for (i=0; i<8; i=i+1) begin : pad
        assign pins[i]=chip_oe[i] ? chip_data[i] : 1'bz;
        if (i>0) pulldown(pins[i]);
    end endgenerate
    pullup(pins[0]);
    // The controller's input comparator can still read low once all drivers release.
    assign pins[0]=controller_senses_low ? 1'b0 : 1'bz;
    tt_um_khangelani_protocol_emulator dut(.clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui),
        .uo_out(uo),.uio_in(pins),.uio_out(chip_data),.uio_oe(chip_oe));

    task tick;
        begin #9 clk=0; #10 clk=1; #1; end
    endtask
    string plan;
    integer steps,remote_rise,local_rise,presence_delay,presence_width,sample_age,parasite;
    integer fp,step,fields,want_pins,want_uo,n,pulse,last_fall,reset_release,last_release;
    integer presence_start,presence_end,samples,peer_slots,peer_fall,high_since,min_recovery;
    reg [7:0] expected_oe,expected_pins,expected_uo;
    reg prev_controller_low,prev_any_low,any_low,slave_low,peer_high,prev_peer_high;
    reg [15:0] received;

    initial begin
        if (!$value$plusargs("plan=%s",plan) || !$value$plusargs("steps=%d",steps) ||
            !$value$plusargs("remote=%d",remote_rise) || !$value$plusargs("local=%d",local_rise) ||
            !$value$plusargs("delay=%d",presence_delay) || !$value$plusargs("width=%d",presence_width) ||
            !$value$plusargs("sample=%d",sample_age) || !$value$plusargs("parasite=%d",parasite))
            $fatal(1,"missing fixture arguments");
        fp=$fopen(plan,"r");
        if (!fp) $fatal(1,"could not open public plan");
        for(step=0;step<steps;step=step+1) begin
            fields=$fscanf(fp,"%d %d %d %h %h %h %d %h %d %h",rst_n,ena,host_drives,ui,host_data,
                expected_oe,want_pins,expected_pins,want_uo,expected_uo);
            if(fields!=10) $fatal(1,"malformed load plan");
            tick;
            if(chip_oe!==expected_oe || (want_pins && pins!==expected_pins) ||
                (want_uo && uo!==expected_uo)) $fatal(1,"loader row %0d",step);
        end
        $fclose(fp);
        rst_n=1; ena=1; ui=0; host_drives=0;
        pulse=-1; last_fall=-1; reset_release=-1; last_release=-100000;
        presence_start=-1; presence_end=-1; samples=0; received=0;
        peer_slots=0; peer_fall=-100000; high_since=-100000; min_recovery=100000;
        prev_controller_low=0; prev_any_low=0; prev_peer_high=1;
        for(n=1;n<=125000;n=n+1) begin
            tick;
            if (chip_oe[0]===1'bx || (chip_oe[0] && chip_data[0]!==0)) $fatal(1,"invalid DQ drive");
            if (chip_oe[0]!=prev_controller_low) begin
                $display("DRIVE %0d %0d",n,chip_oe[0]);
                if (chip_oe[0]) begin pulse=pulse+1; last_fall=n; end
                else if (pulse==0) begin
                    reset_release=n;
                    presence_start=n+remote_rise+presence_delay;
                    presence_end=presence_start+presence_width;
                end
                prev_controller_low=chip_oe[0];
            end
            slave_low=(pulse==0 && reset_release>=0 && n>=presence_start && n<presence_end) ||
                (peer_slots==17 && received===16'hb4cc && parasite && n-peer_fall>=500 && n-peer_fall<2250);
            any_low=chip_oe[0] || slave_low;
            if (prev_any_low && !any_low) last_release=n;
            prev_any_low=any_low;
            peer_high=!any_low && (n-last_release>=remote_rise);
            controller_senses_low=any_low || (n-last_release<local_rise);
            if (peer_high && !prev_peer_high) high_since=n;
            // A new command slot exists for the device only after its own input has risen.
            if (!peer_high && prev_peer_high && pulse>=1 && chip_oe[0]) begin
                if (peer_slots>0 && n-high_since<min_recovery) min_recovery=n-high_since;
                peer_slots=peer_slots+1;
                peer_fall=n;
            end
            prev_peer_high=peer_high;
            if (peer_slots>=1 && peer_slots<=16 && n-peer_fall==sample_age) begin
                received[peer_slots-1]=peer_high; samples=samples+1;
            end
            if (uo[7:6]===2'b11) $fatal(1,"VM fault at %0d",n);
            if (uo[7:6]===2'b10) begin
                if (uo[5]!==1 || chip_oe[2:0]!==3'b110) $fatal(1,"terminal direction");
                $display("RESULT %0d %0d %04x %0d %0d %0d %0d %0d",n,pins[2:1],received,samples,
                         presence_start-reset_release,presence_end-reset_release,peer_slots,min_recovery);
                $finish;
            end
        end
        $fatal(1,"execution exceeded cap");
    end
endmodule
`default_nettype wire
