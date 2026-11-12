// SPDX-License-Identifier: Apache-2.0
`default_nettype none
module reference_store (
    input wire clk, rst_n, ena, load_mode, load_write, load_length, load_bank,
    input wire [4:0] byte_address, input wire [7:0] data_in, pc,
    output reg [7:0] data_out, program_length, output reg program_ready,
    output reg [3:0] program_bank, output reg [31:0] instruction,
    output wire instruction_valid
);
    reg [31:0] memory [0:127];
    integer index;
    wire [7:0] address = {program_bank, byte_address[4:2]};
    wire accepted_length = data_in != 0 && {1'b0, data_in} <= 9'd128;
    (* keep *) wire [31:0] word0 = memory[0];
    (* keep *) wire [31:0] word1 = memory[1];
    (* keep *) wire [31:0] word2 = memory[2];
    (* keep *) wire [31:0] word3 = memory[3];
    (* keep *) wire [31:0] word4 = memory[4];
    (* keep *) wire [31:0] word5 = memory[5];
    (* keep *) wire [31:0] word6 = memory[6];
    (* keep *) wire [31:0] word7 = memory[7];
    (* keep *) wire [31:0] word8 = memory[8];
    (* keep *) wire [31:0] word9 = memory[9];
    (* keep *) wire [31:0] word10 = memory[10];
    (* keep *) wire [31:0] word11 = memory[11];
    (* keep *) wire [31:0] word12 = memory[12];
    (* keep *) wire [31:0] word13 = memory[13];
    (* keep *) wire [31:0] word14 = memory[14];
    (* keep *) wire [31:0] word15 = memory[15];
    (* keep *) wire [31:0] word16 = memory[16];
    (* keep *) wire [31:0] word17 = memory[17];
    (* keep *) wire [31:0] word18 = memory[18];
    (* keep *) wire [31:0] word19 = memory[19];
    (* keep *) wire [31:0] word20 = memory[20];
    (* keep *) wire [31:0] word21 = memory[21];
    (* keep *) wire [31:0] word22 = memory[22];
    (* keep *) wire [31:0] word23 = memory[23];
    (* keep *) wire [31:0] word24 = memory[24];
    (* keep *) wire [31:0] word25 = memory[25];
    (* keep *) wire [31:0] word26 = memory[26];
    (* keep *) wire [31:0] word27 = memory[27];
    (* keep *) wire [31:0] word28 = memory[28];
    (* keep *) wire [31:0] word29 = memory[29];
    (* keep *) wire [31:0] word30 = memory[30];
    (* keep *) wire [31:0] word31 = memory[31];
    (* keep *) wire [31:0] word32 = memory[32];
    (* keep *) wire [31:0] word33 = memory[33];
    (* keep *) wire [31:0] word34 = memory[34];
    (* keep *) wire [31:0] word35 = memory[35];
    (* keep *) wire [31:0] word36 = memory[36];
    (* keep *) wire [31:0] word37 = memory[37];
    (* keep *) wire [31:0] word38 = memory[38];
    (* keep *) wire [31:0] word39 = memory[39];
    (* keep *) wire [31:0] word40 = memory[40];
    (* keep *) wire [31:0] word41 = memory[41];
    (* keep *) wire [31:0] word42 = memory[42];
    (* keep *) wire [31:0] word43 = memory[43];
    (* keep *) wire [31:0] word44 = memory[44];
    (* keep *) wire [31:0] word45 = memory[45];
    (* keep *) wire [31:0] word46 = memory[46];
    (* keep *) wire [31:0] word47 = memory[47];
    (* keep *) wire [31:0] word48 = memory[48];
    (* keep *) wire [31:0] word49 = memory[49];
    (* keep *) wire [31:0] word50 = memory[50];
    (* keep *) wire [31:0] word51 = memory[51];
    (* keep *) wire [31:0] word52 = memory[52];
    (* keep *) wire [31:0] word53 = memory[53];
    (* keep *) wire [31:0] word54 = memory[54];
    (* keep *) wire [31:0] word55 = memory[55];
    (* keep *) wire [31:0] word56 = memory[56];
    (* keep *) wire [31:0] word57 = memory[57];
    (* keep *) wire [31:0] word58 = memory[58];
    (* keep *) wire [31:0] word59 = memory[59];
    (* keep *) wire [31:0] word60 = memory[60];
    (* keep *) wire [31:0] word61 = memory[61];
    (* keep *) wire [31:0] word62 = memory[62];
    (* keep *) wire [31:0] word63 = memory[63];
    (* keep *) wire [31:0] word64 = memory[64];
    (* keep *) wire [31:0] word65 = memory[65];
    (* keep *) wire [31:0] word66 = memory[66];
    (* keep *) wire [31:0] word67 = memory[67];
    (* keep *) wire [31:0] word68 = memory[68];
    (* keep *) wire [31:0] word69 = memory[69];
    (* keep *) wire [31:0] word70 = memory[70];
    (* keep *) wire [31:0] word71 = memory[71];
    (* keep *) wire [31:0] word72 = memory[72];
    (* keep *) wire [31:0] word73 = memory[73];
    (* keep *) wire [31:0] word74 = memory[74];
    (* keep *) wire [31:0] word75 = memory[75];
    (* keep *) wire [31:0] word76 = memory[76];
    (* keep *) wire [31:0] word77 = memory[77];
    (* keep *) wire [31:0] word78 = memory[78];
    (* keep *) wire [31:0] word79 = memory[79];
    (* keep *) wire [31:0] word80 = memory[80];
    (* keep *) wire [31:0] word81 = memory[81];
    (* keep *) wire [31:0] word82 = memory[82];
    (* keep *) wire [31:0] word83 = memory[83];
    (* keep *) wire [31:0] word84 = memory[84];
    (* keep *) wire [31:0] word85 = memory[85];
    (* keep *) wire [31:0] word86 = memory[86];
    (* keep *) wire [31:0] word87 = memory[87];
    (* keep *) wire [31:0] word88 = memory[88];
    (* keep *) wire [31:0] word89 = memory[89];
    (* keep *) wire [31:0] word90 = memory[90];
    (* keep *) wire [31:0] word91 = memory[91];
    (* keep *) wire [31:0] word92 = memory[92];
    (* keep *) wire [31:0] word93 = memory[93];
    (* keep *) wire [31:0] word94 = memory[94];
    (* keep *) wire [31:0] word95 = memory[95];
    (* keep *) wire [31:0] word96 = memory[96];
    (* keep *) wire [31:0] word97 = memory[97];
    (* keep *) wire [31:0] word98 = memory[98];
    (* keep *) wire [31:0] word99 = memory[99];
    (* keep *) wire [31:0] word100 = memory[100];
    (* keep *) wire [31:0] word101 = memory[101];
    (* keep *) wire [31:0] word102 = memory[102];
    (* keep *) wire [31:0] word103 = memory[103];
    (* keep *) wire [31:0] word104 = memory[104];
    (* keep *) wire [31:0] word105 = memory[105];
    (* keep *) wire [31:0] word106 = memory[106];
    (* keep *) wire [31:0] word107 = memory[107];
    (* keep *) wire [31:0] word108 = memory[108];
    (* keep *) wire [31:0] word109 = memory[109];
    (* keep *) wire [31:0] word110 = memory[110];
    (* keep *) wire [31:0] word111 = memory[111];
    (* keep *) wire [31:0] word112 = memory[112];
    (* keep *) wire [31:0] word113 = memory[113];
    (* keep *) wire [31:0] word114 = memory[114];
    (* keep *) wire [31:0] word115 = memory[115];
    (* keep *) wire [31:0] word116 = memory[116];
    (* keep *) wire [31:0] word117 = memory[117];
    (* keep *) wire [31:0] word118 = memory[118];
    (* keep *) wire [31:0] word119 = memory[119];
    (* keep *) wire [31:0] word120 = memory[120];
    (* keep *) wire [31:0] word121 = memory[121];
    (* keep *) wire [31:0] word122 = memory[122];
    (* keep *) wire [31:0] word123 = memory[123];
    (* keep *) wire [31:0] word124 = memory[124];
    (* keep *) wire [31:0] word125 = memory[125];
    (* keep *) wire [31:0] word126 = memory[126];
    (* keep *) wire [31:0] word127 = memory[127];
    always @(posedge clk) begin
        if (!rst_n) begin
            for (index=0; index<128; index=index+1)
                memory[index] <= 0;
            program_bank <= 0;
            program_length <= 0;
            program_ready <= 0;
        end else if (ena && load_mode && load_write) begin
            if (load_bank) begin
                program_bank <= data_in < 16 ? data_in[3:0] : 0;
                program_length <= 0;
                program_ready <= 0;
            end else if (load_length) begin
                program_bank <= 0;
                program_length <= accepted_length ? data_in : 0;
                program_ready <= accepted_length;
            end else begin
                program_ready <= 0;
                if (address < 128)
                    case (byte_address[1:0])
                        0: memory[address][7:0] <= data_in;
                        1: memory[address][15:8] <= data_in;
                        2: memory[address][23:16] <= data_in;
                        3: memory[address][31:24] <= data_in;
                    endcase
            end
        end
    end
    always @(*) begin
        instruction = pc < 128 ? memory[pc] : 32'd0;
        data_out = 0;
        if (address < 128)
            case (byte_address[1:0])
                0: data_out = memory[address][7:0];
                1: data_out = memory[address][15:8];
                2: data_out = memory[address][23:16];
                3: data_out = memory[address][31:24];
            endcase
        if (load_length) data_out = program_length;
    end
    assign instruction_valid = program_ready && pc < program_length && pc < 128;
endmodule
`default_nettype wire
