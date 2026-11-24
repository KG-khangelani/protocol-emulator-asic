# SPDX-License-Identifier: Apache-2.0
"""Clock and bus operations against the public top in the digital fixture."""

from cocotb.triggers import Timer

from tools.host_transport.controller import TransportError


class DigitalPins:
    def __init__(self, dut, *, peer_mask=0, trace=None):
        self.dut = dut
        self.peer_mask = peer_mask
        self.trace = trace
        self.arm_edge = None
        self.handoff = []
        self.launched = False

    def value(self, port):
        return int(getattr(self.dut, port).value)

    def observe(self, ports):
        result = {port: self.value(port) for port in ports}
        if 'uio_out' in result and self.value('loading'):
            result['uio_out'] = self.value('loader_pins')
        return result

    def host_data(self):
        return self.value('host_data')

    def record(self, operation):
        if self.trace is not None:
            fields = ('rising_edges', 'clk', 'rst_n', 'ui_in', 'host_mask', 'peer_drive')
            direction = self.dut.uio_oe.value
            self.trace.append({'operation': operation, **self.observe(fields),
                               'uio_oe': int(direction) if direction.is_resolvable else str(direction)})

    async def take_clock_and_isolate(self):
        dut = self.dut
        dut.clk.value = 0
        dut.ena.value = 1
        dut.rst_n.value = 0
        dut.host_mask.value = 0
        dut.peer_mask.value = self.peer_mask
        dut.peer_connected.value = 0
        dut.ui_in.value = 0xE7
        dut.loading.value = 1
        await Timer(2, unit='ns')
        self.edges = self.value('rising_edges')
        self.arm_edge = None
        self.handoff = []
        self.launched = False
        await self.check_parked()
        if self.value('host_mask') or self.value('peer_connected'):
            raise TransportError('could not isolate host and peer')
        self.record('park-and-isolate')

    async def check_parked(self):
        await Timer(2, unit='ns')
        if self.value('clk') or self.value('rising_edges') != self.edges:
            raise TransportError('unexpected clock edge while parked')
        if self.arm_edge is None and self.value('peer_drive'):
            raise TransportError('external peer is still driving during cold load')
        if self.arm_edge is not None and self.value('peer_drive') != self.peer_mask:
            raise TransportError('peer connection did not settle')
        if self.value('overlap'):
            raise TransportError('shared pin ownership conflict')

    async def release_host(self):
        self.dut.host_mask.value = 0
        await self.check_parked()
        if self.value('host_mask'):
            raise TransportError('host data pins did not release')
        self.record('release-host')

    async def select(self, selector, rst_n):
        self.dut.rst_n.value = rst_n
        self.dut.ui_in.value = selector
        await self.check_parked()
        observed = self.value('ui_in')
        if observed != selector:
            raise TransportError(f'selector {selector:02x} did not settle')
        if self.arm_edge is not None and self.handoff[-1] != observed:
            self.handoff.append(observed)
        self.record('select')

    async def drive_host(self, byte):
        if self.value('uio_oe') or self.value('peer_drive'):
            raise TransportError('write requested while another driver owns the pins')
        self.dut.host_data.value = byte
        self.dut.host_mask.value = 255
        await self.check_parked()
        if self.value('host_mask') != 255:
            raise TransportError('host write direction did not settle')
        self.record('drive-host')

    async def connect_peer(self, idle):
        if self.value('ui_in') != 0xE7 or self.value('host_mask') or self.value('uio_oe'):
            raise TransportError('peer connection requires released pins at E7')
        self.arm_edge = self.edges
        self.handoff = [self.value('ui_in')]
        self.dut.uio_in.value = idle
        self.dut.peer_connected.value = 1
        await self.check_parked()
        self.record('connect-peer')

    async def clock_once(self):
        if self.arm_edge is not None and self.value('ui_in') != 0xE7:
            raise TransportError('clock requested during selector handoff')
        await self.check_parked()
        self.dut.clk.value = 1
        await Timer(10, unit='ns')
        self.dut.clk.value = 0
        self.edges = (self.edges + 1) & 0xffffffff
        await self.check_parked()
        self.record('clock-once')

    async def hand_over_clock(self):
        await self.check_parked()
        if (self.arm_edge is None or ((self.edges - self.arm_edge) & 0xffffffff) != 2
                or self.handoff != [0xE7, 0x67, 0] or self.value('host_mask')
                or not self.value('peer_connected')):
            raise TransportError('incomplete powered handoff')
        self.dut.loading.value = 0
        await self.check_parked()
        self.launched = True
        self.record('hand-over-clock')

    async def abort(self):
        self.launched = False
        self.dut.clk.value = 0
        self.dut.host_mask.value = 0
        self.dut.peer_connected.value = 0
        self.dut.rst_n.value = 0
        self.dut.ui_in.value = 0xE7
        self.dut.loading.value = 1
        await Timer(2, unit='ns')
