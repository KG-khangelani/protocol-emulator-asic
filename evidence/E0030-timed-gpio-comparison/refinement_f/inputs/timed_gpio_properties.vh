    // General timed SET; issue and completion are distinct accepted edges.
`ifdef VARIANT_F
    wire [15:0] gpio_delay={11'd0,instruction[28:24]};
    wire gpio_before=instruction[29];
`else
    wire [15:0] gpio_delay={10'd0,instruction[29:24]};
    wire gpio_before=1'b0;
`endif
    wire set_issue=rst_n && ena && run && instruction_valid && instruction[31:30]==0;
    wire [7:0] set_value=(gpio_value & ~instruction[23:16]) | (instruction[7:0] & instruction[23:16]);
    wire [7:0] set_oe=(gpio_oe & ~instruction[23:16]) | (instruction[15:8] & instruction[23:16]);
    wire gpio_wait=waiting && shift_period_status==0 && !wait_is_input_status;
    reg saw_gpio_pause=0;
    always @(posedge clk) begin
        if(!rst_n) saw_gpio_pause<=0;
        else if(gpio_wait && !ena) saw_gpio_pause<=1;
        if(past_valid) begin
`ifdef VARIANT_F
            assert(!formal_gpio_pending || (gpio_wait && wait_left>0));
`endif
            if($past(rst_n && ena) && !$past(state[1])) begin
                if($past(set_issue)) begin
                    if($past(gpio_delay)==0) begin
                        assert(state==0 && wait_left==0); assert_advance();
                    end else begin
                        assert(state==1 && pc==$past(pc) && !wait_is_input_status && shift_period_status==0);
`ifdef WRONG_COUNT
                        assert(wait_left==$past(gpio_delay)+16'd1);
`else
                        assert(wait_left==$past(gpio_delay));
`endif
                        assert(loop_active_status==$past(loop_active_status) && loop_remaining_status==$past(loop_remaining_status));
                    end
                    if($past(gpio_before && gpio_delay!=0)) begin
                        assert(gpio_value==$past(gpio_value) && gpio_oe==$past(gpio_oe));
                    end else begin
`ifdef WRONG_UPDATE
                        assert(gpio_value==($past(set_value) ^ ($past(gpio_delay)!=0 ? 8'd1 : 8'd0)));
`else
                        assert(gpio_value==$past(set_value));
`endif
                        assert(gpio_oe==$past(set_oe));
                    end
                    assert(gpio_phase_state==$past(gpio_phase_state));
`ifdef VARIANT_F
                    assert(formal_gpio_pending==$past(gpio_before && gpio_delay!=0));
                    if($past(gpio_before && gpio_delay!=0)) begin
                        assert(formal_gpio_pending_value==$past(set_value) && formal_gpio_pending_oe==$past(set_oe));
                    end else begin
                        assert(formal_gpio_pending_value==$past(formal_gpio_pending_value));
                        assert(formal_gpio_pending_oe==$past(formal_gpio_pending_oe));
                    end
`endif
                end
                if($past(gpio_wait)) begin
                    assert(gpio_phase_state==$past(gpio_phase_state));
                    if($past(wait_left)>1) begin
                        assert(state==1 && pc==$past(pc) && wait_left==$past(wait_left)-16'd1);
                        assert(loop_active_status==$past(loop_active_status) && loop_remaining_status==$past(loop_remaining_status));
                    end else begin assert(state==0 && wait_left==0); assert_advance(); end
`ifdef VARIANT_F
                    if($past(formal_gpio_pending && wait_left<=1)) begin
                        assert(gpio_value==$past(formal_gpio_pending_value) && gpio_oe==$past(formal_gpio_pending_oe));
                        assert(!formal_gpio_pending);
                    end else begin
                        assert(gpio_value==$past(gpio_value) && gpio_oe==$past(gpio_oe));
                        assert(formal_gpio_pending==$past(formal_gpio_pending));
                    end
                    assert(formal_gpio_pending_value==$past(formal_gpio_pending_value));
                    assert(formal_gpio_pending_oe==$past(formal_gpio_pending_oe));
`else
                    assert(gpio_value==$past(gpio_value) && gpio_oe==$past(gpio_oe));
`endif
                end
            end
            if(set_issue || (rst_n && ena && gpio_wait)) assert(!shift_result_write);
            cover($past(set_issue && gpio_delay==MAX_DELAY) && gpio_wait && wait_left==MAX_DELAY);
            cover($past(gpio_wait && wait_left==1 && rst_n && ena) && state==0 && saw_gpio_pause);
            cover($past(gpio_wait && !rst_n) && all_state==0);
`ifdef VARIANT_F
            cover(formal_gpio_pending && wait_left==31);
            cover($past(formal_gpio_pending && wait_left==1 && rst_n && ena) && state==0);
`else
            cover($past(drive && instruction[2:0]==7) && gpio_wait && wait_left==28);
`endif
        end
    end
