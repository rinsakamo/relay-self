# WB — one-shot real-World ATT-shadow and expired-review DEV protocol (2026-11-02)

**Scope:** A local operator/LocalCodex protocol, not evidence that this World ran. Run only on a uniquely claimed disposable Minecraft World with **current user DEV grant**, exact approved GGUF and llama.cpp server SHA, and an exclusive, unused local model port. No new native observer, Action issuer, S10 commit, Memory write, Habit promotion or forced L2 scheduling. No main merge. Issue owners: #632 / #633, Draft PR #669.

## Known preconditions (do not assume)

- Verify this branch's **exact HEAD and terminal FAST CI**; do not reuse a previous green HEAD as qualification for a newer HEAD.
- Verify existing binary/process mappings, GPU ownership, original server aliases and model launch arguments; expect an attested pinned llama.cpp build10874, context8192 / 1 slot, Gemma4 12B IT Q4_K_M. For the prior qualified condition, GGUF SHA256 was `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed` and server SHA256 was `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`. If actual mappings differ, do not silently substitute.
- Verify Minecraft / Java / Node / Mineflayer prerequisites and fresh owned DEV output root. Do not stop, attach to, or steal another lane's processes or GPU memory.
- Run relevant focused tests, default-OFF regressions, Ruff, contracts and FAST on the **exact execution HEAD**. CI alone is not a real-World or backend qualification.
- DEV grant belongs to local execution; this document and prior user acknowledgements do not themselves consume or verify a grant.

## Single existing S49 real-World entry

The actual supported DEV entry is `python -m adapters.mineflayer.self_demo`. Copy the flags from the exact checked-out help, rather than editing the old S49 executor or adding native probes. A template, not an executed command:

```sh
python -m adapters.mineflayer.self_demo \
  --mode DEV --dev-scenario native-selfworld \
  --run-disposable --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --live-think --self-world-live --wb-cognition-slice --wb-structured-l2 \
  --model-alias "$QUALIFIED_MODEL_ALIAS" \
  --model-port "$OWNED_LOOPBACK_PORT" --model-timeout 12 \
  --output-dir "$NEW_ABSOLUTE_OUTPUT_DIR"
```

The output directory must **not pre-exist**, though its parent must exist. Do not run twice automatically; any subsequent attempt requires an explicit new DEV run lineage, fresh output and authorization. Preserve failure originals including process logs and transient port conflicts.

## Independent evidence readback

Retain `native_report.json`, `live_l2.jsonl`, `dev_receipt.json`, S15/S16 and S49 source pairs, true HTTP raw request/response/envelope, owner and adapter receipts, SHA256 manifest, exact execution HEAD and process/port cleanup proof. The result must join **the S49 original source_pair_trace** and the WB sidecar; its last Paper/S15 sample is not automatically the L2 source callback or a physical source timestamp.

Check separately:

1. S49's original `WAIT → MOVE_AWAY → MOVE_AWAY` outcomes, each Action/S15/S16 and L0 nonblocking. Never make L0 pause to get a model success.
2. Real `reasoning_effort=none` / strict JSON Schema, 0 or 1 allowed model attempt, HTTP completion / S60-B1 / S60-A admitted count, semantic JSON success and earlier source freshness.
3. `dev_wb_structured_l2`: `ACCEPTED_CURRENT_HOST_SOURCE_BOUND`, `ACCEPTED_THEN_WORLD_ADVANCED_HOST_SOURCE_BOUND`, or `NOT_ACCEPTED_OR_UNQUALIFIED`. A backend completion alone is not a current L2 result.
4. `dev_wb_l2_uncertainty_read`: `CURRENT_EPOCH_READ_ONLY`, `PAST_EPOCH_REVIEW_ONLY`, or `UNAVAILABLE`; check exact source seq, current-vs-past disjointness and original native latest source, not the sidecar's latest claim.
5. `dev_wb_l1_attention_shadow`: `ATT_SELECTED_READ_ONLY` **only with actual S60 adoption witness and original native source match**. This is a shadow ATT candidate and may remain as an *admission-time witness* after the L2 result has expired. It is not evidence of an actual L1 policy change.
6. `dev_wb_past_review_handoff`: `PENDING_INDEPENDENT_OUTCOME` only if the old question actually expired and the sidecar later-source reference joins the **last original S49 native callback**. `outcome_verified=false` and `learning_authorized=false` must always hold. This handoff means *review the question later*, not *the question was answered*.
7. Invalid, missing, foreign or forged witness always yields `UNAVAILABLE` and does not alter S49. Treat provider rejection, source displacement and sidecar interpretation failures separately.

**No positive rate or utility claims** from a single World. Distinguish host callback order, independent Minecraft/Paper timing, actual model completion, and current/past readout qualification. The original vanilla Mojang launcher is not an independently validated Paper-clock experiment.

## Cleanup and report

Verify original S49 Action terminal control, Java/Node/model exit, PID disappearance, port rebinding, disposable World deletion, ownership lock removal and retained failed originals. Local cancellation is **not** an attested backend STOP ACK, and GPU-memory reduction is not independent GPU release qualification.

Post the exact HEAD, outcome matrix, relevant test counts, original source seqs, timestamps with clock domains, independent raw evidence location, SHA manifest and terminal CI to existing Draft #669 and Issues #632/#633. Read back the posts, check remote HEAD and worktree cleanliness. Preserve `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` even if the host-source ATT witness is positive.

**No physical World has been run merely by committing this protocol.**
