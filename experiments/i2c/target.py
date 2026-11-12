# SPDX-License-Identifier: Apache-2.0
"""Single-byte scripted target driven exclusively by public I2C pin events."""


class Target:
    def __init__(self, case, *, response=4, stretches=None, glitch_release=None):
        self.case = case
        self.response = response
        self.stretches = stretches or {}
        self.releases = 0
        self.segment = -1
        self.active = False
        self.mode = "boundary"
        self.cell = 0
        self.received = 0
        self.reject = False
        self.address_read = False
        self.decoded = []
        self.glitch_release = glitch_release
        self.glitched = False

    def controller(self, tick, before, after):
        if before["oe"] & 1 and not after["oe"] & 1:
            self.releases += 1
            delay = self.stretches.get(self.releases, 0)
            if delay:
                return [(tick+delay, 1, 0)]
        return []

    def bus(self, tick, before, after):
        scl0, scl1 = before & 1, after & 1
        sda0, sda1 = (before >> 1) & 1, (after >> 1) & 1
        if scl0 and scl1 and sda0 != sda1:
            if not sda1:
                self.active = True
                self.segment += 1
                self.mode = "address"
                self.cell = self.received = 0
                self.reject = False
            else:
                self.active = False
                self.mode = "boundary"
        if not self.active:
            return []
        if not scl0 and scl1 and self.mode != "boundary":
            if self.cell < 8 and self.mode in ("address", "write"):
                self.received = (self.received << 1) | sda1
                if self.cell == 7:
                    self.decoded.append({"segment": self.segment, "kind": self.mode, "byte": self.received})
                    if self.mode == "address":
                        self.address_read = bool(self.received & 1)
                        location = "address" if self.segment == 0 else "read_address"
                        self.reject = self.received >> 1 != self.case.address or self.case.nack == location
                    else:
                        self.reject = self.case.nack == "data"
            self.cell += 1
            if self.releases == self.glitch_release and not self.glitched:
                self.glitched = True
                return [(tick+100, 2, 2), (tick+101, 2, 0)]
        if scl0 and not scl1:
            if self.cell == 9:
                if self.mode == "address" and not self.reject:
                    self.mode = "read" if self.address_read else "write"
                else:
                    self.mode = "boundary"
                self.cell = self.received = 0
            low_sda = 0
            if self.mode == "read" and self.cell < 8:
                low_sda = 2*(1-((self.case.rx >> (7-self.cell)) & 1))
            elif self.mode in ("address", "write") and self.cell == 8:
                low_sda = 0 if self.reject else 2
            events = [(tick+self.response, 2, low_sda)]
            if self.stretches.get(self.releases+1, 0) != 0:
                events.append((tick+1, 1, 1))
            return events
        return []
