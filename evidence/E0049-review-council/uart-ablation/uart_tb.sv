// SPDX-License-Identifier: Apache-2.0
`timescale 1ps/1ps
`default_nettype none

module uart_tb;
    reg clk = 0;
    reg rst_n, ena, host_drives, peer_drives, peer_level;
    reg [7:0] ui, host_value;
    wire [7:0] uo, chip_value, chip_oe;
    tri [7:0] pins;
    assign pins = host_drives ? host_value : 8'bz;
    assign pins[1] = peer_drives ? peer_level : 1'bz;
    genvar bit_index;
    generate for (bit_index=0; bit_index<8; bit_index=bit_index+1) begin : pad
        assign pins[bit_index] = chip_oe[bit_index] ? chip_value[bit_index] : 1'bz;
        pulldown(pins[bit_index]);
    end endgenerate
    tt_um_khangelani_protocol_emulator dut (
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui), .uo_out(uo),
        .uio_in(pins), .uio_out(chip_value), .uio_oe(chip_oe)
    );

    integer first, second, phase, bad, witness, period, receive_mode, manual;
    integer index, rp, fp, steps, fields, n, event_edge, last_edge, extra_edges;
    integer capture1, capture2, first_data, expected_dir, expected_val;
    integer expected_raw, expected_valid, expected_terminal, final_pc;
    integer previous_trace;
    reg [7:0] status, raw, valid, expected_oe, expected_uio, expected_uo;
    integer want_uio, want_uo, dynamic_tx;
    string plan, cases;

    function automatic integer frame_bit(input integer position, input integer octet,
                                          input integer stop_level);
        if (position == 0) frame_bit = 0;
        else if (position == 9) frame_bit = stop_level;
        else frame_bit = (octet >> (position-1)) & 1;
    endfunction

    function automatic integer target(input integer quarter);
        integer cell_number;
        begin
            if (quarter < 16+phase || bad == 3) target = 1;
            else begin
                cell_number = (quarter-16-phase)/(4*period);
                if (cell_number < 10) target = frame_bit(cell_number, first, bad != 1);
                else if (cell_number < 20) target = frame_bit(cell_number-10, second, bad != 2);
                else target = 1;
            end
        end
    endfunction

    function automatic integer tx_level(input integer edge_no);
        integer cell_number;
        begin
            if (edge_no < 3 || edge_no >= 3+20*period) tx_level = 1;
            else begin
                cell_number = (edge_no-3)/period;
                tx_level = frame_bit(cell_number%10, cell_number < 10 ? first : second, 1);
            end
        end
    endfunction

    task mismatch(input string reason, input integer observed, input integer expected);
        begin
            $display("MISMATCH %s case=%0d edge=%0d observed=%0h expected=%0h", reason,
                     index, n, observed, expected);
            $finish;
        end
    endtask

    task load_image;
        integer row;
        begin
            rp = $fopen(plan, "r");
            if (!rp) $fatal(1, "cannot open plan");
            peer_drives = 0;
            for (row=0; row<steps; row=row+1) begin
                fields = $fscanf(rp, "%d %d %d %h %h %h %d %h %d %h %d",
                    rst_n, ena, host_drives, ui, host_value, expected_oe, want_uio,
                    expected_uio, want_uo, expected_uo, dynamic_tx);
                if (fields != 11) $fatal(1, "invalid plan row");
                if (dynamic_tx != 0 && !receive_mode) begin
                    if (host_drives) host_value = dynamic_tx == 1 ? first : second;
                    else expected_uio = dynamic_tx == 1 ? first : second;
                end
                peer_drives = row >= steps-2;
                peer_level = receive_mode;
                #9000 clk=0;
                #10000 clk=1;
                #1000;
                if (chip_oe !== expected_oe || (want_uio && pins !== expected_uio) ||
                        (want_uo && uo !== expected_uo)) $fatal(1, "loader mismatch row %d", row);
            end
            $fclose(rp);
        end
    endtask

    initial begin
        if (!$value$plusargs("plan=%s",plan) || !$value$plusargs("steps=%d",steps) ||
                !$value$plusargs("cases=%s",cases) || !$value$plusargs("period=%d",period) ||
                !$value$plusargs("rx=%d",receive_mode) || !$value$plusargs("manual=%d",manual))
            $fatal(1, "missing arguments");
        fp = $fopen(cases, "r");
        if (!fp) $fatal(1, "cannot open cases");
        index = 0;
        while ($fscanf(fp, "%d %d %d %d %d", first, second, phase, bad, witness) == 5) begin
            load_image;
            rst_n = 1; ena = 1; ui = 0; host_drives = 0;
            peer_drives = receive_mode; peer_level = receive_mode;
            event_edge = (16+phase+3)/4+2;
            first_data = event_edge+3*period/2;
            capture1 = receive_mode ? event_edge+17*period/2 : 3+8*period;
            capture2 = capture1+10*period;
            if (!receive_mode) last_edge = 3+20*period;
            else if (bad == 3) last_edge = 2+2*period;
            else if (bad != 0) last_edge = event_edge+19*period/2+(bad-1)*10*period;
            else last_edge = event_edge+39*period/2+1;
            final_pc = !bad ? (manual ? (receive_mode ? 17 : 16) : 7) :
                       (bad == 3 ? 1 : (manual ? 8*bad : 6));
            expected_terminal = (bad ? 'he0 : 'ha0) | final_pc;
            extra_edges = witness ? period+1 : 0;
            previous_trace = -1;
            for (n=1; n<=last_edge+extra_edges; n=n+1) begin
                #3999 peer_level = receive_mode && target(4*n-3);
                #5000 clk=0; peer_level = receive_mode && target(4*n-2);
                #5000 peer_level = receive_mode && target(4*n-1);
                #5000 peer_level = receive_mode && target(4*n);
                #1 clk=1;
                #200 status=uo; ui='h62;
                #200 raw=uo; ui='h63;
                #200 valid=uo; ui=0;
                #400;
                expected_dir = !receive_mode || (n>=first_data && bad!=3);
                expected_val = receive_mode ? expected_dir : tx_level(n);
                expected_valid = n>=capture1 && bad!=3;
                expected_raw = !receive_mode || !expected_valid ? 0 :
                               (n>=capture2 && bad!=1 ? second : first);
                if (chip_oe !== expected_dir) mismatch("direction", chip_oe, expected_dir);
                if (chip_value !== expected_val) mismatch("wire", chip_value, expected_val);
                if (raw !== expected_raw) mismatch("raw", raw, expected_raw);
                if (valid !== expected_valid) mismatch("valid", valid, expected_valid);
                if (n < last_edge && status[5] !== 1) mismatch("ready", status, 'h20);
                if (n < last_edge && !(status[7] === 0)) mismatch("early_terminal", status, 0);
                if (n >= last_edge && status !== expected_terminal)
                    mismatch("terminal", status, expected_terminal);
                // The released reader uses ready, state, terminal signature, valid and data.
                // Suppress only redundant observations at witness edges.
                if (witness && previous_trace != {status,valid,raw}) begin
                    $display("OBS %0d %0d %0d %0d %0d", index,n,status,valid,raw);
                    previous_trace = {status,valid,raw};
                end
            end
            $display("CASE %0d %0d %0d %0d %0d %0d %0d %0d",
                     index,first,second,phase,bad,last_edge,status,n-1);
            index=index+1;
        end
        $display("DONE %0d",index);
        $finish;
    end
endmodule
`default_nettype wire
