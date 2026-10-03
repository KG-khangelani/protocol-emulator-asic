/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_engine (
    input wire clk, input wire rst_n, input wire ena,
    input wire [31:0] instruction, input wire instruction_valid,
    input wire [7:0] sampled_inputs,
    output reg [4:0] pc, output reg [1:0] state,
    output reg [15:0] wait_left,
    output reg [7:0] gpio_value, output reg [7:0] gpio_oe,
    output wire wait_is_input_status, output wire [2:0] wait_pin_status,
    output wire wait_level_status, output wire wait_timeout_skip_status
);
    localparam reg [1:0] Run=2'b00, Waiting=2'b01, Halted=2'b10, Faulted=2'b11;
    localparam reg [1:0] OpSet=2'b00, OpWait=2'b01, OpHalt=2'b10, OpWaitPin=2'b11;
    reg wait_is_input;
    reg [2:0] wait_pin;
    reg wait_level;
    reg wait_timeout_skip;
    wire [1:0] opcode = instruction[31:30];
    wire set_valid = (instruction[29:24] == 6'b0);
    wire wait_valid = (instruction[29:16] == 14'b0);
    wire halt_valid = (instruction[29:0] == 30'b0);
    wire wait_pin_valid = (instruction[24:16] == 9'b0);
    wire selected_input = sampled_inputs[instruction[29:27]];
    wire latched_input = sampled_inputs[wait_pin];
    assign wait_is_input_status = wait_is_input;
    assign wait_pin_status = wait_pin;
    assign wait_level_status = wait_level;
    assign wait_timeout_skip_status = wait_timeout_skip;

    always @(posedge clk) begin
        if (!rst_n) begin
            pc <= 5'd0; state <= Run; wait_left <= 16'd0;
            gpio_value <= 8'd0; gpio_oe <= 8'd0;
            wait_is_input <= 1'b0; wait_pin <= 3'd0; wait_level <= 1'b0;
            wait_timeout_skip <= 1'b0;
        end else if (ena) begin
            case (state)
                Halted: begin end
                Faulted: begin end
                Waiting: begin
                    if (wait_is_input && (latched_input == wait_level)) begin
                        wait_left <= 16'd0; pc <= pc + 5'd1; state <= Run;
                        wait_is_input <= 1'b0;
                    end else if (wait_is_input && (wait_left == 16'd1)) begin
                        wait_left <= 16'd0; wait_is_input <= 1'b0;
                        if (wait_timeout_skip) begin
                            pc <= pc + 5'd2; state <= Run;
                        end else
                            state <= Faulted;
                    end else if (wait_left > 16'd1)
                        wait_left <= wait_left - 16'd1;
                    else begin
                        wait_left <= 16'd0; pc <= pc + 5'd1; state <= Run;
                    end
                end
                default: begin
                    if (!instruction_valid) begin
                        state <= Faulted; wait_left <= 16'd0;
                    end else begin
                        case (opcode)
                            OpSet: begin
                                if (!set_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else begin
                                    gpio_value <= (gpio_value & ~instruction[23:16]) |
                                                  (instruction[7:0] & instruction[23:16]);
                                    gpio_oe <= (gpio_oe & ~instruction[23:16]) |
                                               (instruction[15:8] & instruction[23:16]);
                                    pc <= pc + 5'd1; wait_left <= 16'd0;
                                end
                            end
                            OpWait: begin
                                wait_is_input <= 1'b0;
                                if (!wait_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    pc <= pc + 5'd1; wait_left <= 16'd0;
                                end else begin
                                    state <= Waiting; wait_left <= instruction[15:0];
                                end
                            end
                            OpHalt: begin
                                wait_is_input <= 1'b0;
                                state <= halt_valid ? Halted : Faulted;
                                wait_left <= 16'd0;
                            end
                            OpWaitPin: begin
                                if (!wait_pin_valid) begin
                                    state <= Faulted; wait_left <= 16'd0;
                                end else if (selected_input == instruction[26]) begin
                                    pc <= pc + 5'd1; wait_left <= 16'd0;
                                end else if (instruction[15:0] == 16'd0) begin
                                    wait_left <= 16'd0;
                                    if (instruction[25])
                                        pc <= pc + 5'd2;
                                    else
                                        state <= Faulted;
                                end else begin
                                    state <= Waiting; wait_left <= instruction[15:0];
                                    wait_is_input <= 1'b1;
                                    wait_pin <= instruction[29:27];
                                    wait_level <= instruction[26];
                                    wait_timeout_skip <= instruction[25];
                                end
                            end
                            default: begin
                                state <= Faulted; wait_left <= 16'd0;
                                wait_is_input <= 1'b0;
                            end
                        endcase
                    end
                end
            endcase
        end
    end
endmodule

`default_nettype wire
