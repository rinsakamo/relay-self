# S58: complete per-Action monotonic timeline on actual native World

Stack authority: exact frozen S57 Draft PR #413 HEAD `564b52cfead748258594be65927072489fee963d`, local physical qualification described in Issue #412 comment 6082863237. S58 Issue #414; branch `self/postmain-feature-s58-all-action-timing-20261009`. Do not rewrite S57's source branch or original independent observations. S57 proved one native Minecraft 1.21.8 + model-computation overlap; second Action's individual start/outcome timestamps had not been captured. **Historical S57 observations are not backfilled.**

## S58 delta

- New `s58_action_timing.py` appends, fsyncs and refuses overwrite of the per-World-session, two-Action immutable JSONL journal.
- For **every** previously independently admitted and bound native L0 Action, record `ACTION_EXECUTOR_INVOCATION` exactly before S16 executor call; after matching native terminal OUTCOME and measured displacement, separately record `ACTION_TERMINAL_OUTCOME_OBSERVED`. Correlate exact session_id, Action id, independent L0 grant ID, World event/probe sequence and entity id. Fail closed on absent/late/unmatched/duplicate result, wrong source, reused grant, or <0.05m movement. Any unresolved Action appends `ACTION_OUTCOME_NOT_OBSERVED`, cannot qualify the required two.
- Each event uses the same **host monotonic clock** and is durably fsync-ed; do not compare arbitrary timestamps across independently clocked hosts. These are Python executor invocation and OUTCOME receipt observation instants, **not** an exact timestamp of Mineflayer issuing the motor command, GPU infer start, or physical movement onset.
- No change to S53 stale L2 guard, S14 admission, S16 terminal closure, S56 real provider, or S57 owned backend behavior. The only new path is opt-in `--action-timing-jsonl` on the S57 driver in this separate stacked branch. Original S57 CLI without the flag keeps the same behavior.
- S56 report can include `s58_action_timing` with count=2, both Action identities, durations and an exact SHA256 of JSONL. S57 top-level result copies that sanitized summary. Neither publishes private paths, prompts or weights. No PASS if one of the two independent Actions lacks a terminal native timestamp.

## LocalCodex / WSL2 execution

Use the same physical hardware and frozen Gemma 4 GGUF as S57 (check current repo authority and exact SHA256 anew); never consume #46 scientific evidence or S31-B resources. Same local `llama-server` binary/GGUF hash and Mineflayer native provider settings, with **a fresh disposable Minecraft session**. Ensure S57 original private evidence remains intact. In this S58 branch run:

```bash
export PYTHONPATH=.:src:tests
export S57_ALLOW_OWNED_BACKEND=1
python -B -m adapters.mineflayer.s57_owned_llama_backend \
  --llama-server "/verified/path/to/llama-server" \
  --binary-sha256 "<actual-full-server-binary-sha256>" \
  --gguf "/verified/path/to/gemma4-12b-q4km.gguf" \
  --expected-sha256 "<actual-full-model-sha256>" \
  --model-alias relay-self-s58-gemma4-12b-q4km \
  --port 12345 --gpu-layers 50 --ctx-size 4352 \
  --timeout-s 100 \
  --action-timing-jsonl s58-private/action-timing.jsonl \
  --report s58-private/s57-owned-world.json \
  --server-log s58-private/native-minecraft.log \
  --backend-log s58-private/owned-llama-server.log
```

Fresh unique output paths required: do not overwrite original JSONL or automatically rerun uncertain physical Action. A failed/incomplete JSONL **must** be retained as negative evidence, then use a different new path for any independently authorized new trial.

## Qualification and negative controls

`PYTHONPATH=.:src:tests python -m pytest -q tests/test_feature_s58_action_timing.py` runs without a real model or Minecraft; those tests only establish journal semantics, NEVER physical Action timing. The next actual physical run requires two distinct native entities/events, two unique Action grants and full real World OUTCOME, both individual invocation and outcome monotonic timestamps and the existing L2 overlap / stale-result / S57 backend identity evidence. The public classification is bounded `EVERY_NATIVE_ACTION_INVOCATION_AND_OUTCOME_TIMED`, until separately verified on actual local host.

**S59 is a distinct experimental question:** interrupting an actively generating llama.cpp backend task, obtaining independent stop ACK and GPU resource release, which S57's normal process shutdown DOES NOT demonstrate. Do not perform that experiment in S58, and do not silently treat host asyncio cancellation as an actual GPU stop. S58 is measurement of physical Action timing only.