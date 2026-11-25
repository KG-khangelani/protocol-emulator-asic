# SPDX-License-Identifier: Apache-2.0
# Independent uncompressed acquisition. GPIO20/28 are captured as separate bits of each DMA halfword.


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def park_clock():
    pull(block)
    mov(x, osr)
    label("lead")
    set(pins, 1) [4]
    set(pins, 0) [3]
    jmp(x_dec, "lead")
    pull(block)
    mov(x, osr)
    label("park")
    jmp(x_dec, "park")
    wrap_target()
    set(pins, 1) [4]
    set(pins, 0) [4]
    wrap()


def control_capture(name, parked, repeat, ids):
    ck, tx, rx = ids
    program = park_clock if parked else core_clock
    command = binascii.a2b_base64(CASES[name][0])
    capture = bytearray(2*6400)
    run = Pin(32, Pin.OUT, value=0)
    Pin(16, Pin.OUT, value=0)
    for gpio, level in ((25, 0), (26, 0), (27, 1)):
        Pin(gpio, Pin.OUT, value=level)
    pads = [physical_input(20, 0), physical_input(28, -1)]
    pulse()
    pulse()
    clk = rp2.StateMachine(ck, program, freq=-1, set_base=Pin(16))
    tx_sm = rp2.StateMachine(tx, requester, freq=-1, out_base=Pin(25))
    rx_sm = rp2.StateMachine(rx, branch_sampler, freq=-1, in_base=Pin(20))
    if parked:
        clk.put(349)
        clk.put(999)
    tx_dma, rx_dma = rp2.DMA(), rp2.DMA()
    try:
        tx_dma.config(read=command, write=tx_sm, count=len(command)//4,
                      ctrl=tx_dma.pack_ctrl(size=2, inc_read=True, inc_write=False, treq_sel=tx), trigger=True)
        rx_dma.config(read=rx_sm, write=capture, count=len(capture)//4,
                      ctrl=rx_dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4+rx), trigger=True)
        if machine.mem32[0xd0000030] & ((7 << 18) | (1 << 28) | (3 << 30)):
            raise ValueError("host drives a monitored or shared input")
        tx_sm.active(1)
        rx_sm.active(1)
        run.value(1)
        time.sleep_us(40)
        clk.active(1)
        start = time.ticks_us()
        while rx_dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("raw capture stalled", name)
        status = io.read_uo_out_byte()
        if tx_dma.active():
            raise ValueError("held requester schedule incomplete")
    finally:
        clk.active(0)
        Pin(16, Pin.OUT, value=0)
        run.value(0)
        tx_sm.active(0)
        rx_sm.active(0)
        for dma in (rx_dma, tx_dma):
            dma.active(0)
            dma.close()
    for offset in range(0, len(capture), 512):
        report(event="raw", name=name, bias=[0,-1], offset=offset, data=binascii.hexlify(capture[offset:offset+512]).decode())
    report(event="trace", name=name, bias=[0,-1], packed=False, count=len(capture)//2, status=status,
           parked=parked, repeat=repeat, pads=pads)


def run_controls():
    global tt, PLAN
    tt = DemoBoard.get()
    hz, mode = machine.freq(), tt.mode
    free = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if len(free) < 3 or rp2.PIO(0).gpio_base() != Pin(0):
        raise RuntimeError("three free PIO0 machines on bank 0 required")
    PLAN = binascii.a2b_base64(DATA)
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        if machine.freq() != 125000000:
            raise ValueError("125 MHz required")
        report(event="start", order=ORDER, original_hz=hz, system_hz=machine.freq(), samples_hz=125000000,
               core_divisor=10, host=os.uname().machine, micropython=os.uname().release)
        load_program(True)
        load_program(False)
        pairs = [("a4-held", False), ("a5-held", True), ("a4-held", True), ("a5-held", False)]
        for repeat in range(2):
            for name, parked in pairs:
                gc.collect()
                control_capture(name, parked, repeat, free[:3])
            pairs.reverse()
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for gpio in [18, 19, 20] + list(range(25, 33)):
            Pin(gpio, Pin.IN, None)
        for program in (core_clock, park_clock, requester, branch_sampler):
            rp2.PIO(0).remove_program(program)
        machine.freq(hz)
        tt.mode = mode
    report(event="finish", restored_hz=machine.freq(), host_uio_oe=io.read_uio_outputenable())


try:
    run_controls()
finally:
    CASES.clear()
    PLAN = None
    gc.collect()
