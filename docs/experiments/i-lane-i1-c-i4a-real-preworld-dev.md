# I1 + C + I4a dedicated PRE_WORLD runner inventory (HOLD)

Stage: `I1_C_I4A_PRE_WORLD_HOLD`. This is a read-only code-provenance
inventory, **not** an executing real-World or real-Gemma runner. Its one
CLI mode performs a Git exact-HEAD check and hashes nineteen original code files;
it returns exit 2 **even when EULA and real-World DEV grant are provided**.
The optional World directory is never touched.

The existing `issue_s2_first_original_place_move_synthetic_dev` remains
strictly synthetic; this new entrypoint does not import or call it. No
new Physical lease, WAL reservation, Owner, model POST, CPU eligibility, or
World authorization is created.

Before any real-World runner becomes executable, it must independently bind
the original Native stdin/stdout and request/seq/provenance/SENSE revision,
same-world Paper boot/session/UUID/ticks and ACKs, real GGUF/PID/GPU/single
slot, original S1 authenticated WAL anchor and S2 new-run boundary, sole
issuer's PREPARED/STOP/settling path, intact peer Self and independently
source-qualified T1 and T2 five-axis assessments. A missing witness must
leave the canonical WAL unresolved if a PREPARED Action exists; it must
never retry or reissue it.

This manifest checks only local code identity; it **does not authenticate**
any of the above live evidence. A future separately implemented real-S2
issuer must satisfy those gates without relaxing the synthetic process
refusal or promoting I1's independent World evidence into I4a evidence.

Offline negative controls: fake/foreign HEAD, EULA+grant without launch,
non-created World directory, and rejection of process-backed sessions in
the synthetic S2 interface. No real World and no real Gemma were run.

Exact-HEAD source admission additionally compares the bytes of each required
working-tree file against its committed Git blob. A normal clean `git diff`
is insufficient: tracked files flagged `assume-unchanged` or `skip-worktree`
can be modified invisibly to that check. Adversarial fixture tests cover both
index flags. This remains a **code-only** integrity check; it never authorizes
World startup or attests a runtime witness.

## Additional PRE_WORLD boundary coverage

The committed-byte inventory now includes original S2 reservation, Owner
run-boundary and S1 anchor, Paper witness and World lifecycle, checkpoint/
Owner, original Native process adapter and llama.cpp HTTP provider. These
are prerequisites for a future **separate** real runner, not witness
authentication or motor authority. Synthetic S2 issuer rejects subclass
native resources in `__slots__`, class attributes, or descriptor inspection
failure **before** a physical lease or canonical WAL mutation. Adversarial
tests exercise rejection with untouched WAL/Supervisor/lease. Python objects
that deliberately forge their own runtime identity remain out of scope;
a real runner must use the separately qualified original Native source.


## S1→S2 original WAL raw-source capture (offline only)

`freeze_original_s1_wal` writes the original canonical S1 WAL bytes once,
under the original Owner cohort lock and original physical/WAL quiescence.
It requires the already established volatile Owner-held S1 anchor. An
independent `audit_s1_prefix_after_s2` reuses the canonical journal parser
and `certified_prefix_digest` to compare those bytes with the complete S2
WAL, accepting exactly one new S2 suffix (including PREPARED_UNRESOLVED,
which **never** authorizes a retry) and rejecting rewritten S1 history,
changed Intent/Skill/session or replayed IDs. The integrated S1→S2→T2
synthetic regression now exercises the sealed-prefix readback after S2.

Both receipts explicitly say **SOURCE CAPTURE / READBACK ONLY**, not
cross-restart authentication. SHA-256 is integrity evidence only when the
capture receipt has independent custody; a mutable manifest cannot authenticate
itself. Genuine native/Paper/Gemma/Target/T1/T2 source witnesses and an
original real S2 issuer/runner remain HOLD. No real World, GPU or Physical
runtime is executed or enabled by this slice.


## Original Native stdout ↔ S1 WAL source review (offline)

`audit_i4a_original_s1_native_stdout` reparses a bounded original Native
JSONL file using the **existing MineflayerStreamDecoder**, which rejects
wrong session, missing adapter_started, missing/duplicated/rewritten sequence
and malformed events. It joins every settled S1 MOVE_PLACE canonical WAL
row to exactly matching initial native request, LOOK/START/STOP children,
optional SNEAK ACK and initial/first-stable/final STOP probes, checking
saved position and **Native** tick; unexpected physical child ACKs are
refused. This is a **source correlation**, not a claim that Native tick and
Paper tick are numerically interchangeable, nor an independently authenticated
Paper action attribution. Synthetic source-shaped tests cover forgeries,
missing frames and wrong session. It makes no physical issue, starts no
World or Gemma and does not authenticate provenance after restart.

## S1 command geometry negative fence (CPU-only)

The original Native stdin auditor now independently recomputes the yaw
convention from each **saved** S1 WAL starting position and saved PLACE target,
and requires the source LOOK yaw to match both this geometry and the WAL
`aim_yaw_rad` at a strict numeric tolerance. The original LOOK pitch must
be zero. The audit rejects invalid extra OBSERVE/SHUTDOWN fields and
non-terminal SHUTDOWN, in addition to missing/reordered/replaced physical
commands. Adversarial tests recompute the stdin SHA after changing yaw,
pitch, command fields and values. This **does not** validate whether the
saved target itself came from independently qualified WorldBody/terrain,
or authenticate Native command custody. No new issuer or World permission.


## Original S2 Native stdout append-only source comparison

The CPU-only `audit_i4a_s2_native_append` rechecks the S1 WAL frozen source,
S1 stdout and the canonical S2 WAL, and demands that the full original S2
stdout be an exact byte extension of original S1 stdout. It verifies the new
S2 LOOK/START/STOP (optional SNEAK) ACKs, initial Native probe and STOP
settling source against the **one** new canonical WAL Action, refusing foreign
session, extra effects, changes to the old Native prefix, changed outcome
probes and PREPARED_UNRESOLVED. The result is deliberately labeled
`SOURCE_CPU_OFFLINE_ONLY`; supplied hashes cannot authenticate their own
custody or the original Paper/Target/World sources. This is not a real runner,
independent Paper auditor, model invocation or Physical authority.

## Separate-process CLI boundary

`experiments/i_lane_i4a_s2_independent_native_audit_dev.py` is a standalone
read-only subprocess entrypoint. It accepts a disk S1 capture manifest, the
canonical S2 WAL and original before/after Native stdout files; returns exit
0 and JSON only for **offline source-content correlation**, exit 2/HOLD for
missing/malformed/forged evidence. Tests spawn a separate Python interpreter
and reject a forged `restart_authenticated=True` receipt. A caller-authored
manifest/hash does not establish original Owner custody, independently sourced
Paper attribution, valid WorldBody Target, real S2 L1, or qualification.

The S2 stdout auditor also independently compares the actual
first-stable and terminal Native positions and refuses more than 0.06m
residual STOP drift, even with a valid checksum and matching WAL ticks.
It rejects reused probe request IDs. Synthetic STOP fixtures preserve a
stationary first-stable/final pair; deliberate drift is a negative control.
