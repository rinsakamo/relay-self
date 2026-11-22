# I1 + C + I4a dedicated PRE_WORLD runner inventory (HOLD)

Stage: `I1_C_I4A_PRE_WORLD_HOLD`. This is a read-only code-provenance
inventory, **not** an executing real-World or real-Gemma runner. Its one
CLI mode performs a Git exact-HEAD check and hashes sixteen original code files;
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
