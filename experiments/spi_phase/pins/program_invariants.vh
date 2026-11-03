/* SPDX-License-Identifier: Apache-2.0 */
    function automatic [31:0] expected_word(input integer index);
        case (index)
            0: expected_word=32'h65000008;
            1: expected_word=32'ha0486000 | (msb_first ? 32'h10000000 : 32'd0);
            2: expected_word=32'h40000017;
            3: expected_word=32'h00040404;
            4: expected_word=32'ha0500008 | (msb_first ? 32'h10000000 : 32'd0);
            5: expected_word=32'h40000015;
            6: expected_word=32'h000c0c08;
            default: expected_word=32'h80000000;
        endcase
    endfunction
    reg [4:0] e_pc;
    reg [1:0] e_state;
    reg [15:0] e_wait, e_period;
    reg [7:0] e_gpio, e_oe, e_remaining, e_tx, e_rx;
    reg [2:0] e_done;
    reg e_loop, e_active, e_prepared, e_order;
    reg [4:0] e_start, e_end;
    reg [2:0] e_rxpin;
    integer n,t;
    always @(*) begin
        n=cycle>=9'd37 && cycle<=9'd441 ? cycle-9'd37 : 0;
        e_pc=0; e_state=0; e_wait=0; e_period=0;
        e_gpio=0; e_oe=0; e_remaining=0; e_tx=0; e_rx=0; e_done=0;
        e_loop=0; e_active=0; e_prepared=0; e_order=0; e_start=0; e_end=0; e_rxpin=0;
        t=0;
        if (n>=1) begin
            e_pc=1; e_loop=n<401; e_remaining=n==1 ? 8'd8 : 8'd0;
            e_start=1; e_end=6;
        end
        if (n>=2) begin
            e_oe=13; e_active=n<379; e_order=msb_first; e_rxpin=1;
        end
        for (integer k=0;k<8;k=k+1) begin
            if (n>=2+50*k) begin
                e_gpio[0]=msb_first ? tx_byte[7-k] : tx_byte[k];
                e_tx=msb_first ? tx_byte << (k+1) : tx_byte >> (k+1);
            end
            if (n>=27+50*k && n<52+50*k) e_gpio[2]=1'b1;
            if (n>=29+50*k) begin
                e_rx=msb_first ? rx_byte >> (7-k) : rx_byte << (7-k);
                e_done=k==7 ? 3'd0 : k+1;
            end
            if (n>=2+50*k && n<52+50*k) begin
                t=n-(2+50*k);
                e_remaining=t==49 ? 7-k : 8-k;
                e_prepared=t<27;
                if (t<=23) e_pc=2;
                else if (t==24) e_pc=3;
                else if (t<=26) e_pc=4;
                else if (t<=48) e_pc=5;
                else e_pc=k==7 ? 6 : 1;
                if (t>=1 && t<=23) begin e_state=1; e_wait=24-t; end
                if (t==26) begin e_state=1; e_wait=1; e_period=1; end
                if (t>=28 && t<=48) begin e_state=1; e_wait=49-t; end
            end
        end
        if (n>=402) begin e_gpio[3]=1'b1; e_pc=7; end
        if (n>=403) e_state=2;
    end
    reg [7:0] reference_meta, reference_sampled;
    reg history1=1'b0, history2=1'b0;
    always @(posedge clk) begin
        history1<=1'b1; history2<=history1;
        if (!rst_n) begin reference_meta<=0; reference_sampled<=0; end
        else begin reference_meta<=uio_in; reference_sampled<=reference_meta; end
        assert(cycle<=9'd443);
        if (past_valid) begin
            assert(f_formal_sync_meta==reference_meta && f_sampled_inputs==reference_sampled);
            assert(f_program_ready==(cycle>=9'd34 && cycle<=9'd441));
            assert(f_program_length==((cycle>=9'd34 && cycle<=9'd441) ? 4'd8 : 4'd0));
            for (integer b=0;b<32;b=b+1)
                assert(f_formal_program_bits[8*b +: 8] ==
                    ((cycle>=b+2 && cycle<=9'd441) ? ((expected_word(b/4) >> (8*(b%4))) & 8'hff) : 8'd0));
            assert(f_tx_payload==((cycle>=9'd35 && cycle<=9'd441) ? tx_byte : 8'd0));
            assert(f_tx_payload_alt==8'd0);
            assert(f_rx_valid==(cycle>=9'd416 && cycle<=9'd441));
            assert(f_rx_result==((cycle>=9'd416 && cycle<=9'd441) ? rx_byte : 8'd0));
            assert(f_pc==e_pc && f_state==e_state && f_wait_left==e_wait);
            assert(f_gpio_value==e_gpio && f_gpio_oe==e_oe);
            assert(f_loop_active_status==e_loop && f_loop_remaining_status==e_remaining);
            assert(f_loop_start_status==e_start && f_loop_end_status==e_end);
            assert(!f_wait_is_input_status && !f_wait_pin_status && !f_wait_level_status && !f_wait_timeout_skip_status);
            assert(f_shift_active_status==e_active && f_formal_phase_active==e_active);
            assert(f_formal_phase_prepared==e_prepared && f_shift_bits_done_status==e_done);
            assert(f_shift_msb_first_status==e_order && f_shift_tx_pin_status==0 && f_shift_rx_pin_status==e_rxpin);
            assert(f_shift_tx_data_status==e_tx && f_shift_rx_data_status==e_rx);
            assert(f_shift_period_status==e_period && !f_shift_tx_slot_status);
            assert(f_shift_result_write==(cycle==9'd415));
            if (f_shift_result_write) assert(f_shift_result_data==rx_byte);
            for (integer k=0;k<8;k=k+1)
                if (cycle>=9'd37 && cycle<=9'd439 && exec_edge==29+50*k)
                    assert(f_sampled_inputs[1]==(msb_first ? rx_byte[7-k] : rx_byte[k]));
        end
`ifdef FORMAL
        if (history1 && $past(rst_n)) assert(f_formal_sync_meta==$past(uio_in));
        if (history2 && $past(rst_n) && $past($past(rst_n))) assert(f_sampled_inputs==$past($past(uio_in)));
`endif
    end
