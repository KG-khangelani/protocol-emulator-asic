/* SPDX-License-Identifier: Apache-2.0 */
`default_nettype none

module m1_data_store_formal (
    input wire clk, input wire rst_n, input wire ena,
    input wire register_select, input wire register_write,
    input wire [4:0] register_address, input wire [7:0] data_in,
    input wire shift_result_write, input wire [7:0] shift_result_data
);
    wire [7:0] data_out;
    wire [7:0] tx_payload;
    wire [7:0] tx_payload_alt;
    wire [7:0] rx_result;
    wire rx_valid;
    reg past_valid = 1'b0;
    reg reset_seen = 1'b0;
    wire payload_write = ena && register_select && register_write &&
                         (register_address == 5'd1);
    wire payload_alt_write = ena && register_select && register_write &&
                             (register_address == 5'd4);

    m1_data_store dut (
        .clk(clk), .rst_n(rst_n), .ena(ena),
        .register_select(register_select), .register_write(register_write),
        .register_address(register_address), .data_in(data_in),
        .shift_result_write(shift_result_write),
        .shift_result_data(shift_result_data), .data_out(data_out),
        .tx_payload(tx_payload), .tx_payload_alt(tx_payload_alt),
        .rx_result(rx_result), .rx_valid(rx_valid)
    );

    always @(*) begin
        case (register_address)
            5'd1: assert (data_out == tx_payload);
            5'd2: assert (data_out == rx_result);
            5'd3: assert (data_out == {7'd0, rx_valid});
            5'd4: assert (data_out == tx_payload_alt);
            default: assert (data_out == 8'd0);
        endcase
    end

    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!rst_n)
            reset_seen <= 1'b1;
        if (past_valid) begin
            if (!$past(rst_n)) begin
                assert (tx_payload == 8'd0 && tx_payload_alt == 8'd0 &&
                        rx_result == 8'd0 && !rx_valid);
            end else if ($past(reset_seen)) begin
                if ($past(payload_write)) begin
                    assert (tx_payload == $past(data_in));
                    assert (!rx_valid);
                end else begin
                    assert (tx_payload == $past(tx_payload));
                end
                if ($past(payload_alt_write))
                    assert (tx_payload_alt == $past(data_in));
                else
                    assert (tx_payload_alt == $past(tx_payload_alt));
                assert (rx_valid == (($past(payload_write) ||
                                      $past(payload_alt_write)) ? 1'b0 :
                                     ($past(shift_result_write) ?
                                      1'b1 : $past(rx_valid))));
                if ($past(shift_result_write))
                    assert (rx_result == $past(shift_result_data));
                else
                    assert (rx_result == $past(rx_result));
            end
        end
        cover (reset_seen && tx_payload == 8'ha5);
        cover (reset_seen && tx_payload_alt == 8'h5a);
        cover (reset_seen && rx_valid && rx_result == 8'h3c);
    end
endmodule

`default_nettype wire
