# SPDX-License-Identifier: Apache-2.0
# The host prepends the packed loader, requester schedules and original E0057 clock, strobe and loader.
import os


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def branch_sampler():
    wait(1, gpio, 16)
    wrap_target()
    in_(pins, 16)  # GPIO20..31, plus four unused high bits. Two 16-bit samples per DMA word.
    wrap()


@micropython.viper
def pack_samples(buffer, destination, n: int, capacity: int) -> int:
    source = ptr16(buffer)
    out = ptr8(destination)
    used = 0
    last = -1
    for i in range(n):
        raw = int(source[i])
        value = ((raw >> 5) & 127) | ((raw & 1) << 7)
        value ^= (int(source[i % 10]) >> 5) & 64
        if value != last:
            if used + 3 > capacity:
                return -1
            out[used] = i & 255
            out[used+1] = i >> 8
            out[used+2] = value
            used += 3
            last = value
    return used


def physical_input(gpio, direction):
    pull = Pin.PULL_DOWN if direction < 0 else Pin.PULL_UP if direction > 0 else None
    Pin(gpio, Pin.IN, pull)
    pad = machine.mem32[0x40038004 + 4*gpio]
    status = machine.mem32[0x40028000 + 8*gpio]
    function = machine.mem32[0x40028004 + 8*gpio]
    expected = 4 if direction < 0 else 8 if direction > 0 else 0
    if pad & 12 != expected or status & 0x2000 or function & 31 != 5:
        raise ValueError("host pad is not in requested input state", gpio, pad, status, function)
    return [gpio, pad, function, status]


def capture(name, bias, ids):
    packed, count = CASES[name]
    words = binascii.a2b_base64(packed)
    buf = bytearray(2*count)
    changes = bytearray(6500)
    ck, tx, rx = ids
    run = Pin(32, Pin.OUT, value=0)
    clk = rp2.StateMachine(ck, core_clock, freq=-1, set_base=Pin(16))
    driver = rp2.StateMachine(tx, requester, freq=-1, out_base=Pin(25))
    observer = rp2.StateMachine(rx, branch_sampler, freq=-1, in_base=Pin(20))
    Pin(16, Pin.OUT, value=0)
    for gpio, level in ((25, 0), (26, 0), (27, 1)):
        Pin(gpio, Pin.OUT, value=level)
    pads = [physical_input(20, bias[0]), physical_input(28, bias[1])]
    pulse()
    pulse()
    clk.init(core_clock, freq=-1, set_base=Pin(16))
    driver.init(requester, freq=-1, out_base=Pin(25))
    tx_dma, rx_dma = rp2.DMA(), rp2.DMA()
    try:
        tx_dma.config(read=words, write=driver, count=len(words)//4,
                      ctrl=tx_dma.pack_ctrl(size=2, inc_read=True, inc_write=False, treq_sel=tx), trigger=True)
        rx_dma.config(read=observer, write=buf, count=count//2,
                      ctrl=rx_dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4+rx), trigger=True)
        if machine.mem32[0xd0000030] & ((7 << 18) | (1 << 28) | (3 << 30)):
            raise ValueError("host drives a monitored or shared input")
        driver.active(1)
        observer.active(1)
        run.value(1)
        time.sleep_us(40)  # Settle the requested weak bias before starting the FPGA and requester.
        clk.active(1)
        start = time.ticks_us()
        while rx_dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("DMA timeout", name)
        status = io.read_uo_out_byte()
        if tx_dma.active():
            raise ValueError("requester still has pending words")
    finally:
        clk.active(0)
        Pin(16, Pin.OUT, value=0)
        run.value(0)
        observer.active(0)
        driver.active(0)
        for channel in (rx_dma, tx_dma):
            channel.active(0)
            channel.close()
    template = sum(((buf[2*i+1] >> 3) & 1) << i for i in range(10))
    size = pack_samples(buf, changes, count, len(changes))
    if size >= 0:
        report(event="trace", name=name, bias=bias, count=count, template=template, packed=True,
               data=binascii.hexlify(memoryview(changes)[:size]).decode(), status=status, pads=pads)
    else:
        # Keep noisy captures too. Emit bounded lines so the board does not need a second full-sized buffer.
        for k in range(0, len(buf), 512):
            report(event="raw", name=name, bias=bias, offset=k, data=binascii.hexlify(buf[k:k+512]).decode())
        report(event="trace", name=name, bias=bias, count=count, packed=False, status=status, pads=pads)


def run_bias():
    global tt, PLAN
    tt = DemoBoard.get()
    hz, mode = machine.freq(), tt.mode
    free = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if len(free) < 3 or rp2.PIO(0).gpio_base() != Pin(0):
        raise RuntimeError("three free PIO0 state machines on GPIO bank 0 required")
    PLAN = binascii.a2b_base64(DATA)
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        if machine.freq() != 125000000:
            raise ValueError("125 MHz required")
        report(event="start", order=ORDER, host=os.uname().machine, micropython=os.uname().release,
               original_hz=hz, system_hz=machine.freq(), samples_hz=125000000, core_divisor=10)
        load_program(True)
        load_program(False)
        for bias in BIAS:
            for name in NAMES:
                gc.collect()
                capture(name, bias, free[:3])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for gpio in [18, 19, 20] + list(range(25, 33)):
            Pin(gpio, Pin.IN, None)
        for program in (core_clock, requester, branch_sampler):
            rp2.PIO(0).remove_program(program)
        machine.freq(hz)
        tt.mode = mode
    report(event="finish", restored_hz=machine.freq(), host_uio_oe=io.read_uio_outputenable())


try:
    run_bias()
finally:
    CASES.clear()
    PLAN = None
    gc.collect()
