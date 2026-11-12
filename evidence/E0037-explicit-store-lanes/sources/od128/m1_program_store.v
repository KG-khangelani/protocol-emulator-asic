/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none
module m1_program_store (
    input wire clk, input wire rst_n, input wire ena,
    input wire load_mode, input wire load_write, input wire load_length, input wire load_bank,
    input wire [4:0] byte_address, input wire [7:0] data_in,
    input wire [7:0] pc,
    output reg [7:0] data_out, output reg [7:0] program_length,
    output reg program_ready, output reg [3:0] program_bank,
    output reg [31:0] instruction, output wire instruction_valid
);
    reg [31:0] word0;
    reg [31:0] word1;
    reg [31:0] word2;
    reg [31:0] word3;
    reg [31:0] word4;
    reg [31:0] word5;
    reg [31:0] word6;
    reg [31:0] word7;
    reg [31:0] word8;
    reg [31:0] word9;
    reg [31:0] word10;
    reg [31:0] word11;
    reg [31:0] word12;
    reg [31:0] word13;
    reg [31:0] word14;
    reg [31:0] word15;
    reg [31:0] word16;
    reg [31:0] word17;
    reg [31:0] word18;
    reg [31:0] word19;
    reg [31:0] word20;
    reg [31:0] word21;
    reg [31:0] word22;
    reg [31:0] word23;
    reg [31:0] word24;
    reg [31:0] word25;
    reg [31:0] word26;
    reg [31:0] word27;
    reg [31:0] word28;
    reg [31:0] word29;
    reg [31:0] word30;
    reg [31:0] word31;
    reg [31:0] word32;
    reg [31:0] word33;
    reg [31:0] word34;
    reg [31:0] word35;
    reg [31:0] word36;
    reg [31:0] word37;
    reg [31:0] word38;
    reg [31:0] word39;
    reg [31:0] word40;
    reg [31:0] word41;
    reg [31:0] word42;
    reg [31:0] word43;
    reg [31:0] word44;
    reg [31:0] word45;
    reg [31:0] word46;
    reg [31:0] word47;
    reg [31:0] word48;
    reg [31:0] word49;
    reg [31:0] word50;
    reg [31:0] word51;
    reg [31:0] word52;
    reg [31:0] word53;
    reg [31:0] word54;
    reg [31:0] word55;
    reg [31:0] word56;
    reg [31:0] word57;
    reg [31:0] word58;
    reg [31:0] word59;
    reg [31:0] word60;
    reg [31:0] word61;
    reg [31:0] word62;
    reg [31:0] word63;
    reg [31:0] word64;
    reg [31:0] word65;
    reg [31:0] word66;
    reg [31:0] word67;
    reg [31:0] word68;
    reg [31:0] word69;
    reg [31:0] word70;
    reg [31:0] word71;
    reg [31:0] word72;
    reg [31:0] word73;
    reg [31:0] word74;
    reg [31:0] word75;
    reg [31:0] word76;
    reg [31:0] word77;
    reg [31:0] word78;
    reg [31:0] word79;
    reg [31:0] word80;
    reg [31:0] word81;
    reg [31:0] word82;
    reg [31:0] word83;
    reg [31:0] word84;
    reg [31:0] word85;
    reg [31:0] word86;
    reg [31:0] word87;
    reg [31:0] word88;
    reg [31:0] word89;
    reg [31:0] word90;
    reg [31:0] word91;
    reg [31:0] word92;
    reg [31:0] word93;
    reg [31:0] word94;
    reg [31:0] word95;
    reg [31:0] word96;
    reg [31:0] word97;
    reg [31:0] word98;
    reg [31:0] word99;
    reg [31:0] word100;
    reg [31:0] word101;
    reg [31:0] word102;
    reg [31:0] word103;
    reg [31:0] word104;
    reg [31:0] word105;
    reg [31:0] word106;
    reg [31:0] word107;
    reg [31:0] word108;
    reg [31:0] word109;
    reg [31:0] word110;
    reg [31:0] word111;
    reg [31:0] word112;
    reg [31:0] word113;
    reg [31:0] word114;
    reg [31:0] word115;
    reg [31:0] word116;
    reg [31:0] word117;
    reg [31:0] word118;
    reg [31:0] word119;
    reg [31:0] word120;
    reg [31:0] word121;
    reg [31:0] word122;
    reg [31:0] word123;
    reg [31:0] word124;
    reg [31:0] word125;
    reg [31:0] word126;
    reg [31:0] word127;
    wire [8:0] bank_address = {program_bank, byte_address};
    wire length_valid = (data_in >= 8'd1) && (data_in <= 8'd128);
    always @(posedge clk) begin
        if (!rst_n) begin
            word0 <= 32'd0;
            word1 <= 32'd0;
            word2 <= 32'd0;
            word3 <= 32'd0;
            word4 <= 32'd0;
            word5 <= 32'd0;
            word6 <= 32'd0;
            word7 <= 32'd0;
            word8 <= 32'd0;
            word9 <= 32'd0;
            word10 <= 32'd0;
            word11 <= 32'd0;
            word12 <= 32'd0;
            word13 <= 32'd0;
            word14 <= 32'd0;
            word15 <= 32'd0;
            word16 <= 32'd0;
            word17 <= 32'd0;
            word18 <= 32'd0;
            word19 <= 32'd0;
            word20 <= 32'd0;
            word21 <= 32'd0;
            word22 <= 32'd0;
            word23 <= 32'd0;
            word24 <= 32'd0;
            word25 <= 32'd0;
            word26 <= 32'd0;
            word27 <= 32'd0;
            word28 <= 32'd0;
            word29 <= 32'd0;
            word30 <= 32'd0;
            word31 <= 32'd0;
            word32 <= 32'd0;
            word33 <= 32'd0;
            word34 <= 32'd0;
            word35 <= 32'd0;
            word36 <= 32'd0;
            word37 <= 32'd0;
            word38 <= 32'd0;
            word39 <= 32'd0;
            word40 <= 32'd0;
            word41 <= 32'd0;
            word42 <= 32'd0;
            word43 <= 32'd0;
            word44 <= 32'd0;
            word45 <= 32'd0;
            word46 <= 32'd0;
            word47 <= 32'd0;
            word48 <= 32'd0;
            word49 <= 32'd0;
            word50 <= 32'd0;
            word51 <= 32'd0;
            word52 <= 32'd0;
            word53 <= 32'd0;
            word54 <= 32'd0;
            word55 <= 32'd0;
            word56 <= 32'd0;
            word57 <= 32'd0;
            word58 <= 32'd0;
            word59 <= 32'd0;
            word60 <= 32'd0;
            word61 <= 32'd0;
            word62 <= 32'd0;
            word63 <= 32'd0;
            word64 <= 32'd0;
            word65 <= 32'd0;
            word66 <= 32'd0;
            word67 <= 32'd0;
            word68 <= 32'd0;
            word69 <= 32'd0;
            word70 <= 32'd0;
            word71 <= 32'd0;
            word72 <= 32'd0;
            word73 <= 32'd0;
            word74 <= 32'd0;
            word75 <= 32'd0;
            word76 <= 32'd0;
            word77 <= 32'd0;
            word78 <= 32'd0;
            word79 <= 32'd0;
            word80 <= 32'd0;
            word81 <= 32'd0;
            word82 <= 32'd0;
            word83 <= 32'd0;
            word84 <= 32'd0;
            word85 <= 32'd0;
            word86 <= 32'd0;
            word87 <= 32'd0;
            word88 <= 32'd0;
            word89 <= 32'd0;
            word90 <= 32'd0;
            word91 <= 32'd0;
            word92 <= 32'd0;
            word93 <= 32'd0;
            word94 <= 32'd0;
            word95 <= 32'd0;
            word96 <= 32'd0;
            word97 <= 32'd0;
            word98 <= 32'd0;
            word99 <= 32'd0;
            word100 <= 32'd0;
            word101 <= 32'd0;
            word102 <= 32'd0;
            word103 <= 32'd0;
            word104 <= 32'd0;
            word105 <= 32'd0;
            word106 <= 32'd0;
            word107 <= 32'd0;
            word108 <= 32'd0;
            word109 <= 32'd0;
            word110 <= 32'd0;
            word111 <= 32'd0;
            word112 <= 32'd0;
            word113 <= 32'd0;
            word114 <= 32'd0;
            word115 <= 32'd0;
            word116 <= 32'd0;
            word117 <= 32'd0;
            word118 <= 32'd0;
            word119 <= 32'd0;
            word120 <= 32'd0;
            word121 <= 32'd0;
            word122 <= 32'd0;
            word123 <= 32'd0;
            word124 <= 32'd0;
            word125 <= 32'd0;
            word126 <= 32'd0;
            word127 <= 32'd0;
            program_bank <= 4'd0;
            program_length <= 8'd0;
            program_ready <= 1'b0;
        end else if (ena && load_mode && load_write) begin
            if (load_bank) begin
                program_bank <= (data_in < 8'd16) ? data_in[3:0] : 4'd0;
                program_length <= 8'd0;
                program_ready <= 1'b0;
            end else if (load_length) begin
                program_bank <= 4'd0;
                program_length <= length_valid ? data_in : 8'd0;
                program_ready <= length_valid;
            end else begin
                program_ready <= 1'b0;
                case (bank_address[8:2])
                    7'd0: begin
                        case (byte_address[1:0])
                            2'd0: word0[7:0] <= data_in;
                            2'd1: word0[15:8] <= data_in;
                            2'd2: word0[23:16] <= data_in;
                            2'd3: word0[31:24] <= data_in;
                        endcase
                    end
                    7'd1: begin
                        case (byte_address[1:0])
                            2'd0: word1[7:0] <= data_in;
                            2'd1: word1[15:8] <= data_in;
                            2'd2: word1[23:16] <= data_in;
                            2'd3: word1[31:24] <= data_in;
                        endcase
                    end
                    7'd2: begin
                        case (byte_address[1:0])
                            2'd0: word2[7:0] <= data_in;
                            2'd1: word2[15:8] <= data_in;
                            2'd2: word2[23:16] <= data_in;
                            2'd3: word2[31:24] <= data_in;
                        endcase
                    end
                    7'd3: begin
                        case (byte_address[1:0])
                            2'd0: word3[7:0] <= data_in;
                            2'd1: word3[15:8] <= data_in;
                            2'd2: word3[23:16] <= data_in;
                            2'd3: word3[31:24] <= data_in;
                        endcase
                    end
                    7'd4: begin
                        case (byte_address[1:0])
                            2'd0: word4[7:0] <= data_in;
                            2'd1: word4[15:8] <= data_in;
                            2'd2: word4[23:16] <= data_in;
                            2'd3: word4[31:24] <= data_in;
                        endcase
                    end
                    7'd5: begin
                        case (byte_address[1:0])
                            2'd0: word5[7:0] <= data_in;
                            2'd1: word5[15:8] <= data_in;
                            2'd2: word5[23:16] <= data_in;
                            2'd3: word5[31:24] <= data_in;
                        endcase
                    end
                    7'd6: begin
                        case (byte_address[1:0])
                            2'd0: word6[7:0] <= data_in;
                            2'd1: word6[15:8] <= data_in;
                            2'd2: word6[23:16] <= data_in;
                            2'd3: word6[31:24] <= data_in;
                        endcase
                    end
                    7'd7: begin
                        case (byte_address[1:0])
                            2'd0: word7[7:0] <= data_in;
                            2'd1: word7[15:8] <= data_in;
                            2'd2: word7[23:16] <= data_in;
                            2'd3: word7[31:24] <= data_in;
                        endcase
                    end
                    7'd8: begin
                        case (byte_address[1:0])
                            2'd0: word8[7:0] <= data_in;
                            2'd1: word8[15:8] <= data_in;
                            2'd2: word8[23:16] <= data_in;
                            2'd3: word8[31:24] <= data_in;
                        endcase
                    end
                    7'd9: begin
                        case (byte_address[1:0])
                            2'd0: word9[7:0] <= data_in;
                            2'd1: word9[15:8] <= data_in;
                            2'd2: word9[23:16] <= data_in;
                            2'd3: word9[31:24] <= data_in;
                        endcase
                    end
                    7'd10: begin
                        case (byte_address[1:0])
                            2'd0: word10[7:0] <= data_in;
                            2'd1: word10[15:8] <= data_in;
                            2'd2: word10[23:16] <= data_in;
                            2'd3: word10[31:24] <= data_in;
                        endcase
                    end
                    7'd11: begin
                        case (byte_address[1:0])
                            2'd0: word11[7:0] <= data_in;
                            2'd1: word11[15:8] <= data_in;
                            2'd2: word11[23:16] <= data_in;
                            2'd3: word11[31:24] <= data_in;
                        endcase
                    end
                    7'd12: begin
                        case (byte_address[1:0])
                            2'd0: word12[7:0] <= data_in;
                            2'd1: word12[15:8] <= data_in;
                            2'd2: word12[23:16] <= data_in;
                            2'd3: word12[31:24] <= data_in;
                        endcase
                    end
                    7'd13: begin
                        case (byte_address[1:0])
                            2'd0: word13[7:0] <= data_in;
                            2'd1: word13[15:8] <= data_in;
                            2'd2: word13[23:16] <= data_in;
                            2'd3: word13[31:24] <= data_in;
                        endcase
                    end
                    7'd14: begin
                        case (byte_address[1:0])
                            2'd0: word14[7:0] <= data_in;
                            2'd1: word14[15:8] <= data_in;
                            2'd2: word14[23:16] <= data_in;
                            2'd3: word14[31:24] <= data_in;
                        endcase
                    end
                    7'd15: begin
                        case (byte_address[1:0])
                            2'd0: word15[7:0] <= data_in;
                            2'd1: word15[15:8] <= data_in;
                            2'd2: word15[23:16] <= data_in;
                            2'd3: word15[31:24] <= data_in;
                        endcase
                    end
                    7'd16: begin
                        case (byte_address[1:0])
                            2'd0: word16[7:0] <= data_in;
                            2'd1: word16[15:8] <= data_in;
                            2'd2: word16[23:16] <= data_in;
                            2'd3: word16[31:24] <= data_in;
                        endcase
                    end
                    7'd17: begin
                        case (byte_address[1:0])
                            2'd0: word17[7:0] <= data_in;
                            2'd1: word17[15:8] <= data_in;
                            2'd2: word17[23:16] <= data_in;
                            2'd3: word17[31:24] <= data_in;
                        endcase
                    end
                    7'd18: begin
                        case (byte_address[1:0])
                            2'd0: word18[7:0] <= data_in;
                            2'd1: word18[15:8] <= data_in;
                            2'd2: word18[23:16] <= data_in;
                            2'd3: word18[31:24] <= data_in;
                        endcase
                    end
                    7'd19: begin
                        case (byte_address[1:0])
                            2'd0: word19[7:0] <= data_in;
                            2'd1: word19[15:8] <= data_in;
                            2'd2: word19[23:16] <= data_in;
                            2'd3: word19[31:24] <= data_in;
                        endcase
                    end
                    7'd20: begin
                        case (byte_address[1:0])
                            2'd0: word20[7:0] <= data_in;
                            2'd1: word20[15:8] <= data_in;
                            2'd2: word20[23:16] <= data_in;
                            2'd3: word20[31:24] <= data_in;
                        endcase
                    end
                    7'd21: begin
                        case (byte_address[1:0])
                            2'd0: word21[7:0] <= data_in;
                            2'd1: word21[15:8] <= data_in;
                            2'd2: word21[23:16] <= data_in;
                            2'd3: word21[31:24] <= data_in;
                        endcase
                    end
                    7'd22: begin
                        case (byte_address[1:0])
                            2'd0: word22[7:0] <= data_in;
                            2'd1: word22[15:8] <= data_in;
                            2'd2: word22[23:16] <= data_in;
                            2'd3: word22[31:24] <= data_in;
                        endcase
                    end
                    7'd23: begin
                        case (byte_address[1:0])
                            2'd0: word23[7:0] <= data_in;
                            2'd1: word23[15:8] <= data_in;
                            2'd2: word23[23:16] <= data_in;
                            2'd3: word23[31:24] <= data_in;
                        endcase
                    end
                    7'd24: begin
                        case (byte_address[1:0])
                            2'd0: word24[7:0] <= data_in;
                            2'd1: word24[15:8] <= data_in;
                            2'd2: word24[23:16] <= data_in;
                            2'd3: word24[31:24] <= data_in;
                        endcase
                    end
                    7'd25: begin
                        case (byte_address[1:0])
                            2'd0: word25[7:0] <= data_in;
                            2'd1: word25[15:8] <= data_in;
                            2'd2: word25[23:16] <= data_in;
                            2'd3: word25[31:24] <= data_in;
                        endcase
                    end
                    7'd26: begin
                        case (byte_address[1:0])
                            2'd0: word26[7:0] <= data_in;
                            2'd1: word26[15:8] <= data_in;
                            2'd2: word26[23:16] <= data_in;
                            2'd3: word26[31:24] <= data_in;
                        endcase
                    end
                    7'd27: begin
                        case (byte_address[1:0])
                            2'd0: word27[7:0] <= data_in;
                            2'd1: word27[15:8] <= data_in;
                            2'd2: word27[23:16] <= data_in;
                            2'd3: word27[31:24] <= data_in;
                        endcase
                    end
                    7'd28: begin
                        case (byte_address[1:0])
                            2'd0: word28[7:0] <= data_in;
                            2'd1: word28[15:8] <= data_in;
                            2'd2: word28[23:16] <= data_in;
                            2'd3: word28[31:24] <= data_in;
                        endcase
                    end
                    7'd29: begin
                        case (byte_address[1:0])
                            2'd0: word29[7:0] <= data_in;
                            2'd1: word29[15:8] <= data_in;
                            2'd2: word29[23:16] <= data_in;
                            2'd3: word29[31:24] <= data_in;
                        endcase
                    end
                    7'd30: begin
                        case (byte_address[1:0])
                            2'd0: word30[7:0] <= data_in;
                            2'd1: word30[15:8] <= data_in;
                            2'd2: word30[23:16] <= data_in;
                            2'd3: word30[31:24] <= data_in;
                        endcase
                    end
                    7'd31: begin
                        case (byte_address[1:0])
                            2'd0: word31[7:0] <= data_in;
                            2'd1: word31[15:8] <= data_in;
                            2'd2: word31[23:16] <= data_in;
                            2'd3: word31[31:24] <= data_in;
                        endcase
                    end
                    7'd32: begin
                        case (byte_address[1:0])
                            2'd0: word32[7:0] <= data_in;
                            2'd1: word32[15:8] <= data_in;
                            2'd2: word32[23:16] <= data_in;
                            2'd3: word32[31:24] <= data_in;
                        endcase
                    end
                    7'd33: begin
                        case (byte_address[1:0])
                            2'd0: word33[7:0] <= data_in;
                            2'd1: word33[15:8] <= data_in;
                            2'd2: word33[23:16] <= data_in;
                            2'd3: word33[31:24] <= data_in;
                        endcase
                    end
                    7'd34: begin
                        case (byte_address[1:0])
                            2'd0: word34[7:0] <= data_in;
                            2'd1: word34[15:8] <= data_in;
                            2'd2: word34[23:16] <= data_in;
                            2'd3: word34[31:24] <= data_in;
                        endcase
                    end
                    7'd35: begin
                        case (byte_address[1:0])
                            2'd0: word35[7:0] <= data_in;
                            2'd1: word35[15:8] <= data_in;
                            2'd2: word35[23:16] <= data_in;
                            2'd3: word35[31:24] <= data_in;
                        endcase
                    end
                    7'd36: begin
                        case (byte_address[1:0])
                            2'd0: word36[7:0] <= data_in;
                            2'd1: word36[15:8] <= data_in;
                            2'd2: word36[23:16] <= data_in;
                            2'd3: word36[31:24] <= data_in;
                        endcase
                    end
                    7'd37: begin
                        case (byte_address[1:0])
                            2'd0: word37[7:0] <= data_in;
                            2'd1: word37[15:8] <= data_in;
                            2'd2: word37[23:16] <= data_in;
                            2'd3: word37[31:24] <= data_in;
                        endcase
                    end
                    7'd38: begin
                        case (byte_address[1:0])
                            2'd0: word38[7:0] <= data_in;
                            2'd1: word38[15:8] <= data_in;
                            2'd2: word38[23:16] <= data_in;
                            2'd3: word38[31:24] <= data_in;
                        endcase
                    end
                    7'd39: begin
                        case (byte_address[1:0])
                            2'd0: word39[7:0] <= data_in;
                            2'd1: word39[15:8] <= data_in;
                            2'd2: word39[23:16] <= data_in;
                            2'd3: word39[31:24] <= data_in;
                        endcase
                    end
                    7'd40: begin
                        case (byte_address[1:0])
                            2'd0: word40[7:0] <= data_in;
                            2'd1: word40[15:8] <= data_in;
                            2'd2: word40[23:16] <= data_in;
                            2'd3: word40[31:24] <= data_in;
                        endcase
                    end
                    7'd41: begin
                        case (byte_address[1:0])
                            2'd0: word41[7:0] <= data_in;
                            2'd1: word41[15:8] <= data_in;
                            2'd2: word41[23:16] <= data_in;
                            2'd3: word41[31:24] <= data_in;
                        endcase
                    end
                    7'd42: begin
                        case (byte_address[1:0])
                            2'd0: word42[7:0] <= data_in;
                            2'd1: word42[15:8] <= data_in;
                            2'd2: word42[23:16] <= data_in;
                            2'd3: word42[31:24] <= data_in;
                        endcase
                    end
                    7'd43: begin
                        case (byte_address[1:0])
                            2'd0: word43[7:0] <= data_in;
                            2'd1: word43[15:8] <= data_in;
                            2'd2: word43[23:16] <= data_in;
                            2'd3: word43[31:24] <= data_in;
                        endcase
                    end
                    7'd44: begin
                        case (byte_address[1:0])
                            2'd0: word44[7:0] <= data_in;
                            2'd1: word44[15:8] <= data_in;
                            2'd2: word44[23:16] <= data_in;
                            2'd3: word44[31:24] <= data_in;
                        endcase
                    end
                    7'd45: begin
                        case (byte_address[1:0])
                            2'd0: word45[7:0] <= data_in;
                            2'd1: word45[15:8] <= data_in;
                            2'd2: word45[23:16] <= data_in;
                            2'd3: word45[31:24] <= data_in;
                        endcase
                    end
                    7'd46: begin
                        case (byte_address[1:0])
                            2'd0: word46[7:0] <= data_in;
                            2'd1: word46[15:8] <= data_in;
                            2'd2: word46[23:16] <= data_in;
                            2'd3: word46[31:24] <= data_in;
                        endcase
                    end
                    7'd47: begin
                        case (byte_address[1:0])
                            2'd0: word47[7:0] <= data_in;
                            2'd1: word47[15:8] <= data_in;
                            2'd2: word47[23:16] <= data_in;
                            2'd3: word47[31:24] <= data_in;
                        endcase
                    end
                    7'd48: begin
                        case (byte_address[1:0])
                            2'd0: word48[7:0] <= data_in;
                            2'd1: word48[15:8] <= data_in;
                            2'd2: word48[23:16] <= data_in;
                            2'd3: word48[31:24] <= data_in;
                        endcase
                    end
                    7'd49: begin
                        case (byte_address[1:0])
                            2'd0: word49[7:0] <= data_in;
                            2'd1: word49[15:8] <= data_in;
                            2'd2: word49[23:16] <= data_in;
                            2'd3: word49[31:24] <= data_in;
                        endcase
                    end
                    7'd50: begin
                        case (byte_address[1:0])
                            2'd0: word50[7:0] <= data_in;
                            2'd1: word50[15:8] <= data_in;
                            2'd2: word50[23:16] <= data_in;
                            2'd3: word50[31:24] <= data_in;
                        endcase
                    end
                    7'd51: begin
                        case (byte_address[1:0])
                            2'd0: word51[7:0] <= data_in;
                            2'd1: word51[15:8] <= data_in;
                            2'd2: word51[23:16] <= data_in;
                            2'd3: word51[31:24] <= data_in;
                        endcase
                    end
                    7'd52: begin
                        case (byte_address[1:0])
                            2'd0: word52[7:0] <= data_in;
                            2'd1: word52[15:8] <= data_in;
                            2'd2: word52[23:16] <= data_in;
                            2'd3: word52[31:24] <= data_in;
                        endcase
                    end
                    7'd53: begin
                        case (byte_address[1:0])
                            2'd0: word53[7:0] <= data_in;
                            2'd1: word53[15:8] <= data_in;
                            2'd2: word53[23:16] <= data_in;
                            2'd3: word53[31:24] <= data_in;
                        endcase
                    end
                    7'd54: begin
                        case (byte_address[1:0])
                            2'd0: word54[7:0] <= data_in;
                            2'd1: word54[15:8] <= data_in;
                            2'd2: word54[23:16] <= data_in;
                            2'd3: word54[31:24] <= data_in;
                        endcase
                    end
                    7'd55: begin
                        case (byte_address[1:0])
                            2'd0: word55[7:0] <= data_in;
                            2'd1: word55[15:8] <= data_in;
                            2'd2: word55[23:16] <= data_in;
                            2'd3: word55[31:24] <= data_in;
                        endcase
                    end
                    7'd56: begin
                        case (byte_address[1:0])
                            2'd0: word56[7:0] <= data_in;
                            2'd1: word56[15:8] <= data_in;
                            2'd2: word56[23:16] <= data_in;
                            2'd3: word56[31:24] <= data_in;
                        endcase
                    end
                    7'd57: begin
                        case (byte_address[1:0])
                            2'd0: word57[7:0] <= data_in;
                            2'd1: word57[15:8] <= data_in;
                            2'd2: word57[23:16] <= data_in;
                            2'd3: word57[31:24] <= data_in;
                        endcase
                    end
                    7'd58: begin
                        case (byte_address[1:0])
                            2'd0: word58[7:0] <= data_in;
                            2'd1: word58[15:8] <= data_in;
                            2'd2: word58[23:16] <= data_in;
                            2'd3: word58[31:24] <= data_in;
                        endcase
                    end
                    7'd59: begin
                        case (byte_address[1:0])
                            2'd0: word59[7:0] <= data_in;
                            2'd1: word59[15:8] <= data_in;
                            2'd2: word59[23:16] <= data_in;
                            2'd3: word59[31:24] <= data_in;
                        endcase
                    end
                    7'd60: begin
                        case (byte_address[1:0])
                            2'd0: word60[7:0] <= data_in;
                            2'd1: word60[15:8] <= data_in;
                            2'd2: word60[23:16] <= data_in;
                            2'd3: word60[31:24] <= data_in;
                        endcase
                    end
                    7'd61: begin
                        case (byte_address[1:0])
                            2'd0: word61[7:0] <= data_in;
                            2'd1: word61[15:8] <= data_in;
                            2'd2: word61[23:16] <= data_in;
                            2'd3: word61[31:24] <= data_in;
                        endcase
                    end
                    7'd62: begin
                        case (byte_address[1:0])
                            2'd0: word62[7:0] <= data_in;
                            2'd1: word62[15:8] <= data_in;
                            2'd2: word62[23:16] <= data_in;
                            2'd3: word62[31:24] <= data_in;
                        endcase
                    end
                    7'd63: begin
                        case (byte_address[1:0])
                            2'd0: word63[7:0] <= data_in;
                            2'd1: word63[15:8] <= data_in;
                            2'd2: word63[23:16] <= data_in;
                            2'd3: word63[31:24] <= data_in;
                        endcase
                    end
                    7'd64: begin
                        case (byte_address[1:0])
                            2'd0: word64[7:0] <= data_in;
                            2'd1: word64[15:8] <= data_in;
                            2'd2: word64[23:16] <= data_in;
                            2'd3: word64[31:24] <= data_in;
                        endcase
                    end
                    7'd65: begin
                        case (byte_address[1:0])
                            2'd0: word65[7:0] <= data_in;
                            2'd1: word65[15:8] <= data_in;
                            2'd2: word65[23:16] <= data_in;
                            2'd3: word65[31:24] <= data_in;
                        endcase
                    end
                    7'd66: begin
                        case (byte_address[1:0])
                            2'd0: word66[7:0] <= data_in;
                            2'd1: word66[15:8] <= data_in;
                            2'd2: word66[23:16] <= data_in;
                            2'd3: word66[31:24] <= data_in;
                        endcase
                    end
                    7'd67: begin
                        case (byte_address[1:0])
                            2'd0: word67[7:0] <= data_in;
                            2'd1: word67[15:8] <= data_in;
                            2'd2: word67[23:16] <= data_in;
                            2'd3: word67[31:24] <= data_in;
                        endcase
                    end
                    7'd68: begin
                        case (byte_address[1:0])
                            2'd0: word68[7:0] <= data_in;
                            2'd1: word68[15:8] <= data_in;
                            2'd2: word68[23:16] <= data_in;
                            2'd3: word68[31:24] <= data_in;
                        endcase
                    end
                    7'd69: begin
                        case (byte_address[1:0])
                            2'd0: word69[7:0] <= data_in;
                            2'd1: word69[15:8] <= data_in;
                            2'd2: word69[23:16] <= data_in;
                            2'd3: word69[31:24] <= data_in;
                        endcase
                    end
                    7'd70: begin
                        case (byte_address[1:0])
                            2'd0: word70[7:0] <= data_in;
                            2'd1: word70[15:8] <= data_in;
                            2'd2: word70[23:16] <= data_in;
                            2'd3: word70[31:24] <= data_in;
                        endcase
                    end
                    7'd71: begin
                        case (byte_address[1:0])
                            2'd0: word71[7:0] <= data_in;
                            2'd1: word71[15:8] <= data_in;
                            2'd2: word71[23:16] <= data_in;
                            2'd3: word71[31:24] <= data_in;
                        endcase
                    end
                    7'd72: begin
                        case (byte_address[1:0])
                            2'd0: word72[7:0] <= data_in;
                            2'd1: word72[15:8] <= data_in;
                            2'd2: word72[23:16] <= data_in;
                            2'd3: word72[31:24] <= data_in;
                        endcase
                    end
                    7'd73: begin
                        case (byte_address[1:0])
                            2'd0: word73[7:0] <= data_in;
                            2'd1: word73[15:8] <= data_in;
                            2'd2: word73[23:16] <= data_in;
                            2'd3: word73[31:24] <= data_in;
                        endcase
                    end
                    7'd74: begin
                        case (byte_address[1:0])
                            2'd0: word74[7:0] <= data_in;
                            2'd1: word74[15:8] <= data_in;
                            2'd2: word74[23:16] <= data_in;
                            2'd3: word74[31:24] <= data_in;
                        endcase
                    end
                    7'd75: begin
                        case (byte_address[1:0])
                            2'd0: word75[7:0] <= data_in;
                            2'd1: word75[15:8] <= data_in;
                            2'd2: word75[23:16] <= data_in;
                            2'd3: word75[31:24] <= data_in;
                        endcase
                    end
                    7'd76: begin
                        case (byte_address[1:0])
                            2'd0: word76[7:0] <= data_in;
                            2'd1: word76[15:8] <= data_in;
                            2'd2: word76[23:16] <= data_in;
                            2'd3: word76[31:24] <= data_in;
                        endcase
                    end
                    7'd77: begin
                        case (byte_address[1:0])
                            2'd0: word77[7:0] <= data_in;
                            2'd1: word77[15:8] <= data_in;
                            2'd2: word77[23:16] <= data_in;
                            2'd3: word77[31:24] <= data_in;
                        endcase
                    end
                    7'd78: begin
                        case (byte_address[1:0])
                            2'd0: word78[7:0] <= data_in;
                            2'd1: word78[15:8] <= data_in;
                            2'd2: word78[23:16] <= data_in;
                            2'd3: word78[31:24] <= data_in;
                        endcase
                    end
                    7'd79: begin
                        case (byte_address[1:0])
                            2'd0: word79[7:0] <= data_in;
                            2'd1: word79[15:8] <= data_in;
                            2'd2: word79[23:16] <= data_in;
                            2'd3: word79[31:24] <= data_in;
                        endcase
                    end
                    7'd80: begin
                        case (byte_address[1:0])
                            2'd0: word80[7:0] <= data_in;
                            2'd1: word80[15:8] <= data_in;
                            2'd2: word80[23:16] <= data_in;
                            2'd3: word80[31:24] <= data_in;
                        endcase
                    end
                    7'd81: begin
                        case (byte_address[1:0])
                            2'd0: word81[7:0] <= data_in;
                            2'd1: word81[15:8] <= data_in;
                            2'd2: word81[23:16] <= data_in;
                            2'd3: word81[31:24] <= data_in;
                        endcase
                    end
                    7'd82: begin
                        case (byte_address[1:0])
                            2'd0: word82[7:0] <= data_in;
                            2'd1: word82[15:8] <= data_in;
                            2'd2: word82[23:16] <= data_in;
                            2'd3: word82[31:24] <= data_in;
                        endcase
                    end
                    7'd83: begin
                        case (byte_address[1:0])
                            2'd0: word83[7:0] <= data_in;
                            2'd1: word83[15:8] <= data_in;
                            2'd2: word83[23:16] <= data_in;
                            2'd3: word83[31:24] <= data_in;
                        endcase
                    end
                    7'd84: begin
                        case (byte_address[1:0])
                            2'd0: word84[7:0] <= data_in;
                            2'd1: word84[15:8] <= data_in;
                            2'd2: word84[23:16] <= data_in;
                            2'd3: word84[31:24] <= data_in;
                        endcase
                    end
                    7'd85: begin
                        case (byte_address[1:0])
                            2'd0: word85[7:0] <= data_in;
                            2'd1: word85[15:8] <= data_in;
                            2'd2: word85[23:16] <= data_in;
                            2'd3: word85[31:24] <= data_in;
                        endcase
                    end
                    7'd86: begin
                        case (byte_address[1:0])
                            2'd0: word86[7:0] <= data_in;
                            2'd1: word86[15:8] <= data_in;
                            2'd2: word86[23:16] <= data_in;
                            2'd3: word86[31:24] <= data_in;
                        endcase
                    end
                    7'd87: begin
                        case (byte_address[1:0])
                            2'd0: word87[7:0] <= data_in;
                            2'd1: word87[15:8] <= data_in;
                            2'd2: word87[23:16] <= data_in;
                            2'd3: word87[31:24] <= data_in;
                        endcase
                    end
                    7'd88: begin
                        case (byte_address[1:0])
                            2'd0: word88[7:0] <= data_in;
                            2'd1: word88[15:8] <= data_in;
                            2'd2: word88[23:16] <= data_in;
                            2'd3: word88[31:24] <= data_in;
                        endcase
                    end
                    7'd89: begin
                        case (byte_address[1:0])
                            2'd0: word89[7:0] <= data_in;
                            2'd1: word89[15:8] <= data_in;
                            2'd2: word89[23:16] <= data_in;
                            2'd3: word89[31:24] <= data_in;
                        endcase
                    end
                    7'd90: begin
                        case (byte_address[1:0])
                            2'd0: word90[7:0] <= data_in;
                            2'd1: word90[15:8] <= data_in;
                            2'd2: word90[23:16] <= data_in;
                            2'd3: word90[31:24] <= data_in;
                        endcase
                    end
                    7'd91: begin
                        case (byte_address[1:0])
                            2'd0: word91[7:0] <= data_in;
                            2'd1: word91[15:8] <= data_in;
                            2'd2: word91[23:16] <= data_in;
                            2'd3: word91[31:24] <= data_in;
                        endcase
                    end
                    7'd92: begin
                        case (byte_address[1:0])
                            2'd0: word92[7:0] <= data_in;
                            2'd1: word92[15:8] <= data_in;
                            2'd2: word92[23:16] <= data_in;
                            2'd3: word92[31:24] <= data_in;
                        endcase
                    end
                    7'd93: begin
                        case (byte_address[1:0])
                            2'd0: word93[7:0] <= data_in;
                            2'd1: word93[15:8] <= data_in;
                            2'd2: word93[23:16] <= data_in;
                            2'd3: word93[31:24] <= data_in;
                        endcase
                    end
                    7'd94: begin
                        case (byte_address[1:0])
                            2'd0: word94[7:0] <= data_in;
                            2'd1: word94[15:8] <= data_in;
                            2'd2: word94[23:16] <= data_in;
                            2'd3: word94[31:24] <= data_in;
                        endcase
                    end
                    7'd95: begin
                        case (byte_address[1:0])
                            2'd0: word95[7:0] <= data_in;
                            2'd1: word95[15:8] <= data_in;
                            2'd2: word95[23:16] <= data_in;
                            2'd3: word95[31:24] <= data_in;
                        endcase
                    end
                    7'd96: begin
                        case (byte_address[1:0])
                            2'd0: word96[7:0] <= data_in;
                            2'd1: word96[15:8] <= data_in;
                            2'd2: word96[23:16] <= data_in;
                            2'd3: word96[31:24] <= data_in;
                        endcase
                    end
                    7'd97: begin
                        case (byte_address[1:0])
                            2'd0: word97[7:0] <= data_in;
                            2'd1: word97[15:8] <= data_in;
                            2'd2: word97[23:16] <= data_in;
                            2'd3: word97[31:24] <= data_in;
                        endcase
                    end
                    7'd98: begin
                        case (byte_address[1:0])
                            2'd0: word98[7:0] <= data_in;
                            2'd1: word98[15:8] <= data_in;
                            2'd2: word98[23:16] <= data_in;
                            2'd3: word98[31:24] <= data_in;
                        endcase
                    end
                    7'd99: begin
                        case (byte_address[1:0])
                            2'd0: word99[7:0] <= data_in;
                            2'd1: word99[15:8] <= data_in;
                            2'd2: word99[23:16] <= data_in;
                            2'd3: word99[31:24] <= data_in;
                        endcase
                    end
                    7'd100: begin
                        case (byte_address[1:0])
                            2'd0: word100[7:0] <= data_in;
                            2'd1: word100[15:8] <= data_in;
                            2'd2: word100[23:16] <= data_in;
                            2'd3: word100[31:24] <= data_in;
                        endcase
                    end
                    7'd101: begin
                        case (byte_address[1:0])
                            2'd0: word101[7:0] <= data_in;
                            2'd1: word101[15:8] <= data_in;
                            2'd2: word101[23:16] <= data_in;
                            2'd3: word101[31:24] <= data_in;
                        endcase
                    end
                    7'd102: begin
                        case (byte_address[1:0])
                            2'd0: word102[7:0] <= data_in;
                            2'd1: word102[15:8] <= data_in;
                            2'd2: word102[23:16] <= data_in;
                            2'd3: word102[31:24] <= data_in;
                        endcase
                    end
                    7'd103: begin
                        case (byte_address[1:0])
                            2'd0: word103[7:0] <= data_in;
                            2'd1: word103[15:8] <= data_in;
                            2'd2: word103[23:16] <= data_in;
                            2'd3: word103[31:24] <= data_in;
                        endcase
                    end
                    7'd104: begin
                        case (byte_address[1:0])
                            2'd0: word104[7:0] <= data_in;
                            2'd1: word104[15:8] <= data_in;
                            2'd2: word104[23:16] <= data_in;
                            2'd3: word104[31:24] <= data_in;
                        endcase
                    end
                    7'd105: begin
                        case (byte_address[1:0])
                            2'd0: word105[7:0] <= data_in;
                            2'd1: word105[15:8] <= data_in;
                            2'd2: word105[23:16] <= data_in;
                            2'd3: word105[31:24] <= data_in;
                        endcase
                    end
                    7'd106: begin
                        case (byte_address[1:0])
                            2'd0: word106[7:0] <= data_in;
                            2'd1: word106[15:8] <= data_in;
                            2'd2: word106[23:16] <= data_in;
                            2'd3: word106[31:24] <= data_in;
                        endcase
                    end
                    7'd107: begin
                        case (byte_address[1:0])
                            2'd0: word107[7:0] <= data_in;
                            2'd1: word107[15:8] <= data_in;
                            2'd2: word107[23:16] <= data_in;
                            2'd3: word107[31:24] <= data_in;
                        endcase
                    end
                    7'd108: begin
                        case (byte_address[1:0])
                            2'd0: word108[7:0] <= data_in;
                            2'd1: word108[15:8] <= data_in;
                            2'd2: word108[23:16] <= data_in;
                            2'd3: word108[31:24] <= data_in;
                        endcase
                    end
                    7'd109: begin
                        case (byte_address[1:0])
                            2'd0: word109[7:0] <= data_in;
                            2'd1: word109[15:8] <= data_in;
                            2'd2: word109[23:16] <= data_in;
                            2'd3: word109[31:24] <= data_in;
                        endcase
                    end
                    7'd110: begin
                        case (byte_address[1:0])
                            2'd0: word110[7:0] <= data_in;
                            2'd1: word110[15:8] <= data_in;
                            2'd2: word110[23:16] <= data_in;
                            2'd3: word110[31:24] <= data_in;
                        endcase
                    end
                    7'd111: begin
                        case (byte_address[1:0])
                            2'd0: word111[7:0] <= data_in;
                            2'd1: word111[15:8] <= data_in;
                            2'd2: word111[23:16] <= data_in;
                            2'd3: word111[31:24] <= data_in;
                        endcase
                    end
                    7'd112: begin
                        case (byte_address[1:0])
                            2'd0: word112[7:0] <= data_in;
                            2'd1: word112[15:8] <= data_in;
                            2'd2: word112[23:16] <= data_in;
                            2'd3: word112[31:24] <= data_in;
                        endcase
                    end
                    7'd113: begin
                        case (byte_address[1:0])
                            2'd0: word113[7:0] <= data_in;
                            2'd1: word113[15:8] <= data_in;
                            2'd2: word113[23:16] <= data_in;
                            2'd3: word113[31:24] <= data_in;
                        endcase
                    end
                    7'd114: begin
                        case (byte_address[1:0])
                            2'd0: word114[7:0] <= data_in;
                            2'd1: word114[15:8] <= data_in;
                            2'd2: word114[23:16] <= data_in;
                            2'd3: word114[31:24] <= data_in;
                        endcase
                    end
                    7'd115: begin
                        case (byte_address[1:0])
                            2'd0: word115[7:0] <= data_in;
                            2'd1: word115[15:8] <= data_in;
                            2'd2: word115[23:16] <= data_in;
                            2'd3: word115[31:24] <= data_in;
                        endcase
                    end
                    7'd116: begin
                        case (byte_address[1:0])
                            2'd0: word116[7:0] <= data_in;
                            2'd1: word116[15:8] <= data_in;
                            2'd2: word116[23:16] <= data_in;
                            2'd3: word116[31:24] <= data_in;
                        endcase
                    end
                    7'd117: begin
                        case (byte_address[1:0])
                            2'd0: word117[7:0] <= data_in;
                            2'd1: word117[15:8] <= data_in;
                            2'd2: word117[23:16] <= data_in;
                            2'd3: word117[31:24] <= data_in;
                        endcase
                    end
                    7'd118: begin
                        case (byte_address[1:0])
                            2'd0: word118[7:0] <= data_in;
                            2'd1: word118[15:8] <= data_in;
                            2'd2: word118[23:16] <= data_in;
                            2'd3: word118[31:24] <= data_in;
                        endcase
                    end
                    7'd119: begin
                        case (byte_address[1:0])
                            2'd0: word119[7:0] <= data_in;
                            2'd1: word119[15:8] <= data_in;
                            2'd2: word119[23:16] <= data_in;
                            2'd3: word119[31:24] <= data_in;
                        endcase
                    end
                    7'd120: begin
                        case (byte_address[1:0])
                            2'd0: word120[7:0] <= data_in;
                            2'd1: word120[15:8] <= data_in;
                            2'd2: word120[23:16] <= data_in;
                            2'd3: word120[31:24] <= data_in;
                        endcase
                    end
                    7'd121: begin
                        case (byte_address[1:0])
                            2'd0: word121[7:0] <= data_in;
                            2'd1: word121[15:8] <= data_in;
                            2'd2: word121[23:16] <= data_in;
                            2'd3: word121[31:24] <= data_in;
                        endcase
                    end
                    7'd122: begin
                        case (byte_address[1:0])
                            2'd0: word122[7:0] <= data_in;
                            2'd1: word122[15:8] <= data_in;
                            2'd2: word122[23:16] <= data_in;
                            2'd3: word122[31:24] <= data_in;
                        endcase
                    end
                    7'd123: begin
                        case (byte_address[1:0])
                            2'd0: word123[7:0] <= data_in;
                            2'd1: word123[15:8] <= data_in;
                            2'd2: word123[23:16] <= data_in;
                            2'd3: word123[31:24] <= data_in;
                        endcase
                    end
                    7'd124: begin
                        case (byte_address[1:0])
                            2'd0: word124[7:0] <= data_in;
                            2'd1: word124[15:8] <= data_in;
                            2'd2: word124[23:16] <= data_in;
                            2'd3: word124[31:24] <= data_in;
                        endcase
                    end
                    7'd125: begin
                        case (byte_address[1:0])
                            2'd0: word125[7:0] <= data_in;
                            2'd1: word125[15:8] <= data_in;
                            2'd2: word125[23:16] <= data_in;
                            2'd3: word125[31:24] <= data_in;
                        endcase
                    end
                    7'd126: begin
                        case (byte_address[1:0])
                            2'd0: word126[7:0] <= data_in;
                            2'd1: word126[15:8] <= data_in;
                            2'd2: word126[23:16] <= data_in;
                            2'd3: word126[31:24] <= data_in;
                        endcase
                    end
                    7'd127: begin
                        case (byte_address[1:0])
                            2'd0: word127[7:0] <= data_in;
                            2'd1: word127[15:8] <= data_in;
                            2'd2: word127[23:16] <= data_in;
                            2'd3: word127[31:24] <= data_in;
                        endcase
                    end
                    default: begin end
                endcase
            end
        end
    end
    // verilog_lint: waive always-comb
    always @(*) begin
        case (bank_address[8:2])
            7'd0: data_out = word0[8*byte_address[1:0] +: 8];
            7'd1: data_out = word1[8*byte_address[1:0] +: 8];
            7'd2: data_out = word2[8*byte_address[1:0] +: 8];
            7'd3: data_out = word3[8*byte_address[1:0] +: 8];
            7'd4: data_out = word4[8*byte_address[1:0] +: 8];
            7'd5: data_out = word5[8*byte_address[1:0] +: 8];
            7'd6: data_out = word6[8*byte_address[1:0] +: 8];
            7'd7: data_out = word7[8*byte_address[1:0] +: 8];
            7'd8: data_out = word8[8*byte_address[1:0] +: 8];
            7'd9: data_out = word9[8*byte_address[1:0] +: 8];
            7'd10: data_out = word10[8*byte_address[1:0] +: 8];
            7'd11: data_out = word11[8*byte_address[1:0] +: 8];
            7'd12: data_out = word12[8*byte_address[1:0] +: 8];
            7'd13: data_out = word13[8*byte_address[1:0] +: 8];
            7'd14: data_out = word14[8*byte_address[1:0] +: 8];
            7'd15: data_out = word15[8*byte_address[1:0] +: 8];
            7'd16: data_out = word16[8*byte_address[1:0] +: 8];
            7'd17: data_out = word17[8*byte_address[1:0] +: 8];
            7'd18: data_out = word18[8*byte_address[1:0] +: 8];
            7'd19: data_out = word19[8*byte_address[1:0] +: 8];
            7'd20: data_out = word20[8*byte_address[1:0] +: 8];
            7'd21: data_out = word21[8*byte_address[1:0] +: 8];
            7'd22: data_out = word22[8*byte_address[1:0] +: 8];
            7'd23: data_out = word23[8*byte_address[1:0] +: 8];
            7'd24: data_out = word24[8*byte_address[1:0] +: 8];
            7'd25: data_out = word25[8*byte_address[1:0] +: 8];
            7'd26: data_out = word26[8*byte_address[1:0] +: 8];
            7'd27: data_out = word27[8*byte_address[1:0] +: 8];
            7'd28: data_out = word28[8*byte_address[1:0] +: 8];
            7'd29: data_out = word29[8*byte_address[1:0] +: 8];
            7'd30: data_out = word30[8*byte_address[1:0] +: 8];
            7'd31: data_out = word31[8*byte_address[1:0] +: 8];
            7'd32: data_out = word32[8*byte_address[1:0] +: 8];
            7'd33: data_out = word33[8*byte_address[1:0] +: 8];
            7'd34: data_out = word34[8*byte_address[1:0] +: 8];
            7'd35: data_out = word35[8*byte_address[1:0] +: 8];
            7'd36: data_out = word36[8*byte_address[1:0] +: 8];
            7'd37: data_out = word37[8*byte_address[1:0] +: 8];
            7'd38: data_out = word38[8*byte_address[1:0] +: 8];
            7'd39: data_out = word39[8*byte_address[1:0] +: 8];
            7'd40: data_out = word40[8*byte_address[1:0] +: 8];
            7'd41: data_out = word41[8*byte_address[1:0] +: 8];
            7'd42: data_out = word42[8*byte_address[1:0] +: 8];
            7'd43: data_out = word43[8*byte_address[1:0] +: 8];
            7'd44: data_out = word44[8*byte_address[1:0] +: 8];
            7'd45: data_out = word45[8*byte_address[1:0] +: 8];
            7'd46: data_out = word46[8*byte_address[1:0] +: 8];
            7'd47: data_out = word47[8*byte_address[1:0] +: 8];
            7'd48: data_out = word48[8*byte_address[1:0] +: 8];
            7'd49: data_out = word49[8*byte_address[1:0] +: 8];
            7'd50: data_out = word50[8*byte_address[1:0] +: 8];
            7'd51: data_out = word51[8*byte_address[1:0] +: 8];
            7'd52: data_out = word52[8*byte_address[1:0] +: 8];
            7'd53: data_out = word53[8*byte_address[1:0] +: 8];
            7'd54: data_out = word54[8*byte_address[1:0] +: 8];
            7'd55: data_out = word55[8*byte_address[1:0] +: 8];
            7'd56: data_out = word56[8*byte_address[1:0] +: 8];
            7'd57: data_out = word57[8*byte_address[1:0] +: 8];
            7'd58: data_out = word58[8*byte_address[1:0] +: 8];
            7'd59: data_out = word59[8*byte_address[1:0] +: 8];
            7'd60: data_out = word60[8*byte_address[1:0] +: 8];
            7'd61: data_out = word61[8*byte_address[1:0] +: 8];
            7'd62: data_out = word62[8*byte_address[1:0] +: 8];
            7'd63: data_out = word63[8*byte_address[1:0] +: 8];
            7'd64: data_out = word64[8*byte_address[1:0] +: 8];
            7'd65: data_out = word65[8*byte_address[1:0] +: 8];
            7'd66: data_out = word66[8*byte_address[1:0] +: 8];
            7'd67: data_out = word67[8*byte_address[1:0] +: 8];
            7'd68: data_out = word68[8*byte_address[1:0] +: 8];
            7'd69: data_out = word69[8*byte_address[1:0] +: 8];
            7'd70: data_out = word70[8*byte_address[1:0] +: 8];
            7'd71: data_out = word71[8*byte_address[1:0] +: 8];
            7'd72: data_out = word72[8*byte_address[1:0] +: 8];
            7'd73: data_out = word73[8*byte_address[1:0] +: 8];
            7'd74: data_out = word74[8*byte_address[1:0] +: 8];
            7'd75: data_out = word75[8*byte_address[1:0] +: 8];
            7'd76: data_out = word76[8*byte_address[1:0] +: 8];
            7'd77: data_out = word77[8*byte_address[1:0] +: 8];
            7'd78: data_out = word78[8*byte_address[1:0] +: 8];
            7'd79: data_out = word79[8*byte_address[1:0] +: 8];
            7'd80: data_out = word80[8*byte_address[1:0] +: 8];
            7'd81: data_out = word81[8*byte_address[1:0] +: 8];
            7'd82: data_out = word82[8*byte_address[1:0] +: 8];
            7'd83: data_out = word83[8*byte_address[1:0] +: 8];
            7'd84: data_out = word84[8*byte_address[1:0] +: 8];
            7'd85: data_out = word85[8*byte_address[1:0] +: 8];
            7'd86: data_out = word86[8*byte_address[1:0] +: 8];
            7'd87: data_out = word87[8*byte_address[1:0] +: 8];
            7'd88: data_out = word88[8*byte_address[1:0] +: 8];
            7'd89: data_out = word89[8*byte_address[1:0] +: 8];
            7'd90: data_out = word90[8*byte_address[1:0] +: 8];
            7'd91: data_out = word91[8*byte_address[1:0] +: 8];
            7'd92: data_out = word92[8*byte_address[1:0] +: 8];
            7'd93: data_out = word93[8*byte_address[1:0] +: 8];
            7'd94: data_out = word94[8*byte_address[1:0] +: 8];
            7'd95: data_out = word95[8*byte_address[1:0] +: 8];
            7'd96: data_out = word96[8*byte_address[1:0] +: 8];
            7'd97: data_out = word97[8*byte_address[1:0] +: 8];
            7'd98: data_out = word98[8*byte_address[1:0] +: 8];
            7'd99: data_out = word99[8*byte_address[1:0] +: 8];
            7'd100: data_out = word100[8*byte_address[1:0] +: 8];
            7'd101: data_out = word101[8*byte_address[1:0] +: 8];
            7'd102: data_out = word102[8*byte_address[1:0] +: 8];
            7'd103: data_out = word103[8*byte_address[1:0] +: 8];
            7'd104: data_out = word104[8*byte_address[1:0] +: 8];
            7'd105: data_out = word105[8*byte_address[1:0] +: 8];
            7'd106: data_out = word106[8*byte_address[1:0] +: 8];
            7'd107: data_out = word107[8*byte_address[1:0] +: 8];
            7'd108: data_out = word108[8*byte_address[1:0] +: 8];
            7'd109: data_out = word109[8*byte_address[1:0] +: 8];
            7'd110: data_out = word110[8*byte_address[1:0] +: 8];
            7'd111: data_out = word111[8*byte_address[1:0] +: 8];
            7'd112: data_out = word112[8*byte_address[1:0] +: 8];
            7'd113: data_out = word113[8*byte_address[1:0] +: 8];
            7'd114: data_out = word114[8*byte_address[1:0] +: 8];
            7'd115: data_out = word115[8*byte_address[1:0] +: 8];
            7'd116: data_out = word116[8*byte_address[1:0] +: 8];
            7'd117: data_out = word117[8*byte_address[1:0] +: 8];
            7'd118: data_out = word118[8*byte_address[1:0] +: 8];
            7'd119: data_out = word119[8*byte_address[1:0] +: 8];
            7'd120: data_out = word120[8*byte_address[1:0] +: 8];
            7'd121: data_out = word121[8*byte_address[1:0] +: 8];
            7'd122: data_out = word122[8*byte_address[1:0] +: 8];
            7'd123: data_out = word123[8*byte_address[1:0] +: 8];
            7'd124: data_out = word124[8*byte_address[1:0] +: 8];
            7'd125: data_out = word125[8*byte_address[1:0] +: 8];
            7'd126: data_out = word126[8*byte_address[1:0] +: 8];
            7'd127: data_out = word127[8*byte_address[1:0] +: 8];
            default: data_out = 8'd0;
        endcase
        if (load_length)
            data_out = program_length;
        case (pc)
            8'd0: instruction = word0;
            8'd1: instruction = word1;
            8'd2: instruction = word2;
            8'd3: instruction = word3;
            8'd4: instruction = word4;
            8'd5: instruction = word5;
            8'd6: instruction = word6;
            8'd7: instruction = word7;
            8'd8: instruction = word8;
            8'd9: instruction = word9;
            8'd10: instruction = word10;
            8'd11: instruction = word11;
            8'd12: instruction = word12;
            8'd13: instruction = word13;
            8'd14: instruction = word14;
            8'd15: instruction = word15;
            8'd16: instruction = word16;
            8'd17: instruction = word17;
            8'd18: instruction = word18;
            8'd19: instruction = word19;
            8'd20: instruction = word20;
            8'd21: instruction = word21;
            8'd22: instruction = word22;
            8'd23: instruction = word23;
            8'd24: instruction = word24;
            8'd25: instruction = word25;
            8'd26: instruction = word26;
            8'd27: instruction = word27;
            8'd28: instruction = word28;
            8'd29: instruction = word29;
            8'd30: instruction = word30;
            8'd31: instruction = word31;
            8'd32: instruction = word32;
            8'd33: instruction = word33;
            8'd34: instruction = word34;
            8'd35: instruction = word35;
            8'd36: instruction = word36;
            8'd37: instruction = word37;
            8'd38: instruction = word38;
            8'd39: instruction = word39;
            8'd40: instruction = word40;
            8'd41: instruction = word41;
            8'd42: instruction = word42;
            8'd43: instruction = word43;
            8'd44: instruction = word44;
            8'd45: instruction = word45;
            8'd46: instruction = word46;
            8'd47: instruction = word47;
            8'd48: instruction = word48;
            8'd49: instruction = word49;
            8'd50: instruction = word50;
            8'd51: instruction = word51;
            8'd52: instruction = word52;
            8'd53: instruction = word53;
            8'd54: instruction = word54;
            8'd55: instruction = word55;
            8'd56: instruction = word56;
            8'd57: instruction = word57;
            8'd58: instruction = word58;
            8'd59: instruction = word59;
            8'd60: instruction = word60;
            8'd61: instruction = word61;
            8'd62: instruction = word62;
            8'd63: instruction = word63;
            8'd64: instruction = word64;
            8'd65: instruction = word65;
            8'd66: instruction = word66;
            8'd67: instruction = word67;
            8'd68: instruction = word68;
            8'd69: instruction = word69;
            8'd70: instruction = word70;
            8'd71: instruction = word71;
            8'd72: instruction = word72;
            8'd73: instruction = word73;
            8'd74: instruction = word74;
            8'd75: instruction = word75;
            8'd76: instruction = word76;
            8'd77: instruction = word77;
            8'd78: instruction = word78;
            8'd79: instruction = word79;
            8'd80: instruction = word80;
            8'd81: instruction = word81;
            8'd82: instruction = word82;
            8'd83: instruction = word83;
            8'd84: instruction = word84;
            8'd85: instruction = word85;
            8'd86: instruction = word86;
            8'd87: instruction = word87;
            8'd88: instruction = word88;
            8'd89: instruction = word89;
            8'd90: instruction = word90;
            8'd91: instruction = word91;
            8'd92: instruction = word92;
            8'd93: instruction = word93;
            8'd94: instruction = word94;
            8'd95: instruction = word95;
            8'd96: instruction = word96;
            8'd97: instruction = word97;
            8'd98: instruction = word98;
            8'd99: instruction = word99;
            8'd100: instruction = word100;
            8'd101: instruction = word101;
            8'd102: instruction = word102;
            8'd103: instruction = word103;
            8'd104: instruction = word104;
            8'd105: instruction = word105;
            8'd106: instruction = word106;
            8'd107: instruction = word107;
            8'd108: instruction = word108;
            8'd109: instruction = word109;
            8'd110: instruction = word110;
            8'd111: instruction = word111;
            8'd112: instruction = word112;
            8'd113: instruction = word113;
            8'd114: instruction = word114;
            8'd115: instruction = word115;
            8'd116: instruction = word116;
            8'd117: instruction = word117;
            8'd118: instruction = word118;
            8'd119: instruction = word119;
            8'd120: instruction = word120;
            8'd121: instruction = word121;
            8'd122: instruction = word122;
            8'd123: instruction = word123;
            8'd124: instruction = word124;
            8'd125: instruction = word125;
            8'd126: instruction = word126;
            8'd127: instruction = word127;
            default: instruction = 32'd0;
        endcase
    end
    assign instruction_valid = program_ready && (pc < program_length) && (pc < 8'd128);
endmodule
`default_nettype wire
