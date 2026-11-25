# SPDX-License-Identifier: Apache-2.0
# The host supplies the checked program loader, project_clock and trial settings.
@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def sample_dq():
    in_(pins, 16)


@rp2.asm_pio(set_init=rp2.PIO.IN_LOW, in_shiftdir=rp2.PIO.SHIFT_RIGHT)
def reply_to_command():
    pull(block)
    mov(x, osr)              # Presence delay loop count.
    pull(block)
    mov(y, osr)              # Expected 16 command bits, left aligned.
    wait(0, pin, 0)
    wait(1, pin, 0)
    label("delay")
    jmp(x_dec, "delay")
    set(pindirs, 1) [31]     # Sink for 96 peer clocks.
    nop() [31]
    nop() [31]
    set(pindirs, 0)
    set(x, 15)
    label("write_slot")
    wait(0, pin, 0) [23]
    in_(pins, 1)
    wait(1, pin, 0)
    jmp(x_dec, "write_slot")
    mov(x, isr)
    push(block)              # Actual sampled command, even on rejection.
    jmp(x_not_y, "mismatch")
    pull(block)
    mov(y, osr)
    wait(0, pin, 0)          # Read-slot initiation from the FPGA.
    jmp(y_dec, "match")      # A one leaves the line pulled up.
    set(pindirs, 1) [31]
    set(pindirs, 0)
    label("match")
    set(x, 1)
    jmp("done")
    label("mismatch")
    set(x, 2)
    label("done")
    mov(isr, x)
    push(block)
    label("park")
    jmp("park")


def trial(tt, name, config, plan, capture, clk_id):
    delay, bit, match = config
    load_program(tt, plan, name)
    run_pin = Pin(32, Pin.OUT, value=0)
    Pin(25, Pin.OUT, value=0)
    Pin(28, Pin.OUT, value=0)
    Pin(26, Pin.IN, Pin.PULL_UP)
    target = Pin(27, Pin.IN, Pin.PULL_UP)
    linked = Pin(19, Pin.IN, Pin.PULL_UP)
    timer = rp2.StateMachine(clk_id, project_clock, freq=-1, set_base=Pin(16))
    reader = rp2.StateMachine(8, sample_dq, freq=5000000, in_base=linked)
    peer = rp2.StateMachine(9, reply_to_command, freq=1000000, in_base=linked, set_base=linked)
    dma = rp2.DMA()
    try:
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(20)
        before = [linked.value(), target.value()]
        if before != [1, 1]:
            raise ValueError("DQ did not recover before trial", before)
        peer.put(delay - 1)
        peer.put((0xb4cc if match else 0xb4cd) << 16)
        peer.put(bit)
        peer.active(1)
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
        status = io.read_uo_out_byte()
        observed = [peer.get() for _ in range(peer.rx_fifo())]
        held = [linked.value(), target.value()]
    finally:
        timer.active(0)
        reader.active(0)
        peer.active(0)
        dma.active(0)
        dma.close()
        linked.init(Pin.IN, Pin.PULL_UP)
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(30)
        released = [linked.value(), target.value()]
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
    emit(event="trace", name=name, delay_us=delay, bit=bit, match=match, samples=len(capture) // 2,
         status=status, peer_fifo=observed, before=before, at_halt=held, released=released)


def run_peer():
    tt = DemoBoard.get()
    initial_hz, initial_mode = machine.freq(), tt.mode
    bank = rp2.PIO(2)
    old_base = bank.gpio_base()
    clocks = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if not clocks or any(rp2.StateMachine(i).active() for i in range(8, 12)):
        raise RuntimeError("clock or capture bank in use")
    packed = binascii.a2b_base64(PLAN)
    capture = bytearray(30000)
    bank.gpio_base(16)
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000 and bank.gpio_base() == Pin(16)
        emit(event="start", protocol="onewire-peer", system_hz=machine.freq(), original_hz=initial_hz,
             core_divisor=10, sample_hz=5000000, peer_hz=1000000, gpio_base=16, in_base=19, mask=0x8901)
        for i, config in enumerate(TRIALS):
            gc.collect()
            trial(tt, str(i), config, packed, capture, clocks[0])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        Pin(19, Pin.IN, None)
        tt.reset_project(True)
        for gpio in range(25, 33):
            Pin(gpio, Pin.IN, None)
        for block, program in ((rp2.PIO(0), project_clock), (bank, sample_dq), (bank, reply_to_command)):
            block.remove_program(program)
        bank.gpio_base(old_base)
        machine.freq(initial_hz)
        tt.mode = initial_mode
    emit(event="finish", restored_hz=machine.freq(), restored_bank=(bank.gpio_base() == old_base),
         host_uio_oe=io.read_uio_outputenable())


try:
    run_peer()
finally:
    PLAN = None
    gc.collect()
