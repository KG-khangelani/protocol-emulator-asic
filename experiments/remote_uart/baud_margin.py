# SPDX-License-Identifier: Apache-2.0
"""Physical baud-offset trials. The host appends this to the board GPIO helpers."""


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def project_clock():
    set(pins, 1)
    set(pins, 0)


@rp2.asm_pio(out_init=rp2.PIO.OUT_HIGH, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def serial_peer():
    pull(block)
    mov(isr, osr)  # Save the bit-cell loop count.
    pull(block)
    mov(x, osr)    # Programmable launch delay.
    pull(block)    # Two packed frames followed by an idle mark.
    set(y, 20)
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    label('arm')
    jmp(x_dec, 'arm')
    label('send')
    out(pins, 1)
    mov(x, isr)
    label('hold')
    jmp(x_dec, 'hold')
    jmp(y_dec, 'send')
    label('idle')
    jmp('idle')


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def pad_sampler():
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    wrap_target()
    in_(pins, 1) [1]  # GPIO26 input buffer, one sample per two system ticks.
    wrap()


def measure_pair(name, ticks, delay, first, second, stop1, stop2, free):
    clock_id, tx_id, sample_id = free[:3]
    clk = rp2.StateMachine(clock_id, project_clock, freq=25000000, set_base=Pin(16))
    tx = rp2.StateMachine(tx_id, serial_peer, freq=-1, out_base=Pin(26))
    sampler = rp2.StateMachine(sample_id, pad_sampler, freq=-1, in_base=Pin(26))
    capture = bytearray(1440 * 4)
    dma = rp2.DMA()
    try:
        io.write_uio_outputenable(0)
        bits = (first << 1) | (stop1 << 9) | (second << 11) | (stop2 << 19) | (1 << 20)
        tx.put(ticks - 4)
        tx.put(158 + delay)
        tx.put(bits)
        # PIO0 RX DREQs are 4..7. The sampler's RX FIFO is the fixed source.
        control = dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4 + sample_id)
        dma.config(read=sampler, write=capture, count=len(capture) // 4, ctrl=control, trigger=True)
        sampler.active(1)
        tx.active(1)
        gc.collect()
        terminal, tentative, accepted, polls, gap, duration = poll_pair(clk)
        start = time.ticks_us()
        while dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 20000:
                raise ValueError('digital capture timed out')
        sampler.active(0)
        sampler.init(count_clock, freq=-1)
        elapsed = measure_clock(sampler, 12500000)
        record(event='margin', case=name, cell_ticks=ticks, delay_ticks=delay, cpu_hz=machine.freq(),
               terminal=terminal, tentative=tentative, accepted=accepted, polls=polls,
               max_poll_gap_us=gap, max_read_sequence_us=duration, service_upper_us=gap+duration+2,
               pad_clock_periods=100000, pad_count_elapsed_us=elapsed,
               samples_hex=binascii.hexlify(capture).decode())
    finally:
        clk.active(0)
        tx.active(0)
        sampler.active(0)
        dma.active(0)
        dma.close()
        park()


def margin_trials(free):
    for rate, ticks in (('fast', 4254), ('nominal', 4340), ('slow', 4429)):
        for delay in (0, 4, 8):
            name = '%s-%d' % (rate, delay)
            assert cold(name, False)
            measure_pair(name, ticks, delay, 0x55, 0xaa, 1, 1, free)
    for name, ticks, a, b, stop1, stop2 in (
            ('fast-distinct', 4254, 0xa5, 0x3c, 1, 1),
            ('fast-bad-first', 4254, 0x55, 0xaa, 0, 1),
            ('slow-bad-second', 4429, 0x55, 0xaa, 1, 0)):
        assert cold(name, False)
        measure_pair(name, ticks, 4, a, b, stop1, stop2, free)
