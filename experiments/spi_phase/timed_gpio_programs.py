# SPDX-License-Identifier: Apache-2.0
"""Independent semantic extension; no RTL generation or instruction expansion."""
from dataclasses import dataclass, fields, replace
from experiments.spi_phase.phase_programs import PhaseMachine, encode as old_encode
from experiments.spi_phase.four_mode_programs import image as old_image
from tools.m1_contract_model import Instruction, State
from tools.spi_four_mode_oracle import timing, raw_at, assess

@dataclass(frozen=True)
class TimedInstruction(Instruction):
    delay: int = 0
    before: bool = False

def base(word):
    return Instruction(**{f.name:getattr(word,f.name) for f in fields(Instruction)})

def encode(word, variant):
    delay=getattr(word,"delay",0)
    before=getattr(word,"before",False)
    if variant not in ("P","F") and (delay or before):
        raise ValueError("extension unavailable")
    if word.opcode=="SET":
        limit=63 if variant=="P" else 31
        if not 0<=delay<=limit or (variant!="F" and before):
            raise ValueError("invalid SET delay")
        return old_encode(base(word)) | (delay<<24) | (int(before)<<29)
    if word.opcode=="DRIVE":
        if before or (variant=="P" and (delay%4 or not 0<=delay<=28)) or (variant!="P" and delay):
            raise ValueError("invalid DRIVE delay")
        return old_encode(base(word)) | (delay//4)
    if delay or before:
        raise ValueError("only SET/DRIVE may be timed")
    return old_encode(base(word))

def image(variant, mode, order):
    if mode not in (1,3):
        return old_image(mode,order,"held")[0]
    if variant=="compact10":
        return old_image(mode,order,"held")[0]
    if variant not in ("P","F"):
        raise ValueError("phase1 does not fit compact8")
    cpol=mode>>1
    return [
        TimedInstruction("SET",mask=12,value=8|(cpol<<2),oe=12),
        TimedInstruction("SET",mask=12,value=cpol<<2,oe=12,delay=23),
        TimedInstruction("LOOP",length=3,count=8),
        TimedInstruction("DRIVE",mask=12,value=(1-cpol)<<2,tx_pin=0,rx_pin=1,msb_first=order,
                         delay=24 if variant=="P" else 0),
        TimedInstruction("SET",mask=4,value=cpol<<2,oe=4,delay=24 if variant=="F" else 0,
                         before=variant=="F"),
        TimedInstruction("SAMPLE",count=23,tx_pin=0,rx_pin=1,msb_first=order),
        TimedInstruction("SET",mask=12,value=8|(cpol<<2),oe=12),
        TimedInstruction("HALT")]

@dataclass
class TimedMachine(PhaseMachine):
    variant: str = "P"
    timed_pending: bool = False
    future_gpio: object = None

    @property
    def capacity(self):
        return 10 if self.variant=="compact10" else 8

    def edge(self, program, *, rst_n=True, ena=True, sampled_inputs=0, tx_payload=0, tx_payload_alt=0):
        if len(program)>self.capacity:
            raise ValueError("image exceeds actual capacity")
        if not rst_n:
            self.timed_pending=False
            self.future_gpio=None
        self.shift_result_write=False
        if rst_n and self.timed_pending:
            if ena:
                if self.wait_left>1:
                    self.wait_left-=1
                else:
                    if self.future_gpio is not None:
                        self.gpio_value,self.gpio_oe=self.future_gpio
                    self.future_gpio=None;self.timed_pending=False
                    self.wait_left=0;self.state=State.RUN;self._advance()
            return
        word = program[self.pc] if rst_n and ena and self.state==State.RUN and self.pc<len(program) else None
        delay=getattr(word,"delay",0)
        before=getattr(word,"before",False)
        if word is not None and (delay or before):
            try: encode(word,self.variant)
            except ValueError:
                self.state=State.FAULT;self.wait_left=0;return
            saved=(self.pc,self.loop_remaining,self.loop_active,self.gpio_value,self.gpio_oe)
            plain=[base(w) for w in program]
            super().edge(plain,rst_n=rst_n,ena=ena,sampled_inputs=sampled_inputs,
                         tx_payload=tx_payload,tx_payload_alt=tx_payload_alt)
            if self.state==State.FAULT or not delay:
                return
            self.pc,self.loop_remaining,self.loop_active=saved[:3]
            if before:
                self.future_gpio=(self.gpio_value,self.gpio_oe)
                self.gpio_value,self.gpio_oe=saved[3:]
            self.state=State.WAIT;self.wait_left=delay
            self.wait_is_input=False;self.shift_period=0
            self.timed_pending=True
            return
        super().edge(program,rst_n=rst_n,ena=ena,sampled_inputs=sampled_inputs,
                     tx_payload=tx_payload,tx_payload_alt=tx_payload_alt)

def execute(program,variant,tx,raw,steps):
    machine=TimedMachine(variant=variant)
    machine.edge(program,rst_n=False,ena=False)
    result,valid=0,0
    trace=[{"edge":0,"out":0,"oe":0,"miso":raw(0),"rx":0,"rx_valid":0,"state":"RUN"}]
    for n in range(1,steps+1):
        machine.edge(program,sampled_inputs=raw(n-2)<<1,tx_payload=tx)
        if machine.shift_result_write:
            result=machine.shift_result_data;valid=1
        trace.append({"edge":n,"out":machine.gpio_value,"oe":machine.gpio_oe,"miso":raw(n),
                      "rx":result,"rx_valid":valid,"state":machine.state.name})
    return trace

def evaluate(variant,mode,order,tx=0x96,rx=0x69,responses=None,profile="held"):
    program=image(variant,mode,order)
    schedule=timing(mode,2 if mode&1 else 3)
    raw={n:raw_at(n,schedule,rx,order,profile,responses) for n in range(-1,schedule["halt"]+1)}
    trace=execute(program,variant,tx,raw.__getitem__,schedule["halt"])
    errors=assess(trace,schedule,tx,rx,order,[s+24 for s in schedule["sample"]])
    return program,trace,errors

MIXED=[1,96,2,95,48,24,72,12]

def public_cases():
    for mode in (1,3):
        for order in (0,1):
            for rx in range(256):
                rotation=rx%8
                yield (f"m{mode}-o{order}-rx{rx:02x}",mode,order,(73*rx+19)&255,rx,
                       MIXED[rotation:]+MIXED[:rotation])
            for name,tx,rx,responses in (("early",0x96,0x69,[1]*8),("late",0,255,[96]*8),
                                        ("mixed",255,0,MIXED)):
                yield f"m{mode}-o{order}-{name}",mode,order,tx,rx,responses
