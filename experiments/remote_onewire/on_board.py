# SPDX-License-Identifier: Apache-2.0
# Host-supplied helpers implement the measured cold load, clock and terminal reporting.

@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def bus_samples():
    in_(pins, 16)


@rp2.asm_pio(set_init=rp2.PIO.IN_LOW)
def hold_after_fall():
    wait(0, pin, 0)
    set(pindirs, 1)
    pull(block)


def control(tt, name, mode, packed, capture, clk_id, hold_id):
    load_program(tt, packed, name)
    run_pin = Pin(32, Pin.OUT, value=0)
    Pin(25, Pin.OUT, value=0)
    Pin(28, Pin.OUT, value=0)
    Pin(26, Pin.IN, Pin.PULL_UP)
    dq = Pin(27, Pin.IN, Pin.PULL_UP)
    linked = Pin(19, Pin.IN, Pin.PULL_UP)
    timer = rp2.StateMachine(clk_id, project_clock, freq=-1, set_base=Pin(16))
    reader = rp2.StateMachine(8, bus_samples, freq=5000000, in_base=linked)
    dma = rp2.DMA()
    holder = None
    try:
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(20)
        before = [dq.value(), linked.value()]
        if before != [1, 1]:
            raise ValueError("DQ did not recover before control", before)
        if mode == "stuck-before":
            linked.init(Pin.OPEN_DRAIN, Pin.PULL_UP, value=0)
        elif mode == "stuck-after":
            holder = rp2.StateMachine(hold_id, hold_after_fall, freq=10000000, in_base=linked, set_base=linked)
            holder.active(1)
        time.sleep_us(10)
        at_launch = [dq.value(), linked.value()]
        pulse()
        pulse()
        timer.init(project_clock, freq=-1, set_base=Pin(16))
        dma.config(read=reader, write=capture, count=len(capture) // 4,
                   ctrl=dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=20), trigger=True)
        run_pin.value(1)
        time.sleep_us(5)
        reader.active(1)
        timer.active(1)
        start = time.ticks_us()
        while dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("DQ capture timeout")
        terminal = io.read_uo_out_byte()
        held = [dq.value(), linked.value()]
    finally:
        timer.active(0)
        reader.active(0)
        if holder is not None:
            holder.active(0)
        dma.active(0)
        dma.close()
        Pin(16, Pin.OUT, value=0)
        linked.init(Pin.IN, Pin.PULL_UP)
        time.sleep_us(30)
        released = [dq.value(), linked.value()]
        run_pin.value(0)
        for gpio in (19, 25, 26, 27, 28, 29, 30, 31):
            Pin(gpio, Pin.IN, None)
    changes = []
    last = -1
    for pos in range(0, len(capture), 2):
        val = (capture[pos] | capture[pos + 1] << 8) & 0x8901
        if val != last:
            changes.append([pos // 2, val])
            last = val
            if len(changes) == 20:
                emit(event="pins", name=name, changes=changes)
                changes = []
    if changes:
        emit(event="pins", name=name, changes=changes)
    emit(event="trace", name=name, mode=mode, samples=len(capture) // 2, status=terminal,
         before=before, at_launch=at_launch, held=held, released=released)


def controls():
    tt = DemoBoard.get()
    initial_hz, initial_mode = machine.freq(), tt.mode
    pio = rp2.PIO(2)
    bank = pio.gpio_base()
    if any(rp2.StateMachine(i).active() for i in (8, 9, 10, 11)):
        raise RuntimeError("capture bank in use")
    clocks = [i for i in range(4) if not rp2.StateMachine(i).active()]
    holds = [i for i in range(4, 8) if not rp2.StateMachine(i).active()]
    if not clocks or not holds:
        raise RuntimeError("clock or independent open-drain control unavailable")
    capture = bytearray(30000)  # 15,000 simultaneous samples, nominally 200 ns each.
    packed = binascii.a2b_base64(PLAN)
    pio.gpio_base(16)
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000 and pio.gpio_base() == Pin(16)
        emit(event="start", protocol="1-wire-controls", system_hz=machine.freq(), original_hz=initial_hz,
             clock_divisor=10, sample_hz=5000000, gpio_base=16, in_base=19, mask=0x8901)
        for i, mode in enumerate(("absent", "stuck-before", "stuck-after", "stuck-after", "stuck-before", "absent")):
            gc.collect()
            control(tt, "%d-%s" % (i, mode), mode, packed, capture, clocks[0], holds[0])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        Pin(19, Pin.IN, None)
        tt.reset_project(True)
        for gpio in range(25, 33):
            Pin(gpio, Pin.IN, None)
        for block, program in ((rp2.PIO(0), project_clock), (rp2.PIO(1), hold_after_fall), (pio, bus_samples)):
            block.remove_program(program)
        pio.gpio_base(bank)
        machine.freq(initial_hz)
        tt.mode = initial_mode
    emit(event="finish", restored_hz=machine.freq(), restored_bank=(pio.gpio_base() == bank),
         host_uio_oe=io.read_uio_outputenable())


try:
    controls()
finally:
    PLAN = None
    gc.collect()
