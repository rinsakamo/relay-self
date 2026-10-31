# Issue #651: in-World next L0 epoch DEV integration

Base: PR #650 exact `0f52d8d22814874baaa7d435ffc491abe3309d95`.
The isolated host opt-in `--selfbody-live-next-epoch-dev` retains the
original S49 Action owner, thresholds, S15/S16, and Action limit of one.
The default remains OFF; this opt-in and route A's postworld opt-in are
mutually exclusive.

The original two World stimuli remain unchanged. Only after the S16 typed
closure and the actual complete Paper WAIT/INPUT 8×2 window, a third external
World stimulus replaces the zombie with a new one ten blocks away. The
existing native event receiver and original L0 policy must produce
`WAIT → MOVE_AWAY → WAIT`. An extra MOVE request fails before any grant.
No diagnostic observe is added to stand in for an event or decision.

The existing live-probe callback consumes the original next probe through
`LiveNextEpochLease` and takes its readout once. The recorded decision-time
summary is copied for reporting without reading prior experience twice.
Current Body/World Present comes from the new probe only; prior Paper
motion remains `PROVISIONAL_PAPER_ONLY` and is not a policy input.

The original L22/L23 validators require a source prefix ending at the
second Goal probe. The sole S7 recorder therefore seals a byte-exact
snapshot of its already measured prefix into `capture/pre-next-l0-prefix/`
without closing the full original stream. Full S7 recording continues
through the third event/probe, and final cleanup seals the full-session
receipt. Prefix-to-full byte identity is checked separately. No validator
or complete Node TRACE_END requirement is relaxed.

After actual Node/Java shutdown, the original L22/L23/S50 owners review
that prefix plus complete Paper/Node originals. The live Paper prefix is
compared against final Paper bytes. `tools/selfbody_route_b_readback.py`
independently decodes full native originals, correlates three actual
entity events/probes with original L0 policy decisions, re-runs original
source validators, and checks cleanup. Archived JSON does not reconstruct
live typed identity; that identity is asserted in the original host.

DEV_ONLY. Effective clear tick, whole-tick idle and physical stability are
not attested. Goal UNDETERMINED; P1 WAIT/L10/S10/S11 zero;
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. No policy learning is claimed.
