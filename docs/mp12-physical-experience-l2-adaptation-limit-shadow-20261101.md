# RelaySelf MP12 — Physical-experience-grounded L2 capability shadow

Date: 2026-11-01. Stacked on MP11 G3 Draft #666, parent exact HEAD `fb8db5967bc8960ef860f692c20994974465f353`. Main and existing owners untouched.

## Purpose

The lane's end goal is **experience-derived environmental adaptation AND appropriately calibrated assessment of Self's current limits**. This MP12 slice implements the entry to Stage 2: authentic previous original S49/S16 and Paper S50 body-motion experience is passed as epistemically limited *read-only* data to a replaceable L2 provider. It is **not** yet the G1 real model run, not online experiment control and not a demonstration that knowledge has changed behavior.

## Implemented original-source and model boundary

- `adapters/mineflayer/self_body_mp12_capability_shadow.py` reads **complete postrun physical original files**, not manually transcribed synthetic receipts: `report.json`, `paper-stdout-original.log`, `native-stdout/w3-node-stdout.raw.jsonl` and the matching sealed original W3 receipt. It uses existing independent G3 audit `tools/mp11_g3_paper_one_world_audit.review()`, enforcing same Paper World UUID, actual original S49/S16 sessions, exact original Action/marker correspondence, 3×8 actual Paper WAIT+INPUT tick samples, 3×7 Paper-local frozen-before-next-tick prediction scores. It verifies Node stdout SHA256, exact report receipt, complete EOF/shutdown ACK, single-session scope, source chronology and original score recomputation. A mismatch fails closed.
- Builds one original-source *causal prefix per completed trial*, hashed at the last original Paper-local forecast score of that trial. The L2 request after observed trial N includes **only** the verified motion/errors and source markers for trial 1..N; later historical trial observations are excluded from the model input even though the postrun auditor first verified the complete file.
- Context includes **SelfWorld** floor/Action scope and **SelfBody** actual motion, original WAIT tick samples, calibrated errors for the fixed unlearned slope 0.65 and the cheap zero-next-motion predictor, explicit unknown initial speed/input duration and effective native clear World tick. This is deliberately conservative: observed movement/stop does not establish Self's ability to stop at a future chosen goal.
- L2 chooses one of **four future *hypothetical*** surface/input-duration test labels, a bounded model family and falsifiable predicted WAIT8 displacement, with an ability-limit estimate. Because all observed trials had the same GRASS and MOVE_BACKWARD regime, the only admissible ability classes **at this stage** are `UNKNOWN` and `CONDITIONAL_HYPOTHESIS`. Claims of known impossibility or proven adaptation are rejected. This is not the full final four-way ability-status graduation target.
- The model response has a strict seven-field JSON schema and a sealed SHA256 proposal. Any foreign provider provenance, malformed/stale output, unsafe motor instruction, duplicate added key or mathematically invalid prediction is rejected. This is **read-only shadow output**, never an S10/S11/L10 grant, native executor Action, changed Current Intent or learned L1 policy. **No provider fallback, no invented LLM output**.
- `tools/mp12_l2_source_shadow.py` is an explicit **local-only** actual `LlamaCppRelayProvider` → canonical `RelayEngine.open` CLI with `http://127.0.0.1:<port>/v1/chat/completions` (or localhost/::1) and user-supplied *exact served model alias*. The local model name is operator-supplied and **does not prove the running model weights**. This tool never starts the server. In three-round mode, one verified retrospective source prefix enters each of three real endpoint requests; there is no automated retry or quiet model fallback. It writes bounded outcomes to a new file or a fail-closed record.

## Genuine G3 original source replay preflight: PASS

