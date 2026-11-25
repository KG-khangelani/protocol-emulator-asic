# SPDX-License-Identifier: Apache-2.0
# The host supplies the E0059 cold-loader helpers, six trial plans and clock settings.

@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def receiver_pins():
    in_(pins, 16)


def receiver_trial(tt, name, plan, register, reply, address, clock_id, reader_id, capture):
    load_program(tt, plan, name)
    run_pin = Pin(32, Pin.OUT, value=0)
    page = Pin(25, Pin.OUT, value=0)
    valid_page = Pin(28, Pin.OUT, value=0)
    sda = Pin(26, Pin.IN, Pin.PULL_UP)
    scl = Pin(27, Pin.IN, Pin.PULL_UP)
    if EXTRA_PULL:
        Pin(18, Pin.IN, Pin.PULL_UP)
        Pin(19, Pin.IN, Pin.PULL_UP)
    memory = bytearray(256)
    memory[register] = reply
    target = machine.I2CTarget(1, addr=address, mem=memory, mem_addrsize=8, scl=Pin(TARGET_SCL), sda=Pin(TARGET_SDA))
    timer = rp2.StateMachine(clock_id, project_clock, freq=-1, set_base=Pin(16))
    reader = rp2.StateMachine(reader_id, receiver_pins, freq=SAMPLE_HZ, in_base=Pin(19))
    dma = rp2.DMA()
    try:
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(15)
        idle = [sda.value(), scl.value(), Pin(19).value(), Pin(34).value()]
        if idle[:3] != [1, 1, 1]:
            raise ValueError("receiver bus idle", idle)
        # Read the RP2350 pad, function-select and PIO2 input-synchronizer registers.
        # The receiver configuration remains in place throughout the measurement.
        pad_registers = [[gpio, machine.mem32[0x40038004 + 4 * gpio], machine.mem32[0x40028004 + 8 * gpio]]
                         for gpio in (18, 19, 26, 27)]
        pio2_bypass = machine.mem32[0x50400038]
        pulse()
        pulse()
        timer.init(project_clock, freq=-1, set_base=Pin(16))
        # PIO RX DREQ is block*8 + 4 + the state machine index in that block.
        dreq = 8 * (reader_id // 4) + 4 + reader_id % 4
        dma.config(read=reader, write=capture, count=len(capture) // 4,
                   ctrl=dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=dreq), trigger=True)
        run_pin.value(1)
        time.sleep_us(5)
        reader.active(1)
        timer.active(1)
        start = time.ticks_us()
        while dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("wide receiver DMA timeout")
        status = io.read_uo_out_byte()
        timer.active(0)
        Pin(16, Pin.OUT, value=0)
        page.value(1)
        time.sleep_us(5)
        rx = io.read_uo_out_byte()
        valid_page.value(1)
        time.sleep_us(5)
        valid = io.read_uo_out_byte()
    finally:
        timer.active(0)
        reader.active(0)
        dma.active(0)
        dma.close()
        Pin(16, Pin.OUT, value=0)
        run_pin.value(0)
        target.deinit()
        for gpio in (18, 19, 25, 26, 27, 28, 29, 30, 31):
            Pin(gpio, Pin.IN, None)
    # One 16-bit sample covers GPIO19..34. Keep the two SCL inputs, SDA,
    # both controller drive commands and HALT. These six bits share a PIO read.
    previous = -1
    changes = []
    for pos in range(0, len(capture), 2):
        observed = (capture[pos] | capture[pos + 1] << 8) & 0x8d81
        if observed != previous:
            changes.append([pos // 2, observed])
            previous = observed
            if len(changes) == 20:
                emit(event="pins", name=name, changes=changes)
                changes = []
    if changes:
        emit(event="pins", name=name, changes=changes)
    emit(event="trace", name=name, samples=len(capture) // 2, sample_hz=SAMPLE_HZ,
         idle=idle, target_address=address, register=register, reply=reply, status=status, rx=rx, valid=valid,
         pad_registers=pad_registers, pio2_input_sync_bypass=pio2_bypass)


def receiver_run():
    tt = DemoBoard.get()
    initial_hz, initial_mode = machine.freq(), tt.mode
    block = rp2.PIO(2)
    initial_bank = block.gpio_base()
    assert initial_bank in (Pin(0), Pin(16))
    if any(rp2.StateMachine(i).active() for i in (8, 9, 10, 11)):
        raise RuntimeError("capture PIO2 in use")
    clock_ids = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if not clock_ids:
        raise RuntimeError("no idle project-clock state machine")
    capture = bytearray(2 * (SAMPLE_HZ * 24 // 10000))
    block.gpio_base(16)
    try:
        assert block.gpio_base() == Pin(16)
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000
        emit(event="start", system_hz=machine.freq(), original_hz=initial_hz, project_divisor=10,
             sample_hz=SAMPLE_HZ, linked_pulls=EXTRA_PULL, gpio_base=16,
             initial_bank=16 if initial_bank == Pin(16) else 0, in_base=19, pin_mask=0x8d81, machines=[clock_ids[0], 8],
             target_sda=TARGET_SDA, target_scl=TARGET_SCL)
        for cycles, register, reply, address, key in TRIALS:
            gc.collect()
            name = "%d-%02x-%02x" % (cycles, register, address)
            receiver_trial(tt, name, binascii.a2b_base64(PLANS[key]), register, reply, address,
                           clock_ids[0], 8, capture)
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for gpio in range(25, 33):
            Pin(gpio, Pin.IN, None)
        for pio, program in ((rp2.PIO(0), project_clock), (block, receiver_pins)):
            pio.remove_program(program)
        block.gpio_base(initial_bank)
        machine.freq(initial_hz)
        tt.mode = initial_mode
    assert block.gpio_base() == initial_bank
    emit(event="finish", restored_hz=machine.freq(), restored_bank=16 if initial_bank == Pin(16) else 0,
         host_uio_oe=io.read_uio_outputenable())


try:
    receiver_run()
finally:
    PLANS.clear()
    gc.collect()
