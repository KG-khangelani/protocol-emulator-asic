# SPDX-License-Identifier: Apache-2.0
"""RP2350 peer for the FPGA oscillator bench. The transmitter has no clock input."""


def peer_clock_tree():
    read = machine.mem32
    return [read[0x4001003c], read[0x40010040], read[0x40010044], read[0x40048004],
            read[0x40050000], read[0x40050008], read[0x4005000c]]


def runtime_selector(value):
    return (value & ~0x12) | ((value & 2) << 3)


def runtime_page(value):
    return page(runtime_selector(value))


def selector_one_driven():
    return (machine.mem32[0xd0000030] >> 18) & 1


def isolated_cold(name, damaged):
    tt.clock_project_stop()
    park()
    tt.mode = RPMode.ASIC_RP_CONTROL
    park()
    stage = Pin(32, Pin.OUT, value=0)
    readback = bytearray()
    registers = []
    previous_reset = -1
    for edge, (selector, rst_n, write_data, expected_status, expected_bus) in enumerate(STEPS, 1):
        if write_data >= 0:
            assert selector & 0xc0 == 0xc0
            stage.value(1)
            select(write_data ^ int(damaged and selector == 0xc1))
            stage.value(0)  # Keep the original byte in the staging register.
        select(selector if selector & 0x80 else runtime_selector(selector))
        if rst_n != previous_reset:
            tt.reset_project(not rst_n)
            previous_reset = rst_n
        time.sleep_us(3)
        io.write_clock(1)
        time.sleep_us(3)
        io.write_clock(0)
        time.sleep_us(3)
        if expected_status >= 0 and io.read_uo_out_byte() != expected_status:
            raise ValueError('staged loader status', edge, expected_status, io.read_uo_out_byte())
        if expected_bus >= 0:
            observed = io.read_uo_out_byte()
            if observed != expected_bus:
                record(case=name, event='readback_failure', edge=edge, selector=selector,
                       expected=expected_bus, observed=observed, path='dedicated_uo')
                if damaged and edge == 38 and expected_bus == 0 and observed == 1:
                    return False
                raise ValueError('staged readback', edge, expected_bus, observed)
            if selector < 0xa0:
                readback.append(observed)
            else:
                registers.append([selector, observed])
    assert not damaged and len(readback) == 32 and io.read_uio_outputenable() == 0x80
    Pin(18, Pin.IN, None)  # UI1 and the UART pin share a Raspberry Pi HAT connection.
    assert selector_one_driven() == 0
    io.write_uio_byte(2)
    io.write_uio_outputenable(0x82)
    identity = runtime_page(0x67)
    status = runtime_page(0)
    record(case=name, event='isolated_cold', edges=len(STEPS), image=binascii.hexlify(readback).decode(),
           registers=registers, identity=identity, status=status, selector1_oe=selector_one_driven(),
           host_uio_oe=io.read_uio_outputenable(), path='dedicated_uo')
    if identity != 0x22 or status != 0x20:
        record(case=name, event='handoff_failure', status_samples=[runtime_page(0) for _ in range(4)],
               pc=runtime_page(0x66), request=Pin(16).value(), stage=Pin(32).value(),
               physical_ui=io.read_ui_in_byte())
    assert identity == 0x22 and status == 0x20
    return True


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
    in_(pins, 4) [1]  # GPIO26 = UART, GPIO29 = FPGA clock. Two samples per byte.
    wrap()


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def idle_clock_and_data():
    in_(pins, 4) [1]


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
    assert isolated_cold('calibration', False)
    assert Pin(16).value() == 0
    sampler = rp2.StateMachine(number, idle_clock_and_data, freq=-1, in_base=Pin(26))
    buf = bytearray(8192)
    dma = rp2.DMA()
    try:
        capture_start(sampler, number, dma, buf)
        capture_done(dma)
        sampler.active(0)
        assert Pin(16).value() == 0
        first = last = -1
        rising = 0
        previous = (buf[0] >> 3) & 1
        for i in range(len(buf)*2):
            level = (buf[i//2] >> (4*(i%2)+3)) & 1
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
               first_rise=first, last_rise=last, rising=rising, matched_ticks=ticks, clock_tree=peer_clock_tree())
        return ticks
    finally:
        sampler.active(0)
        dma.active(0)
        dma.close()
        park()


def oscillator_pair(name, ticks, first, second, stop1, stop2, free):
    assert isolated_cold(name, False)
    tx_id, sample_id, watch_id = free[:3]
    tx = rp2.StateMachine(tx_id, xtal_peer, freq=-1, out_base=Pin(26), sideset_base=Pin(16))
    sampler = rp2.StateMachine(sample_id, clock_and_data, freq=-1, in_base=Pin(26))
    watch = rp2.StateMachine(watch_id, watch_enable, freq=-1)
    buf = bytearray(4*((20*ticks+2048+15)//16))
    dma = rp2.DMA()
    try:
        io.write_uio_outputenable(0x80)
        before = peer_clock_tree()
        tx.put(ticks-4)
        tx.put((first << 1) | (stop1 << 9) | (second << 11) | (stop2 << 19) | (1 << 20))
        capture_start(sampler, sample_id, dma, buf)
        watch.active(1)
        gc.collect()
        terminal, tentative, accepted, polls, gap, dwell = poll_pair(tx, runtime_page)
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
               max_read_sequence_us=dwell, service_upper_us=gap+dwell+2, clock_tree_before=before,
               clock_tree_after=peer_clock_tree(), selector1_oe=selector_one_driven())
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
