# SPDX-License-Identifier: Apache-2.0
"""RP2350 peer for the FPGA oscillator bench. The transmitter has no clock input."""


@rp2.asm_pio(out_init=rp2.PIO.OUT_HIGH, sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def xtal_peer():
    pull(block).side(0)
    mov(isr, osr).side(0)
    pull(block).side(0)
    set(y, 20).side(0)
    set(x, 31).side(1)  # Hold RUN high. Only the FPGA's own oscillator clocks its UART.
    label('arm')
    jmp(x_dec, 'arm').side(1) [4]
    label('send')
    out(pins, 1).side(1)
    mov(x, isr).side(1)
    label('hold')
    jmp(x_dec, 'hold').side(1)
    jmp(y_dec, 'send').side(1)
    label('idle')
    jmp('idle').side(1)


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def clock_and_data():
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    wrap_target()
    in_(pins, 2) [1]  # GPIO26 = UART, GPIO27 = FPGA's receiver clock.
    wrap()


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def idle_clock_and_data():
    in_(pins, 2) [1]


@rp2.asm_pio()
def watch_enable():
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    wait(0, gpio, 16)
    push(block)


def capture_start(sm, number, dma, buf):
    control = dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4+number)
    dma.config(read=sm, write=buf, count=len(buf)//4, ctrl=control, trigger=True)
    sm.active(1)


def capture_done(dma):
    start = time.ticks_us()
    while dma.active():
        if time.ticks_diff(time.ticks_us(), start) > 30000:
            raise ValueError('clock/data DMA timed out')


def save_capture(name, buf):
    for offset in range(0, len(buf), 1024):
        record(event='samples', case=name, offset=offset, data=binascii.hexlify(buf[offset:offset+1024]).decode())


def calibrate(number):
    assert cold('calibration', False)
    assert Pin(16).value() == 0
    sampler = rp2.StateMachine(number, idle_clock_and_data, freq=-1, in_base=Pin(26))
    buf = bytearray(4096)
    dma = rp2.DMA()
    try:
        capture_start(sampler, number, dma, buf)
        capture_done(dma)
        sampler.active(0)
        assert Pin(16).value() == 0
        first = last = -1
        rising = 0
        previous = (buf[0] >> 1) & 1
        for i in range(len(buf)*4):
            level = (buf[i//4] >> (2*(i%4)+1)) & 1
            if level and not previous:
                if first < 0:
                    first = i
                last = i
                rising += 1
            previous = level
        assert rising > 100
        intervals = rising-1
        ticks = (2*434*(last-first) + intervals//2)//intervals
        save_capture('calibration', buf)
        record(case='calibration', event='clock', cpu_hz=machine.freq(), request_level=Pin(16).value(),
               first_rise=first, last_rise=last, rising=rising, matched_ticks=ticks)
        return ticks
    finally:
        sampler.active(0)
        dma.active(0)
        dma.close()
        park()


def oscillator_pair(name, ticks, first, second, stop1, stop2, free):
    assert cold(name, False)
    tx_id, sample_id, watch_id = free[:3]
    tx = rp2.StateMachine(tx_id, xtal_peer, freq=-1, out_base=Pin(26), sideset_base=Pin(16))
    sampler = rp2.StateMachine(sample_id, clock_and_data, freq=-1, in_base=Pin(26))
    watch = rp2.StateMachine(watch_id, watch_enable, freq=-1)
    buf = bytearray(4*((20*ticks+2048+31)//32))
    dma = rp2.DMA()
    try:
        io.write_uio_outputenable(0)
        tx.put(ticks-4)
        tx.put((first << 1) | (stop1 << 9) | (second << 11) | (stop2 << 19) | (1 << 20))
        capture_start(sampler, sample_id, dma, buf)
        watch.active(1)
        gc.collect()
        terminal, tentative, accepted, polls, gap, dwell = poll_pair(tx)
        capture_done(dma)
        sampler.active(0)
        level = Pin(16).value()
        early_fall = watch.rx_fifo()
        tx.active(0)
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(10)
        final_fall = watch.rx_fifo()
        watch.active(0)
        save_capture(name, buf)
        record(case=name, event='oscillator_uart', cpu_hz=machine.freq(), cell_ticks=ticks,
               request_level=level, early_fall=early_fall, final_fall=final_fall, terminal=terminal,
               tentative=tentative, accepted=accepted, polls=polls, max_poll_gap_us=gap,
               max_read_sequence_us=dwell, service_upper_us=gap+dwell+2)
    finally:
        tx.active(0)
        watch.active(0)
        sampler.active(0)
        dma.active(0)
        dma.close()
        park()


def oscillator_trials(free):
    nominal_ticks = (125*434 + NOMINAL_MHZ//2)//NOMINAL_MHZ
    oscillator_pair('preset', nominal_ticks, 0x55, 0xaa, 1, 1, free)
    matched = calibrate(free[1])
    assert nominal_ticks*8 < matched*10 < nominal_ticks*12
    for name, ticks, a, b, stop1, stop2 in (
            ('matched', matched, 0x55, 0xaa, 1, 1),
            ('distinct', matched, 0x96, 0x69, 1, 1),
            ('fast', (100*matched+51)//102, 0x55, 0xaa, 1, 1),
            ('slow', (100*matched+49)//98, 0x55, 0xaa, 1, 1),
            ('bad-first', matched, 0x55, 0xaa, 0, 1),
            ('bad-second', matched, 0x55, 0xaa, 1, 0)):
        oscillator_pair(name, ticks, a, b, stop1, stop2, free)
