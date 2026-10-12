# RelaySelf S Lane S7 — immutable original bridge receipts and S6 index audit

Authority: Self product #537, S6 *consumed* controlled physical
[Issue #537 #6116683016](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6116683016).
Stack only on S6 Draft #604 exact frozen HEAD
`a6ed8ed6b99dd09edcaa6cc9e5cefc08778aec8f`; do not modify #604,
main, R4 #602, V1 #595, L, Golden #583/#588 or host evidence.

## S6 already happened — do not rerun

One original S6 NoAI intervention at S6 exact HEAD physically observed
1 zombie (ID 2) -> S49 native correlated probe -> L0 MOVE_AWAY -> 1 original
terminal executed movement (0.6269m) -> S3 observational Memory 1,
cleanup confirmed, 0 learning/Habit, physical permit **CONSUMED**.

Source evidence files are host-local. The summary here and GitHub comments
are **not** independent readbacks of their bytes. At the time of S6 the
MineflayerProcessSession decoded the child stdout stream without persisting
each original line, so neither discarded outer frames nor original effect
results can be reconstructed from S4 aggregates, S3 Memory, synthetic tests,
Timeline or an Action hash. S7 cannot grant R4/V retroactive qualification.

### SHA discrepancy — use host-local read-only verification

Two claims are *different*:
- User-posted “全証拠索引のSHA256”:
  `baa0e633a10f2cfd64107d1aee77250e56b4fa56405c826ff27e2f3f3652fd47`
- GitHub host operator report “SHA256SUMS 自身”:
  `b22598cc985d5fce4f8c8ffbb15452a8e6f79578aa18d5326650eaa4143536e7`.

Different digests could indicate different index objects/contents or error;
do not assume either tampering or consistency. The host directory is
`/home/rinsa/work/self-s6-evidence-20261012-a6ed8ed`.
`adapters.mineflayer.self_s7_evidence_audit` is an opt-in **read-only**
verifier for canonical SHA256SUMS and every referenced original source file.
It blocks on missing/non-regular/symlink/oversized/traversing/duplicate/
tampered originals, never overwrites, and separately reports whether either
claimed hash matches the actual index and whether the user hash instead
matches another *indexed* original. These are *content* checks, not
provenance/physics attestations. Host execution is required; GitHub CI has
no original WSL2 files.

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_s7_evidence_audit
python -m adapters.mineflayer.self_s7_evidence_audit \
  --root /home/rinsa/work/self-s6-evidence-20261012-a6ed8ed
```

No Minecraft/Java/Node/model World session is used by this audit, and the
single S6 permission **MUST NOT** be replayed.

## Prospective S7 source producer (no current run permission)

New optional `NativeStreamReceipt` writes **exact binary lines** observed
at the existing Python-owned Mineflayer child stdout reader **before UTF-8
decode/JSON validation**, including `adapter_started`, `spawn`, `entities`,
`probe`, `effect_result` and any bad/unknown input bytes actually read.
It separately records exact Python send-attempt lines **before** process
stdin.write()/drain(), including S49 request/action effects. Both are
exclusive-create, fsync'd and size/line bounded under the same fresh
physical operator output root. Bytes are not re-serialized from typed
frames, S3 Memory or server messages. A bad/partial file write blocks
the run rather than silently disabling raw capture.

This records original **bridge JSONL** at the process boundary. It does
**NOT** record raw Minecraft network packets or prove the server executed
an attempted outbound action. Mineflayer bot event emission is also a
transform of network packets, so the phrase "native original" is scoped
to the bridge JSONL source; its scope cannot be expanded retrospectively.

`MineflayerProcessSession.launch(..., native_receipt=None)` preserves
all prior callers. Original S1/S6 `run_physical(..., capture_native_originals=False)`
is unchanged by default; no new reader, child, background collector,
Action issuer or server. For future separately permitted experiments,
`capture_native_originals=True` connects the sole source owner before
the initial `adapter_started` read and all later S49 callbacks:
- `native_bridge_received_original.jsonl`
- `native_bridge_sent_original.jsonl`
- `native_bridge_source_receipt.json` SHA256 and counts (derived index,
  **not** R1 authority envelope)

The separately gated `self_s7_native_trial` CLI is **dry-run only by
default**; it refuses the consumed S6 grant URL, demands distinct S7
confirmation and future fresh user authorization, and keeps the same
bounded controlled NoAI fixture and RSEE preflight. No actual S7 World
may start under this PR or a generic 「進めて」.

### R4/R2/V integration boundary

R4 Draft #602's evidence check requires **an independent R1 envelope**
with proper original receipt/action references under a canonical receipt
root, correct session/head/profile, matched file hashes and Action/OUTCOME
original data. S7 provides the source producer **prerequisite** only.
S7 does not invent the R1 envelope, assert that unrelated JSONL logs are
actual Minecraft TCP frames, or pass R2/V review. Future operator must
supply independent session, original receipt index and R1 authority;
R/V must audit them in their own separate branches. Source ingestion
can remain review-only even if hashes match. No G3 or science GO.

### Offline checks

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_s7_native_trial
python -m adapters.mineflayer.self_s7_evidence_audit
python -m pytest -q tests/test_self_s7_native_originals.py \
  tests/test_mineflayer_process_session.py \
  tests/test_self_s6_controlled.py tests/test_self_s1_runtime.py
python -m pytest -q
```

No installed/new runtime or imported host original required for CI.
Never modify or rerun S6, never recycle its grant. The expected S7
classification until a fresh explicit real-run grant is:
`S7_OFFLINE_ORIGINAL_BRIDGE_SOURCE_CONTRACT_QUALIFIED /`
`S6_ORIGINAL_RAW_NOT_RESTORED / HOST_SHA_AUDIT_NOT_RUN /`
`S7_PHYSICAL_NOT_RUN / NO_PRODUCTION_GO`.
