# RelaySelf L — original S49 live prefix to bounded llama.cpp L2 OPEN (DEV prepared)

2026-11-01. Stacked on L #673 → #671 → #668 → MP11 G3 #666. Owners: #431, #653.

## Development contract

The original S49 single Action issuer can opt in to two L2 OPEN calls after the first and second genuine S16 OUTCOME + Paper WAIT8 windows, using the original running Paper log's completed-line prefix (existing L #673). An asyncio gate prevents the operator-staged next zombie stimulus until each previous response has been checked; the L2 response **does not select the next physical stimulus or Action**. Original L0 decision/admission, native control, Paper owner, and S10/S11/L0 promotion are unchanged.

The canonical existing LlamaCppRelayProvider → RelayEngine.open path is used. A physical S49 request accepts only a localhost / 127.0.0.1 / [::1] HTTP chat-completions endpoint and explicit served model alias. The typed L2 JSON covers referenced prior trial ordinals, model family, reconsideration, falsification test, bounded next-test *idea*, prediction and epistemic ability status (UNKNOWN or CONDITIONAL_HYPOTHESIS). No World command or action owner rights are accepted. Two calls maximum, one attempt each, bounded timeout; abort safely without retry or action if response/timeout fails. Provider label alone is **not weights identity attestation**.

The optional original G2/G3 and live prefix postrun auditors now recognize two actual shadow OPEN calls when explicitly requested and fully source-matched. Their previous zero-model-call default is preserved. No science, training, retained policy or L0 promotion is authorized.

## Offline evidence

Source-only tests use a fake, explicitly labelled RelayEngine provider to check original prior-only input, schema denials, absent/future/malformed references, no Action authority, and non-replay. G2/G3 and S49 source regression included in dedicated GitHub CI. Green CI is **not** a real Gemma inference and is **not** physical validation of the gated execution.

## LocalCodex DEV run recipe (unexecuted here)

In a controlled WSL environment, first confirm a running actual local llama.cpp server with the intended Gemma GGUF and verify model-file identity using local logs/hash; a served alias is not sufficient proof. Reuse exactly source-built RelayMetabolismDev Paper plugin, pinned Paper 1.21.8 build60 SHA-verified JAR, Paper profile and G3 flags from the known-good workflow mp11-g3-three-paper-window-physical-dev.yml. Never upload GGUF or proprietary credentials.

Use a fresh evidence directory, original single Paper server and original S49 owner. Required environment:

    PYTHONPATH=src:tests:.
    NODE_OPTIONS=
    S49_REAL_SERVER_CI=1
    MP11_S49_THREE_ACTION_DEV=1
    MP11_G3_PAPER_THREE_WINDOWS_DEV=1
    L_MP11_LIVE_PREFIX_DEV=1
    L_MP11_LIVE_L2_DEV=1

Run the original Python 3.12 S49 entrypoint with these additional flags and actual local paths:

    python -B -m adapters.mineflayer.s49_normal_session_real_ci \
      --mp11-three-actions-dev --l-mp11-live-prefix-dev \
      --l-mp11-live-l2-endpoint http://127.0.0.1:8080/v1/chat/completions \
      --l-mp11-live-l2-model "$SERVED_GEMMA_ALIAS" \
      --mp11-g3-paper-jar "$PINNED_PAPER_JAR" \
      --mp11-g3-plugin-jar "$PINNED_SOURCE_BUILT_PLUGIN_JAR" \
      --mp11-g3-config "$SOURCE_FROZEN_ACTIVE_MP11_CONFIG" \
      --raw-capture-root "$FRESH_EVIDENCE/native-stdout" \
      --report "$FRESH_EVIDENCE/report.json" \
      --server-log "$FRESH_EVIDENCE/paper-stdout-original.log"

After successful source and cleanup checks:

    python tools/mp11_g3_paper_one_world_audit.py \
      --report "$FRESH_EVIDENCE/report.json" \
      --original-paper "$FRESH_EVIDENCE/paper-stdout-original.log" \
      --expected-live-l2-calls 2 \
      --output "$FRESH_EVIDENCE/independent-g3.json"
    python tools/l_mp11_live_paper_postrun_audit.py \
      --report "$FRESH_EVIDENCE/report.json" \
      --original-paper "$FRESH_EVIDENCE/paper-stdout-original.log" \
      --output "$FRESH_EVIDENCE/independent-l2-prefix.json"

Fail and preserve original positive/negative evidence if the model endpoint, response shape, identity, chronology, physical budget or cleanup is bad. Do not retry a physical World without an authorized DEV decision. Do not claim adaptive intervention: **all three original World stimuli remain human-staged, same grass floor, same MOVE_BACKWARD.**

## Next distinct milestone

Real Gemma OPEN within the running World after prior trial and before next Action, audited from independently sealed W3/Paper and model runtime facts; then separately gate owner-controlled varied physical tests and later heldout model-structure revision. One-shot CHEAP superiority is not required for DEV exploration; scientific gain must still be proved.

Current classification: OFFLINE_DEV_ONLY / REAL_GEMMA_NOT_RUN / L2_CHOSEN_PHYSICAL_EXPERIMENTS_0 / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
