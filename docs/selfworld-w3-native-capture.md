# RelaySelf SelfWorld W3 — Native source capture boundary (DEV ONLY)

Authority: SelfWorld #633, S integration #537, Adaptive Cognition #426,
physical control #627, existing Draft PR #634. Main unchanged.

## Evidence scope (strict)

The **original** `MineflayerProcessSession.receive()` reads the bytes from
one Node bridge `stdout.readline()`. The W3 opt-in observer writes the
**exact bytes** before UTF-8 or JSON decoding, before the S49 native
`NativeObservationOnly` event filter and before Action outcome aggregation.

It does **not** store the raw Minecraft Java server-to-Node TCP packet stream
or instrument `mineflayer` network protocol. It cannot attest events the
Node bridge did not emit. This is **`NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP`**,
not independent World truth or source validity.

The observer never sends a command, selects an action, creates S10 learning
authority, or introduces another Mineflayer instance. Existing S49 Action
owner and no-capture route remain unchanged.

## New W3 files

- `w3-node-stdout.raw.jsonl`: exact pre-decode Node stdout bytes,
  including `adapter_started`, `entity_hurt`, effects, observations,
  `shutdown_ack` and all other received Node JSONL frames. The writer is
  created exclusively in the new DEV evidence root with file mode 0600,
  flush/fsync after each received line, bounded total 32 MiB by default.
  Partial lines, frame-size/total-size overflow and write failures fail closed.
- `w3-node-stdout-receipt.json`: exclusively created sealed receipt,
  SHA256 of exact raw file, total bytes, frames, session, first/last seq,
  tracked shutdown ACK count, EOF, child exit, fault and qualification.
  Complete only if `seq 0..n` decoded continuously, one same session, exact
  `adapter_started`, one shutdown ACK, actual Node EOF, clean shutdown
  and exit 0. Interrupted/sham/truncated evidence is
  `INCOMPLETE_UNQUALIFIED`; **no later upgrade of an existing receipt**.

Offline read-only audit:
```python -c 'from pathlib import Path; from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout; print(audit_w3_sealed_stdout(Path("/ABS/NEW/DEV_ROOT")))' ```

`audit_w3_sealed_stdout` replays the stored bytes through the existing
`MineflayerStreamDecoder` (not an independently provisioned witness),
independently recomputes SHA256 and sequence/session/ACK/length. A
self-generated SHA256+receipt does not create independent notarization.
Raw stdout may be lost after adapter shutdown if underlying process does
not flush: this yields incomplete/blocked evidence rather than success.

## Separate bounded DEV acquisition — NOT automatic

After exact-head FAST tests pass and with existing disposable-world DEV
permission only, a LocalCodex operator can opt into the sole original S49
source owner with a **new** absolute evidence root:

```bash
PYTHONPATH=src:tests:. python -B -m adapters.mineflayer.self_demo \
  --mode DEV --dev-scenario native --run-disposable \
  --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --self-world-w3-raw-capture \
  --output-dir /ABS/NEW/UNUSED_W3_DEV_ROOT
```

This command provisions a fresh disposable Minecraft server and Node bridge;
it **does issue real original S49 physical Action** in an expressly new
DEV-only run. It is **not** an instruction to reuse historical grants, change
S49 owner or attach to the existing R/V Science environment.

The existing `self_demo` DEV receipt SHA manifest will additionally index
both W3 files. Report and inspect all prior S49 native decoded Action/World
outcomes, capture receipt, SHA hashes, STOP/Node/Java exit and cleanup.
Preserve failures as their own new run; never silently rerun to rewrite
one-shot frozen evidence.

## Negative tests and qualification ladder

FAST test `tests/test_self_world_stage_w3_capture.py`: exact startup,
unfiltered observation, shutdown/EOF, default no-capture behavior,
gap, session swap, invalid UTF-8, malformed/partial/oversized frame,
no/duplicate ACK, file tampering/truncation, wrong SHA, forged
`s10_commit_permitted` flag, wrong session and exclusive-create denial.
Also rerun `tests/test_mineflayer_process_session.py`.

1. `W3_RAW_NODE_STDOUT_OFFLINE_CONTRACT_PASS`: CI-only synthetic capture
   and read-only replay; does not assert physical World.
2. `W3_ORIGINAL_S49_NODE_STDOUT_DEV_SOURCE_CAPTURED`: new disposable
   original owner run with complete archived Node stdout bytes,
   validated original startup/ACK/EOF. This is DEV source, not SCIENCE.
3. `W3_INDEPENDENT_SOURCE_ATTESTED`: **not** awarded by the code alone.
   Requires separately trusted archivist, independently pinned digest,
   Node emitter completeness/connection provenance and reconciliation
   with S16/Stage S and the W1 signed archive. A locally minted pin is
   insufficient.
4. Real non-HOLD S10 learning, near-threat WAIT physical safety,
   survival gain, SCIENCE causal ON/OFF/sham: all remain **NO_GO**.

Existing Stage R ZIP from W2 is historical and remains
`RAW_NATIVE_SOURCE_NOT_ATTESTED`; W3 does not retroactively repair it.

## One-shot disposable DEV pre-registration (GitHub Actions)

Exactly one branch push with commit marker
`[selfworld-stage-w3-capture-dev-once]` can invoke the gated
`selfworld-stage-w3-capture-dev-once` job, **only** after all four FAST
jobs succeed on that exact source HEAD, and only on first workflow
attempt. It uses a fresh `/tmp/selfworld-stage-w3-<run>-1` and original
model-free S49 DEV Action owner. Archive `native_report.json`, existing
DEV receipt and original bytes/receipt even if the job fails. Stop without
automatic retry after any incomplete evidence; new independent trial
must not reuse any prior grant, run ID, evidence root or historical World.
Physical capture remains DEV, and raw Node stdout does not establish
original Minecraft wire-packet identity or a trusted external archivist.
