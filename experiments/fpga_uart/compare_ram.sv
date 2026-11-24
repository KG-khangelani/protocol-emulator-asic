// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`default_nettype none
module compare_ram;
    reg A_CLK = 0, A_MEN = 0, A_WEN = 0, A_REN = 0;
    reg [7:0] A_ADDR = 0;
    reg [31:0] A_DIN = 0, A_BM = 0;
    wire A_DLY = 1, A_BIST_CLK = 0, A_BIST_EN = 0, A_BIST_MEN = 0;
    wire A_BIST_WEN = 0, A_BIST_REN = 0;
    wire [7:0] A_BIST_ADDR = 0;
    wire [31:0] A_BIST_DIN = 0, A_BIST_BM = 0;
    wire [31:0] vendor, fpga;
    reg [31:0] expected [0:255];
    reg [31:0] held;
    integer checks = 0, addr, mask;

    vendor_reference reference_model (.A_DOUT(vendor), .*);
    RM_IHPSG13_1P_256x32_c2_bm_bist fpga_model (.A_DOUT(fpga), .*);

    task check_edge(input bit men, wen, ren, input reg [3:0] lanes,
                    input reg [7:0] address, input reg [31:0] data);
        begin
            A_MEN = men; A_WEN = wen; A_REN = ren; A_ADDR = address; A_DIN = data;
            A_BM = {{8{lanes[3]}}, {8{lanes[2]}}, {8{lanes[1]}}, {8{lanes[0]}}};
            if (men && wen)
                expected[address] = (expected[address] & ~A_BM) | (data & A_BM);
            if (men && ren)
                held = expected[address];
            #5; A_CLK = 1; #4;
            if ((fpga !== held) || (vendor !== held))
                $fatal(1, "RAM_MISMATCH check=%0d address=%0d mask=%h expected=%h vendor=%h fpga=%h",
                       checks+1, address, lanes, held, vendor, fpga);
            A_CLK = 0; #1;
            checks = checks + 1;
        end
    endtask

    initial begin
        for (addr = 0; addr < 256; addr = addr+1)
            check_edge(1, 1, 1, 15, addr, 32'h81d35a26 ^ (32'h0103070b * addr));
        for (mask = 0; mask < 16; mask = mask+1)
            for (addr = 0; addr < 256; addr = addr+1) begin
                check_edge(1, 1, 1, mask, addr, 32'h73428ce5 * (mask+1) ^ (32'h03110d25 * addr));
                check_edge(0, 1, 1, 15, addr+1, ~A_DIN);
                check_edge(1, 1, 0, mask, addr, ~A_DIN);
                check_edge(1, 0, 1, 0, addr, 0);
            end
        $display("PASS_RAM checks=%0d", checks);
        $finish;
    end
endmodule
`default_nettype wire
