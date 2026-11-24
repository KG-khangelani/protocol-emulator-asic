`timescale 1ns/1ps
`default_nettype none

module selector_order_tb;
    reg clk = 0;
    reg rst_n;
    reg [7:0] ui, host_data;
    reg host_drive, peer_drive, peer_level;
    wire [7:0] pads, result, out_value, oe;
    genvar pin;
    for (pin = 0; pin < 8; pin = pin + 1) begin : shared_pin
        assign pads[pin] = oe[pin] ? out_value[pin] : 1'bz;
    end
    assign (weak0, weak1) pads = 8'h03;
    assign pads = host_drive ? host_data : 8'bz;
    assign pads[6] = peer_drive ? peer_level : 1'bz;
    tt_um_khangelani_protocol_emulator chip (
        .clk(clk), .rst_n(rst_n), .ena(1'b1), .ui_in(ui), .uo_out(result),
        .uio_in(pads), .uio_out(out_value), .uio_oe(oe)
    );

    task tick;
        begin
            #10 clk = 1;
            #10 clk = 0;
        end
    endtask

    task write_byte(input [7:0] select_value, input [7:0] data);
        begin
            ui = select_value;
            #2;
            if (oe !== 0) $fatal(1, "write selector drove");
            host_data = data;
            host_drive = 1;
            tick();
            host_drive = 0;
            #2;
        end
    endtask

    task park(input integer mode);
        begin
            peer_drive = 0;
            #2 ui = 8'h67;
            #2 ui = 8'he7;
            #2;
            if (oe !== 0 || result !== 8'h20) $fatal(1, "failed to park");
            peer_level = mode == 1;
            peer_drive = mode != 0;
            #2;
        end
    endtask

    task observe(input integer ordinal, input integer mode, input integer progress);
        begin
            #2;
            $display("P %0d %0d %0d %02h %02h %02h %b %b %b",
                     ordinal, mode, progress, ui, oe, result, pads[6], pads[0], out_value[6]);
        end
    endtask

    reg [23:0] orders [0:719];
    reg [4095:0] order_file;
    integer trial, mode, item, bit_number;
    initial begin
        if (!$value$plusargs("ORDERS=%s", order_file)) $fatal(1, "missing order file");
        $readmemh(order_file, orders);
        #1 rst_n = 0; ui = 0; host_data = 0; host_drive = 0; peer_drive = 0; peer_level = 0;
        tick();
        rst_n = 1; ui = 8'h67;
        #2;
        if (result !== 8'h22) $fatal(1, "wrong interface");
        write_byte(8'he5, 0);
        for (item = 0; item < 4; item = item + 1)
            write_byte(8'hc0 + item, item == 3 ? 8'h80 : 0);
        for (item = 0; item < 4; item = item + 1) begin
            ui = 8'h80 + item;
            tick();
            if (oe !== 8'hff || pads !== (item == 3 ? 8'h80 : 8'h00))
                $fatal(1, "incorrect test image readback");
        end
        write_byte(8'he0, 1);
        ui = 8'he7;
        tick(); tick();
        if (oe !== 0 || result !== 8'h20) $fatal(1, "wrong flush state");
        for (trial = 0; trial < 720; trial = trial + 1) begin
            for (mode = 0; mode < 3; mode = mode + 1) begin
                park(mode);
                for (item = 0; item < 6; item = item + 1) begin
                    bit_number = orders[trial][item * 4 +: 4];
                    ui = ui & ~(8'h01 << bit_number);
                    observe(trial, mode, item);
                end
            end
        end
        for (mode = 0; mode < 3; mode = mode + 1) begin
            park(mode);
            ui = 8'h67;
            observe(720, mode, 0);
            ui = 8'h00;
            observe(720, mode, 1);
        end
        if (clk !== 0) $fatal(1, "clock did not remain parked");
        $finish;
    end
endmodule

`default_nettype wire