[GitHub Actions #41294294020](https://github.com/rinsakamo/relay-self/actions/runs/41294294020) **SUCCESS** from MP12 code and actual [G3 one-Paper-World original #41289358266](https://github.com/rinsakamo/relay-self/actions/runs/41289358266) artifact ID `13076239081`, retrieved with read-only GitHub Actions permission, not a synthetic owner fixture. No new World, no real provider/model; source history preflight only. Python3.12 **72 PASS** + Ruff/compileall/repository contracts PASS.

Original same Paper World UUID `93104ce4-97f1-4819-87dc-7044977e816f` / native session `71d219ce-3da9-481c-8936-89647f25c5e1`, originals already sealed in G3. Three successive **source time-cuts**:

| Prefix after trial | Last real Paper source line (index count) | SHA256 of original Paper prefix | WAIT8 total | Fixed 0.65 MAE | Cheap zero MAE |
| --- | ---: | --- | ---: | ---: | ---: |
| 1 (ticks 299–306) | 624 | `b29dccf6bc9ea43830fca57dda6c9db3f8851dc85e7d2a9c9080c373ed0e2cea` | 0.0642466 m | 0.003858 m | 0.002108 m |
| 2 (ticks 499–506) | 1359 | from the saved 3-prefix readback | 0.1228786 m | 0.006805 m | 0.004605 m |
| 3 (ticks 699–706) | 1906 | `18c064a71cbbcc76d0e6f2a389a2527d9e9ae2bd01b7ef40da7e391be027f2d8` | 0.1228786 m | 0.006805 m | 0.004605 m |

The 1-round output was a strict prefix of the complete 3-round output. All per-round data were recalculated from the retained original Paper bytes (not L2's output), and W3 verified the original native session. CI uploaded `mp12-source-only-G3-real-original-prefix-readback-41294294020`, artifact ID `13078692563`, ZIP SHA256 `cb0bf2bc4cc3b51b3b0afa644f35cb848a246e4495f1a3df52587d36e0b29508`; it contains **only** independently recomputed source-summary JSON, not any actual LLM response.

**Critical time-semantics:** This is **retrospective historical replay** after a complete World has shut down. L2 at runtime is not physically present before G3's historical second/third Actions; a later hypothetical choice cannot influence those actions. A hash of postrun paper bytes is source verification, **not** proof the original online L2 saw that state in real time. The physically online condition decision and per-Action Paper prefix freeze remain to be built.

## Run local actual Gemma if an explicitly started compatible llama.cpp server exists

Extract the original `mp11-g3-paper-one-world-three-original-windows-41289358266-1` artifact ZIP to an owned directory, and use the installed repo/venv:

```bash
cd ~/work/relay-self
PYTHONPATH=src:tests:. python tools/mp12_l2_source_shadow.py \
  --g3-originals /absolute/path/to/extracted/g3-originals \
  --output /absolute/path/to/new/mp12-real-l2-result.json \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model YOUR_ACTUAL_LLAMA_SERVER_MODEL_ALIAS \
  --rounds 3
```

The endpoint and served model must actually exist. The script never downloads model weights or starts llama.cpp; real execution has **not** occurred in the current GitHub CI environment. If the LLM emits non-JSON or invalid constraints the script fails closed and preserves previous validated rounds for debugging, without retry. With no server, perform only the verified source preflight:

```bash
PYTHONPATH=src:tests:. python tools/mp12_l2_source_shadow.py \
  --g3-originals /absolute/path/to/extracted/g3-originals \
  --output /absolute/path/to/new/mp12-prefix-only.json \
  --rounds 3 --preflight-only
```

## Next steps, according to the bounded development target

1. **G1 — real local Gemma L2 call:** run above with the exact served local Gemma model, independently preserve provider identity, request/response and call counts; verify L2 changes its proposed experiment/model hypothesis after genuine prior original source. A schema-valid JSON does not prove L2 learned or improved.
2. **G1/G3 → controlled prospective experiment:** bind the actual L2's *sealed BEFORE-ACTION* proposal to a safe original Action-independent operator validation path; physically vary input regime and/or floor in one World (current original Paper plugin floor intervention is one-shot and requires grass, and S49 uses fixed-duration MOVE_BACKWARD). Do not label a condition SHORT/LONG unless actual native control durations differ and are verified.
3. **L1 development:** compare hypothesis against same-information cheap baselines and fresh heldout physical trials. Admit knowledge to L1 only after a positive measured advantage; no L0 auto-promotion.
4. **Adaptation and limits:** validate goal-point stopping/velocity control in multiple environments and recognize controllable, conditionally controllable, currently unsupported and unknown states. Abstention/route change when capability or safety budget is insufficient, rather than a hard-coded slippery-floor rule.

`MP12_G3_ORIGINAL_SOURCE_TO_L2_PREFIX_SEAM_PREFLIGHT_PASS / REAL_LLAMA_CPP_GEMMA_NOT_RUN / RETROSPECTIVE_NOT_ONLINE / PHYSICAL_CONDITIONS_UNCHANGED / L0_OWNER_UNCHANGED / NO_LEARNING_ADMISSION / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

No change to main, historical G3 source, original S49/S16 Action owner or L0 safety.
