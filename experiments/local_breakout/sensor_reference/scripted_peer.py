# SPDX-License-Identifier: Apache-2.0
# The remote runner prepends pico.py. Each master slot is independently sampled by the peer.
from array import array
import gc
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode
from ttboard.util.platform import rp2350 as io


def emit(**values):
    print("I2CLAB " + json.dumps(values))


@rp2.asm_pio(set_init=rp2.PIO.IN_LOW, in_shiftdir=rp2.PIO.SHIFT_LEFT)
def sensor_peer():
    wrap_target()
    label("next")
    pull(block)
    mov(x, osr)
    wait(0, pin, 0)
    jmp(not_x, "listen")
    jmp(x_dec, "active")
    label("active")
    jmp(not_x, "zero")
    wait(1, pin, 0)            # The reset has ended at the peer.
    nop() [22]
    set(pindirs, 1) [31]
    nop() [31]
    nop() [31]
    set(pindirs, 0)
    jmp("next")
    label("zero")
    set(pindirs, 1) [15]
    jmp("sample")
    label("listen")
    nop() [17]
    label("sample")
    mov(isr, null)
    in_(pins, 1)
    push(noblock)
    nop() [12]
    set(pindirs, 0)
    wait(1, pin, 0)
    wrap()


def run_case(name):
    master = Pin(27, Pin.IN, Pin.PULL_UP)
    tap = Pin(19, Pin.IN, Pin.PULL_UP)
    tx = rx = peer = None
    levels = array("I")
    try:
        if name != "empty":
            commands, expected_count = VECTORS[name]
            actions = array("I", list(binascii.a2b_base64(commands)))
            levels = array("I", [2] * expected_count)
            peer = rp2.StateMachine(9, sensor_peer, freq=1000000, in_base=tap, set_base=tap)
            tx, rx = rp2.DMA(), rp2.DMA()
            tx.config(read=actions, write=peer, count=len(actions),
                      ctrl=tx.pack_ctrl(size=2, inc_read=True, inc_write=False, treq_sel=17), trigger=True)
            rx.config(read=peer, write=levels, count=len(levels),
                      ctrl=rx.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=21), trigger=True)
            peer.active(1)
        time.sleep_us(100)
        result = {}
        try:
            result = observe(master, tap, 8, Pin.PULL_UP)
            result.update(fixture="scripted-peer", host=os.uname().machine, system_hz=machine.freq(),
                          master_gpio=27, sensor_gpio=19)
            error = ""
        except (ValueError, RuntimeError, onewire.OneWireError) as exc:
            error = repr(exc)
        # Drop any unused fill words from a deliberately interrupted acquisition.
        captured = bytes(v for v in levels if v != 2)
        emit(event="trace", name=name, result=result, error=error, peer_samples=binascii.hexlify(captured).decode(),
             planned=len(levels), received=len(captured))
    finally:
        if peer is not None:
            peer.active(0)
        for dma in (tx, rx):
            if dma is not None:
                dma.active(0)
                dma.close()
        master.init(Pin.IN, None)
        tap.init(Pin.IN, None)


def bench():
    tt = DemoBoard.get()
    bank = rp2.PIO(2)
    old_base, old_mode, old_hz = bank.gpio_base(), tt.mode, machine.freq()
    if any(rp2.StateMachine(i).active() for i in range(8, 12)):
        raise RuntimeError("PIO2 is in use")
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        tt.reset_project(True)
        Pin(32, Pin.OUT, value=0)  # Keep the E0059 bidirectional FPGA pins disabled.
        Pin(16, Pin.OUT, value=0)
        bank.gpio_base(16)
        machine.freq(125000000)
        emit(event="start", host=os.uname().machine, micropython=os.uname().release, initial_hz=old_hz,
             system_hz=machine.freq(), mode="scripted sensor fixture", peer_clock_hz=1000000)
        for name in CASES:
            gc.collect()
            run_case(name)
    finally:
        for gpio in (19, 27, 32):
            Pin(gpio, Pin.IN, None)
        bank.remove_program(sensor_peer)
        bank.gpio_base(old_base)
        machine.freq(old_hz)
        tt.mode = old_mode
    emit(event="finish", host_uio_oe=io.read_uio_outputenable(), restored_hz=machine.freq(),
         restored_bank=(bank.gpio_base() == old_base))


bench()
