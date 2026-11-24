// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module tt_um_khangelani_protocol_emulator (
    input wire clk, input wire rst_n, input wire ena,
    input wire [7:0] ui_in, output wire [7:0] uo_out,
    input wire [7:0] uio_in, output wire [7:0] uio_out, output wire [7:0] uio_oe
);
    // The host holds ui_in[0] high during initialization and low to run.
    localparam [15:0] COMMAND_BITS = 16'hb4cc;
    localparam [14:0] RESET_LOW_CYCLES = 15'd25000;
    localparam [3:0] IDLE = 0, RESET_LOW = 1, PRESENCE = 2, RECOVERY = 3,
        WRITE_LOW = 4, WRITE_HIGH = 5, READ_LOW = 6, READ_SAMPLE = 7,
        READ_END = 8, DONE = 9;

    reg dq_meta, dq_sync;
    reg [3:0] state;
    reg [14:0] remaining;
    reg [3:0] bit_index;
    reg [1:0] result;
    reg drive_low;
    wire [3:0] next_bit = bit_index + 4'd1;
    wire terminal = state == DONE;
    assign uo_out = terminal ? 8'ha0 : 8'h20;
    assign uio_out = {5'd0, result, 1'b0};
    assign uio_oe = {5'd0, terminal, terminal, drive_low};

    // All durations run on the single 50 MHz system clock.
    function [14:0] write_low;
        input bit_value;
        begin
            write_low = bit_value ? 15'd300 : 15'd3100;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq_meta <= 1'b0;
            dq_sync <= 1'b0;
        end else begin
            dq_meta <= uio_in[0];
            dq_sync <= dq_meta;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            remaining <= 15'd0;
            bit_index <= 4'd0;
            result <= 2'd0;
            drive_low <= 1'b0;
        end else if (ena) begin
            if (remaining != 0) begin
                remaining <= remaining - 15'd1;
            end else begin
                case (state)
                    IDLE: if (!ui_in[0]) begin
                        if (dq_sync) begin
                            drive_low <= 1'b1;
                            remaining <= RESET_LOW_CYCLES - 15'd1;
                            state <= RESET_LOW;
                        end else begin
                            result <= 2'd3;
                            state <= DONE;
                        end
                    end
                    RESET_LOW: begin
                        drive_low <= 1'b0;
                        remaining <= 15'd3499;
                        state <= PRESENCE;
                    end
                    PRESENCE: if (dq_sync) begin
                        result <= 2'd3;
                        state <= DONE;
                    end else begin
                        remaining <= 15'd21499;
                        state <= RECOVERY;
                    end
                    RECOVERY: if (dq_sync) begin
                        drive_low <= 1'b1;
                        remaining <= write_low(COMMAND_BITS[0]) - 15'd1;
                        state <= WRITE_LOW;
                    end else begin
                        result <= 2'd3;
                        state <= DONE;
                    end
                    WRITE_LOW: begin
                        drive_low <= 1'b0;
                        remaining <= 15'd3499 - write_low(COMMAND_BITS[bit_index]);
                        state <= WRITE_HIGH;
                    end
                    WRITE_HIGH: begin
                        drive_low <= 1'b1;
                        if (bit_index == 4'd15) begin
                            remaining <= 15'd299;
                            state <= READ_LOW;
                        end else begin
                            bit_index <= next_bit;
                            remaining <= write_low(COMMAND_BITS[next_bit]) - 15'd1;
                            state <= WRITE_LOW;
                        end
                    end
                    READ_LOW: begin
                        drive_low <= 1'b0;
                        remaining <= 15'd399;
                        state <= READ_SAMPLE;
                    end
                    READ_SAMPLE: begin
                        result <= dq_sync ? 2'd1 : 2'd2;
                        remaining <= 15'd2799;
                        state <= READ_END;
                    end
                    READ_END: state <= DONE;
                    DONE: state <= DONE;
                    default: begin
                        drive_low <= 1'b0;
                        result <= 2'd3;
                        state <= DONE;
                    end
                endcase
            end
        end
    end
endmodule

`default_nettype wire
