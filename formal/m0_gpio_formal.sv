/*
 * SPDX-License-Identifier: Apache-2.0
 * M0 public-pin formal contract and ignored-input self-composition.
 */
`default_nettype none

module m0_gpio_formal (
    input wire       clk,
    input wire       rst_n,
    input wire       ena,
    input wire [7:0] ui_in_a,
    input wire [7:0] uio_in_a,
    input wire [7:0] ui_in_b,
    input wire [7:0] uio_in_b
);
    wire [7:0] uo_out_a;
    wire [7:0] uio_out_a;
    wire [7:0] uio_oe_a;
    wire [7:0] uo_out_b;
    wire [7:0] uio_out_b;
    wire [7:0] uio_oe_b;

    tt_um_khangelani_protocol_emulator dut_a (
        .ui_in(ui_in_a),
        .uo_out(uo_out_a),
        .uio_in(uio_in_a),
        .uio_out(uio_out_a),
        .uio_oe(uio_oe_a),
        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );

    tt_um_khangelani_protocol_emulator dut_b (
        .ui_in(ui_in_b),
        .uo_out(uo_out_b),
        .uio_in(uio_in_b),
        .uio_out(uio_out_b),
        .uio_oe(uio_oe_b),
        .ena(ena),
        .clk(clk),
        .rst_n(rst_n)
    );

    reg past_valid = 1'b0;
    reg reset_seen = 1'b0;

`ifdef M0_COVER
    // The cover task requests one readable witness: reset once, then run. This
    // assumption is never compiled into the exhaustive safety proof.
    reg cover_started = 1'b0;
    always @(posedge clk) begin
        if (!cover_started) begin
            assume (!rst_n);
            cover_started <= 1'b1;
        end else begin
            assume (rst_n);
            assume (ena);
        end
    end
`endif

    always @(posedge clk) begin
        past_valid <= 1'b1;
        if (!rst_n)
            reset_seen <= 1'b1;

        // The bidirectional path is always disabled and driven to a known zero.
        assert (uio_out_a == 8'h00);
        assert (uio_oe_a == 8'h00);
        assert (uio_out_b == 8'h00);
        assert (uio_oe_b == 8'h00);

        if (past_valid) begin
            // These three branches are the state-transition table in the spec.
            if (!$past(rst_n)) begin
                assert (uo_out_a == 8'h00);
                assert (uo_out_b == 8'h00);
            end else if ($past(ena)) begin
                assert (uo_out_a == $past(uo_out_a) + 8'h01);
                assert (uo_out_b == $past(uo_out_b) + 8'h01);
            end else begin
                assert (uo_out_a == $past(uo_out_a));
                assert (uo_out_b == $past(uo_out_b));
            end

            // Make the modulo-256 wrap explicit rather than relying on inference.
            if ($past(rst_n) && $past(ena) && ($past(uo_out_a) == 8'hff))
                assert (uo_out_a == 8'h00);

            // The cover task must exhibit a reset-to-FF-to-00 execution trace.
            cover (reset_seen && (uo_out_a == 8'hff));
            cover (reset_seen && $past(rst_n) && $past(ena)
                   && ($past(uo_out_a) == 8'hff) && (uo_out_a == 8'h00));
        end

        // Before reset, power-up state is intentionally unspecified. After one
        // sampled reset, arbitrary and independent ui/uio inputs cannot make the
        // two copies observably diverge.
        if (reset_seen) begin
            assert (uo_out_a == uo_out_b);
            assert (uio_out_a == uio_out_b);
            assert (uio_oe_a == uio_oe_b);
        end
    end
endmodule

`default_nettype wire
