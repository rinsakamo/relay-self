# RelaySelf L18 — capture original S16 owner-terminal event in the S49 process (2026-10-31)

Parent L17 docs HEAD `adf99fb5ac721c55c195e654d4b76932fa645407`. L18 is a narrow S49/S16 owner-produced source upgrade, not a new Action owner or physical SCIENCE grant.

## Producer — existing S16 Action terminal, not fabricated World ACK

Previously L16 captured exact native JSONL `received`/`sent` byte streams and two subsequent Goal position observations, and L17 could re-audit them, but S16's **owner-produced terminal original** had not been retained. L13 therefore lacked a prospective genuine Python S16 Action original and could only consume external fixtures.

L18 adds an opt-in synchronous `on_terminal` callback in the existing `NormalSessionActionExecutor.execute`: after `record_interpreted_action_outcome()` has closed the original S16 `ActionSupervisor`, but **before** the next S49 Action. A failed callback propagates; there is no retry, new Action, changed outcome or alternate transport. Normal S49 with no callback is unchanged.

When L16's explicit physical source capture is enabled, the S49 first Action callback:

1. Uses the actual existing `ActionLifecycle` terminal event, S16 `ActionOutcomeInterpretation` and S15 `WorldConsequence` from the original executor; it **does not re-run or re-interpret S16**.
2. Reads the *already fsync'd original* pre-Action native probe bytes written by the one S7 process source recorder. No reconstruction from typed observation or historical report. Verifies parsing, immutable typed equality, exact Action/session, source revision, S15 dispatch/clear applied ACK, execution status and S16 closure lineage.
3. Exclusively writes/flushes/fsyncs `l18_s16_terminal_original.jsonl` under the existing L16 fresh capture root, using the exact `L13_S16_TERMINAL_SOURCE_V1` field contract. A second creation attempt is rejected (no overwrite/replay).
4. Embeds the source-owner original SHA256/byte count, pre-probe SHA and identity in the S49 report's `l16_capture.l18_s16_owner_source` only after the normal L16 two Goal probes and S7 prefix seal. An incomplete capture remains unable to claim a complete Goal window.
5. Existing L17 saved-file CLI optionally reviews that S16 owner original against the sealed S7 raw received bytes and S49 report, action/session/pre- and post-seq, index SHA, exact schema, and pre-Action probe original SHA. Missing L18 source in a historical L16 report stays `s16_owner_original_present=false` and cannot be retroactively manufactured.

### Source authenticity boundaries

This is an **original newly created by the Python S16 owner at its existing closure boundary**, *not an original Minecraft TCP packet*. The operator-specified `source_revision=0` currently means `0` for an unqualified prior epoch placeholder, **not independently established SelfWorld/SelfBody revision**. Future L13 review must independently verify any actual matching revision and next-epoch witness; do not infer it from this number. No independent external Goal owner or prospective L14 external criterion is minted by this callback. Even a perfect S16 original, two stable native probes and successful S49 run only supply first-party source bytes, not an externally established reached/not-reached goal label.

S7 raw sent stream still cannot prove actual server command delivery, independent absence of environmental intervention or authoritative Minecraft protocol wire bytes. Existing external S/R/V review is needed. No S10/S11 update, autonomous habit grant, L0 promotion or qualified real L10 pair. No real World run performed in L18 here.

## Read-only audit

Existing `adapters.mineflayer.l17_saved_original_goal_readback` CLI remains unchanged in invocation. The CLI now additionally verifies `l18_s16_terminal_original.jsonl` when `l16_capture.l18_s16_owner_source` exists. Legacy L16 capture without this field remains readable and **never upgraded** to a physical S16 event.

```bash
PYTHONPATH=src:tests:. python -m adapters.mineflayer.l17_saved_original_goal_readback
PYTHONPATH=src:tests:. python -m adapters.mineflayer.l17_saved_original_goal_readback \
  --root /absolute/existing/l16-physical-root \
  --s49-report /absolute/existing/s49-report.json
```

Focused synthetic tests cover exact L13 contract, source typed equality, one-write-only, wrong Action/session/pre-probe/source owner, `UNKNOWN` and missing clearance, SHA tampering, symlink/foreign source, and end-to-end L17 readback still waiting for independent external Goal. None of these tests performs a new Minecraft Action.

**Status ceiling:** `DEV_ONLY / L18_S16_OWNER_ORIGINAL_PRODUCER / EXTERNAL_GOAL_0 / PHYSICAL_NEW_WORLD_0 / QUALIFIED_L10_0 / S10_S11_WRITES_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
