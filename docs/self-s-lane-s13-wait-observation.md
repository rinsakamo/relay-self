# RelaySelf S Lane S13 — WAIT is a bounded World observation, not an issued Action

Authority: S product #537, L #426 (especially 6124218906), V #544, R #575.
Immutable parent S12 [Draft #615](https://github.com/rinsakamo/relay-self/pull/615):
`7fd6201befecc43738175335a758d8acd9575cc4`, exact-head CI 4/4 PASS.
Frozen S11 #614 and L5 #613 unchanged.

## Why now

S12 found that S49 `MOVE_AWAY` bound to `MOVE_BACKWARD` is the only
currently issuable normal-session Action. `WAIT` is not issued and must
not be represented as an S16 executed `ActionOutcome` merely to
construct a second treatment or teach an L1/L3 Habit. Independent V
has already observed L5 vs same-info cheap two-feature parity on the
synthetic sixteen-episode fixture.

A *potential* legitimate behavioral comparison is **issued MOVE_AWAY**
with a native S16 terminal vs **nonissued WAIT** with an independently
original pre/post **World observation**. These are different evidence
classes. No existing S9 source claims a WAIT interval, independent
Goal success, or a matched heldout trial.

## One source-specific offline contract

`adapters/mineflayer/self_s13_wait_interval.py` consumes the original
S7 bounded inbound/outbound Mineflayer Python-boundary JSONL **bytes**
and the actual S49 `NormalSessionActionExecutor` owner (with zero issue
count, no dispatch IDs and empty ActionSupervisor). No new HTTP/Node,
Minecraft, Action or World observation is created.

The contract checks:
- Original inbound **whole captured stream** in one Mineflayer
  session, from seq 0 `adapter_started` through `shutdown_ack`, no
  lost/duplicate seq, foreign owner, decoded error, death, respawn,
  forcedMove, effect result, entity hurt or truncated entity registry
- Outbound **whole captured stream**: exactly two correlated
  `{"type":"observe","request_id":"..."}` and shutdown; any effect,
  unexpected command, extra observe, partial line or duplicate request
  fails closed
- The same zombie entity within declared 16m complete native registry
  on both probes; a monotonic bounded World tick delta (default
  1–200), and original health/food/position reported as differences
  **without** assigning a Goal label
- Strongest scoped result: **no Action issued by this single retained
  S49 owner, no effect-command recorded in this single owned bridge's
  complete sent stream, and a bounded source-shaped pre/post World
  observation**. No claim that another client or the Minecraft server
  itself remained inactive

Current original replay/review output is always
`S13_ORIGINAL_SHAPED_NONISSUED_WORLD_INTERVAL_REVIEW_ONLY`.
It is not proof of external original-byte authenticity:
a caller could supply crafted bytes or a newly constructed idle owner.
Only independently archived, immutable, separately witnessed original
runtime receipts and R owner source validation could upgrade the
original provenance. The complete stdout at Python `readline()`
boundary can miss unread data after exit, so absence of events in
decoded bytes is not proof of global absence. `shutdown_ack` confirms
only a bridge ACK if authenticated, not STOP proof for all processes.
World clock ticks can be changed by commands; tick progress alone does
not authenticate elapsed wall time.

## Goal and causal test remain independently blocked

`WAIT` returns **no S16 Action**. This S-owned source reviewer must not
generate `L1_SOURCE_EPISODE_V1`, a Memory success label, an Action
grant, Habit, signed World Goal, or independent physical science GO.
Source types cannot be merged across WAIT and MOVE_AWAY. The V owner
must separately predeclare an independently measurable World Goal,
World-start fingerprint, matched separate sessions, equal-resource
training/heldout, hazard/safety behavior, source-specific cost and
strongest cheap two-feature comparator. R must separately verify
original bytes and any native S16 receipt on issued arm. A controlled
future user-authorized physical run is still NOT approved or ready.

## Engineering validation

S13 synthetic fixtures create valid complete original-format streams
and positive source-shaped review plus fail-closed controls for
partial/reordered/foreign/truncated observations, duplicate requests,
unexpected effects, ActionSupervisor usage, missing owner, time rollback,
missing zombie, missing ACK and stale/altered source. S12/S11/S10
inherited regression and independently pinned V/L5 controls must still
pass. No original WSL2 S9 bytes were read or changed by S13 CI.

Ceiling:
`S13_NONISSUED_WAIT_INTERVAL_OFFLINE_SOURCE_SHAPE_ONLY /
NO_S16_WAIT_OUTCOME / NO_R_ORIGINAL_ADMISSION /
NO_EXPERIMENT_PERMISSION / V_G3_NO_GO / NO_PRODUCTION_GO`.
