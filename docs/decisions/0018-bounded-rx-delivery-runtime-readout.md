# D18 - Bounded last-byte RX delivery with nonintrusive readout

Date: 2026-10-05. Status: RTL/formal and clean-CI qualified implementation,
E0018 at `181cfa1`; PR7 tracks final-record exact-head CI/integration.

Choose an explicit two-frame batch: validate both starts/stops and deliver only
the final byte after normal HALT. The first byte is intentionally discarded;
there is no lossless two-byte delivery, FIFO, per-frame accepted flag or overrun
detector. A failure anywhere rejects the entire batch, even when raw-valid is
one. This is useful bounded acquisition, not a continuous UART receiver. The
evaluation contract's full RX delivery capability remains an open limitation.

The host owns the known image, loader handoff, uninterrupted enable and terminal
status checks. Disable/reset during reception aborts the batch at the host; no
new hardware latch promises to detect that interruption. Reset/reload is
required before a new accepted batch. Human M0 fluency remains pending (D8).

Add only a generic combinational selector from the existing data register mux
to dedicated `uo_out` when `ui_in[7:5]=011`. It adds no retained state and does
not change the engine, store, GPIO ownership, instruction set or loader. Loader
reads drive RX and sampled loader entry resets the engine, so they are not a
safe active-receive service mechanism. A tiny subcycle loader pulse would hide
that electrical/control problem and is explicitly rejected.

Alternatives deferred: a FIFO/second RX slot increases state before its service
contract is measured; a one-frame image avoids overwrite but does not exercise
the existing back-to-back schedule; UART-specific accepted/error flags weaken
the protocol-independent-core hypothesis. Record generic cell cost, not IHP
area. Focused pin traces falsify the policy before full review/CI qualification.

Contracts: `specs/m1-runtime-readback.md`, `specs/p-uart-rx-8n1.md`.
