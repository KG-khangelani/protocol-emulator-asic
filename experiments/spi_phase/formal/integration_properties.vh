/* SPDX-License-Identifier: Apache-2.0 */
    reg integration_past_valid = 1'b0;
    (* anyconst *) reg [4:0] watched_address;
    reg [7:0] watched_byte;
    reg [7:0] reference_tx, reference_alt, reference_rx;
    reg reference_valid;
    reg [7:0] reference_sync0, reference_sync1;
    wire public_byte_write = ena && ui_in[7:5] == 3'b110;
    wire public_length_write = ena && ui_in == 8'he0;
    wire public_tx_write = ena && ui_in == 8'he1;
    wire public_alt_write = ena && ui_in == 8'he4;
    wire public_length_valid = uio_in >= 8'd1 && uio_in <= 8'd8;
    wire [7:0] expected_phase_rx = shift_msb_first_status ?
        {shift_rx_data_status[6:0],sampled_inputs[shift_rx_pin_status]} :
        {sampled_inputs[shift_rx_pin_status],shift_rx_data_status[7:1]};
    wire phase_sample_shape = instruction[31:29] == 3'b101 && !instruction[21] &&
        instruction[20:19] == 2'd2 && instruction[2:0] == 3'd0 &&
        instruction[27:25] != instruction[24:22] &&
        instruction[28] == shift_msb_first_status &&
        instruction[27:25] == shift_tx_pin_status && instruction[24:22] == shift_rx_pin_status;
    wire phase_completion = rst_n && program_ready && !ui_in[7] && ena &&
        formal_phase_active && formal_phase_prepared && shift_active_status &&
        shift_bits_done_status == 3'd7 &&
        ((state == 2'd0 && instruction_valid && phase_sample_shape && instruction[18:3] == 16'd0) ||
         (state == 2'd1 && shift_period_status == 16'd1 && wait_left == 16'd1));

    always @(*) if (integration_past_valid) begin
        assert(formal_program_bits[8*watched_address +: 8] == watched_byte);
        assert(tx_payload == reference_tx && tx_payload_alt == reference_alt);
        assert(rx_result == reference_rx && rx_valid == reference_valid);
        assert(formal_sync_meta == reference_sync0 && sampled_inputs == reference_sync1);
        assert(instruction_valid == (program_ready && pc < {1'b0,program_length} && pc < 5'd8));
        if (pc < 5'd8) assert(instruction == formal_program_bits[32*pc[2:0] +: 32]);
        if (ui_in[7] || !program_ready || !rst_n || !ena) assert(!shift_result_write);
        if (formal_phase_active || shift_period_status == 16'd1)
            assert(shift_result_write == phase_completion);
        if (phase_completion) assert(shift_result_data == expected_phase_rx);
        if (ui_in[7] && !ui_in[6] && !ui_in[5] && ui_in[4:0] == watched_address)
            assert(uio_out == watched_byte);
        if (ui_in[7] && !ui_in[6] && ui_in[5]) begin
            case (ui_in[4:0])
                5'd0: assert(uio_out == {4'd0,program_length});
                5'd1: assert(uio_out == reference_tx);
                5'd2: assert(uio_out == reference_rx);
                5'd3: assert(uio_out == {7'd0,reference_valid});
                5'd4: assert(uio_out == reference_alt);
                default: assert(uio_out == 8'd0);
            endcase
        end
        if (ui_in[7:5] == 3'b011) begin
            case (ui_in[4:0])
                5'd1: assert(uo_out == reference_tx);
                5'd2: assert(uo_out == reference_rx);
                5'd3: assert(uo_out == {7'd0,reference_valid});
                5'd4: assert(uo_out == reference_alt);
                default: assert(uo_out == 8'd0);
            endcase
        end
    end

    always @(posedge clk) begin
        integration_past_valid <= 1'b1;
        if (!integration_past_valid) assume(!rst_n);
        if (!rst_n) begin
            watched_byte <= 8'd0;
            reference_tx <= 8'd0; reference_alt <= 8'd0;
            reference_rx <= 8'd0; reference_valid <= 1'b0;
            reference_sync0 <= 8'd0; reference_sync1 <= 8'd0;
        end else begin
            if (public_byte_write && ui_in[4:0] == watched_address) watched_byte <= uio_in;
            if (public_tx_write) reference_tx <= uio_in;
            if (public_alt_write) reference_alt <= uio_in;
            if (shift_result_write) reference_rx <= shift_result_data;
            if (public_tx_write || public_alt_write) reference_valid <= 1'b0;
            else if (shift_result_write) reference_valid <= 1'b1;
            reference_sync0 <= uio_in; reference_sync1 <= reference_sync0;
        end
        if (integration_past_valid) begin
            if (!$past(rst_n)) begin
                assert(formal_program_bits == 256'd0);
                assert(!program_ready && program_length == 4'd0);
            end else if ($past(public_length_write)) begin
                assert(program_ready == $past(public_length_valid));
                assert(program_length == ($past(public_length_valid) ? $past(uio_in[3:0]) : 4'd0));
            end else begin
                assert(program_length == $past(program_length));
                assert(program_ready == ($past(public_byte_write) ? 1'b0 : $past(program_ready)));
            end
            if (!$past(rst_n) || $past(ui_in[7]) || !$past(program_ready))
                assert(integrated_engine_state == 110'd0);
            if ($past(rst_n) && $past(ui_in[7]) && !$past(public_tx_write) && !$past(public_alt_write)) begin
                assert(rx_result == $past(rx_result) && rx_valid == $past(rx_valid));
            end
        end
    end
