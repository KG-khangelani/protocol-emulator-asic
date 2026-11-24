// SPDX-License-Identifier: Apache-2.0
// A one-transfer SPI target. Only the resolved port supplies its clock and select.
class ClockPeer {
    constructor(mode, order, responseByte, delays) {
        this.cpol = mode >> 1;
        this.cpha = mode & 1;
        this.mostFirst = Boolean(order);
        this.response = responseByte;
        this.delays = delays;
        this.level = 1;
        this.pending = null;
        this.previous = null;
        this.selected = false;
        this.refused = false;
        this.decoded = 0;
        this.launches = [];
        this.samples = [];
        this.asserted = null;
        this.released = null;
    }

    atCoreEdge(edge) {
        if (this.pending && 4 * edge >= this.pending.quarter) {
            this.level = this.pending.level;
            this.pending = null;
        }
        return this.level;
    }

    launch(edge) {
        const bit = this.launches.length;
        if (bit >= 8 || this.pending) throw new Error("target launch collision");
        this.launches.push(edge);
        const shift = this.mostFirst ? 7 - bit : bit;
        this.pending = {quarter: 4 * edge + this.delays[bit], level: (this.response >> shift) & 1};
    }

    sample(edge, data) {
        const bit = this.samples.length;
        if (bit >= 8) throw new Error("more than eight MOSI samples");
        this.samples.push(edge);
        if (this.mostFirst) this.decoded = (this.decoded << 1) | data;
        else this.decoded |= data << bit;
    }

    observe(edge, output, enable) {
        // The fixture supplies a pull-up on CS and pull-downs on SCK and MOSI.
        const pins = (output & enable) | (8 & ~enable);
        const cs = (pins >> 3) & 1;
        const clock = (pins >> 2) & 1;
        if (this.previous !== null) {
            const lastCs = (this.previous >> 3) & 1;
            const lastClock = (this.previous >> 2) & 1;
            if (lastCs && !cs) {
                this.asserted = edge;
                this.refused = lastClock !== this.cpol || clock !== this.cpol;
                this.selected = !this.refused;
                if (this.selected && this.cpha === 0) this.launch(edge);
            } else if (!lastCs && cs) {
                this.released = edge;
                this.selected = false;
            } else if (this.selected && !cs && lastClock !== clock) {
                const leading = clock !== this.cpol;
                if (leading === Boolean(this.cpha)) this.launch(edge);
                else this.sample(edge, pins & 1);
            }
        }
        this.previous = pins;
    }

    result() {
        return {asserted: this.asserted, released: this.released, refused: this.refused,
            launches: this.launches, samples: this.samples, decoded: this.decoded};
    }
}

module.exports = {ClockPeer};
