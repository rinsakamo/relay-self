# S49 / Paper directional DASH cap — isolated DEV (2026-10-26)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Design correction: **DASH stance stays active during side/back movement.**
Speed is direction-dependent: forward-only sprint is eligible for the
existing temporary +50% Paper speed modifier; an issued sideways or
backward motion receives a **negative -25% movement-speed attribute
modifier** in place of the forward bonus. This is an *attribute multiplier*
(0.75) and **not** attestation of a hard absolute 4.32 m/s bound or any
measured 0.75× displacement. No new cooldown or fatigue gauge.

## Original S49 Action owner — backward negative control

The unchanged original S49 authorizes/executes an actual BACK control
Action in a disposable Paper 1.21.8 World. The opt-in DEV wrapper attaches
the Paper modifier ONLY to that exact already-issued command, bound by
session, action ID, original sole receiver, backward control and duration.
It passes issued direction 'back' to the DEV Paper plugin before the
Mineflayer control ON. The Paper plugin applies the negative modifier
before movement begins, keeps DASH stance across its callbacks, then
cleans up both forward and negative transient modifiers when the original
control Action terminates. The original S49/Node owner, Action OUTCOME
and cleanup path remain unchanged.

DEV command shape:
relays49dasharm <action-id> <session-id> <player-uuid> <power> <issued-direction>

The Paper console claim is **not a grant**. The plugin cannot verify an
S49 Action by itself. The one-run wrapper checks the underlying original
command, not any arbitrary console ID. Forward and side are not invoked
by the wrapper because there is **no original S49 forward/side issuance
in this branch**. Do not fabricate a forward grant for convenience.

## Validation claims

- Paper plugin source and Java21 build (default OFF outside disposable World).
- Python3.12 focused tests + Ruff before World.
- One disposable Paper 1.21.8 on loopback with pinned JAR SHA and one original
  S49 session. Original S49 backward Action has genuine typed S16 closure,
  while Paper logs the transient modifier presence/ticks.
- No assert that Paper's getCurrentInput reflects all Mineflayer controls,
  or that server-effective control intervals are authenticated.
- Attribute modifier presence is **not** proof of achieved speed or
  direction-specific velocity/position limit.
- P1 physical state/M0 ledger remain unchanged. The offline one-P1 gait
  load-minus-recovery model is not promoted to real fatigue.
- Both transient modifiers are removed on release, plugin disable, player quit.
- Main / Draft PR #634 / protected historical blobs untouched.

Initial DEV workflow 40266400768 showed **5 consecutive Paper callbacks**
with issued_direction=back and cap_modifier_applied=true, forward bonus false;
original S49 reported two real outcome Actions, Node/Java exit 0.
Its Python wrapper nevertheless returned FAIL from a string-matching
bug: modifier_applied=true was matched as a substring of
cap_modifier_applied=true. This is **validation FAIL**, not a physical
failure. The predicate has been updated to require the exact delimited
forward-bonus token. Initial failure remains preserved.

Remaining: independently check verified forward/side issued Actions,
effective physical speeds, directional cap under rapid direction changes,
and per-tick M0/P1 actual ledger settlement.
