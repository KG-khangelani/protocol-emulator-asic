`timescale 1ns/1ps
`default_nettype none

module powered_host_tb;
    reg clk = 0;
    reg rst_n;
    reg ena;
    reg [7:0] ui_in;
    reg [7:0] host_data;
    reg host_drive;
    reg [7:0] bias;
    wire [7:0] pads, uo_out, uio_out, uio_oe;
    assign (weak0, weak1) pads = bias;
    assign pads = host_drive ? host_data : 8'bz;
    genvar bit_index;
    for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin : shared_pin
        assign pads[bit_index] = uio_oe[bit_index] ? uio_out[bit_index] : 1'bz;
    end

    tt_um_khangelani_protocol_emulator chip (
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui_in), .uo_out(uo_out),
        .uio_in(pads), .uio_out(uio_out), .uio_oe(uio_oe)
    );

    integer file_id, fields, edge_number = 0;
    reg [4095:0] stimulus;
    initial begin
        #1;
        if (!$value$plusargs("STIMULUS=%s", stimulus)) $fatal(1, "missing stimulus");
        file_id = $fopen(stimulus, "r");
        if (file_id == 0) $fatal(1, "unreadable stimulus");
        while (!$feof(file_id)) begin
            fields = $fscanf(file_id, "%h %h %h %h %h %h\n", rst_n, ena, ui_in,
                             host_drive, host_data, bias);
            if (fields == 6) begin
                #10 clk = 1;
                #1 $display("EDGE %0d %02h %02h %02h", edge_number, uo_out, uio_oe, pads);
                #9 clk = 0;
                edge_number = edge_number + 1;
            end else if (!$feof(file_id)) begin
                $fatal(1, "malformed stimulus");
            end
        end
        $fclose(file_id);
        $finish;
    end
endmodule

`default_nettype wire
