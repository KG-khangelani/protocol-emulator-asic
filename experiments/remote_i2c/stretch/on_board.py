# SPDX-License-Identifier: Apache-2.0
# The host supplies the E0059 public loader, project clock and the two checked plans.
import os


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, out_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def stretch_pins():
    mov(osr, pins)        # Capture all inputs simultaneously, starting at GPIO18.
    in_(osr, 2)          # SDA18, SCL19.
    out(null, 11)
    in_(osr, 6)          # GPIO29..34 include SDA enable, HALT and SCL enable.
    nop()                # Five instructions at 31.25 MHz, one sample per 160 ns.


class ReadService:
    def __init__(self):
        self.register = bytearray(1)
        self.reply = b"\x01"
        self.read_events = 0
        self.received = 0
        self.request_at = -1
        self.supplied_at = -1
        self.enqueued = 0

    def interrupt(self, target):
        flags = target.irq().flags()
        if flags & machine.I2CTarget.IRQ_WRITE_REQ:
            self.received += target.readinto(self.register)
        if flags & machine.I2CTarget.IRQ_READ_REQ:
            self.read_events += 1
            if self.request_at == -1:
                self.request_at = time.ticks_us()
            # Leave the TX FIFO empty. The foreground services the first request.

    def service(self, target, delay):
        if delay >= 0 and self.request_at != -1 and self.supplied_at == -1:
            now = time.ticks_us()
            if time.ticks_diff(now, self.request_at) >= delay:
                self.enqueued = target.write(self.reply)
                self.supplied_at = time.ticks_us()


def one_trial(tt, name, clocks, delay, buffer, clock_id):
    load_program(tt, binascii.a2b_base64(PLANS[clocks]), name)
    run = Pin(32, Pin.OUT, value=0)
    page = Pin(25, Pin.OUT, value=0)
    valid = Pin(28, Pin.OUT, value=0)
    for gpio in (18, 19, 26, 27):
        Pin(gpio, Pin.IN, Pin.PULL_UP)
    sda, scl = Pin(18), Pin(19)
    response = ReadService()
    timer = rp2.StateMachine(clock_id, project_clock, freq=-1, set_base=Pin(16))
    reader = rp2.StateMachine(8, stretch_pins, freq=31250000, in_base=sda)
    dma = rp2.DMA()
    target = None
    try:
        target = machine.I2CTarget(1, addr=0x2e, scl=scl, sda=sda)
        target.irq(response.interrupt, trigger=machine.I2CTarget.IRQ_READ_REQ | machine.I2CTarget.IRQ_WRITE_REQ,
                   hard=True)
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(25)
        idle = [sda.value(), scl.value()]
        pads = [[g, machine.mem32[0x40038004 + 4*g], machine.mem32[0x40028004 + 8*g]] for g in (18,19,26,27)]
        if idle != [1, 1]:
            raise ValueError("native receiver idle", idle)
        pulse()
        pulse()
        timer.init(project_clock, freq=-1, set_base=Pin(16))
        dma.config(read=reader, write=buffer, count=len(buffer)//4,
                   ctrl=dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=20), trigger=True)
        run.value(1)
        time.sleep_us(5)
        reader.active(1)
        timer.active(1)
        origin = time.ticks_us()
        while dma.active():
            response.service(target, delay)
            if time.ticks_diff(time.ticks_us(), origin) > 40000:
                raise ValueError("native receiver capture stalled")
        status = io.read_uo_out_byte()
        timer.active(0)
        Pin(16, Pin.OUT, value=0)
        at_halt = [sda.value(), scl.value()]
        page.value(1)
        time.sleep_us(5)
        received = io.read_uo_out_byte()
        valid.value(1)
        time.sleep_us(5)
        received_valid = io.read_uo_out_byte()
    finally:
        timer.active(0)
        reader.active(0)
        dma.active(0)
        dma.close()
        Pin(16, Pin.OUT, value=0)
        run.value(0)
        if target is not None:
            target.deinit()
        for gpio in (18, 19, 26, 27):
            Pin(gpio, Pin.IN, Pin.PULL_UP)
        time.sleep_us(30)
        recovered = [sda.value(), scl.value()]
        for gpio in (18, 19, 25, 26, 27, 28, 29, 30, 31):
            Pin(gpio, Pin.IN, None)
    last, changes = -1, []
    for i, raw in enumerate(buffer):
        value = raw & 0x8f
        if value != last:
            changes.append([i, value])
            last = value
        if len(changes) == 20:
            emit(event="pins", name=name, changes=changes)
            changes = []
    if changes:
        emit(event="pins", name=name, changes=changes)
    actual_delay = None
    if response.supplied_at != -1:
        actual_delay = time.ticks_diff(response.supplied_at, response.request_at)
    emit(event="trace", name=name, guard=clocks, delay_us=delay, service_us=actual_delay,
         read_events=response.read_events, writes_received=response.received, pointer=response.register[0],
         enqueued=response.enqueued, status=status, rx=received, valid=received_valid, samples=len(buffer),
         idle=idle, at_halt=at_halt, recovered=recovered, pad_registers=pads)


def stretch_run():
    tt = DemoBoard.get()
    hz, mode = machine.freq(), tt.mode
    pio = rp2.PIO(2)
    previous_bank = pio.gpio_base()
    if any(rp2.StateMachine(i).active() for i in (8, 9, 10, 11)):
        raise RuntimeError("PIO2 in use")
    clocks = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if not clocks:
        raise RuntimeError("no free clock state machine")
    buf = bytearray(45000)
    pio.gpio_base(16)
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000 and pio.gpio_base() == Pin(16)
        emit(event="start", system_hz=machine.freq(), original_hz=hz, core_divisor=10, sample_hz=6250000,
             sm_hz=31250000, gpio_base=16, in_base=18, mask=0x8f, host=os.uname().machine,
             micropython=os.uname().release, capture="native-i2c1-stretch")
        for clocks_added, delay in TRIALS:
            gc.collect()
            one_trial(tt, "%d-%d" % (clocks_added, delay), clocks_added, delay, buf, clocks[0])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for gpio in range(25,33):
            Pin(gpio, Pin.IN, None)
        for block, program in ((rp2.PIO(0), project_clock), (pio, stretch_pins)):
            block.remove_program(program)
        pio.gpio_base(previous_bank)
        machine.freq(hz)
        tt.mode = mode
    emit(event="finish", restored_hz=machine.freq(), restored_bank=pio.gpio_base()==previous_bank,
         host_uio_oe=io.read_uio_outputenable())


try:
    stretch_run()
finally:
    PLANS.clear()
    gc.collect()
