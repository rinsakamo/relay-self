# RelaySelf MP11 G3 — One real Paper World, three native S49/S16 Actions and three Paper S50 windows

Date 2026-11-01. Stacked on MP11 G2 Draft #665; exact G2 parent HEAD `9737c25ff564a67a72ce15922f592755dc634715`. Issues #653 / #537.

## What was changed

1. The original S49 DEV-only G2 extension now accepts **explicit**, source-verified Paper 1.21.8/plugin/config assets under `MP11_G3_PAPER_THREE_WINDOWS_DEV=1`. It reuses one existing original `NormalWorldL0`, one `NormalSessionActionExecutor` and its S14/S15/S16 owners; no extra Action source. It retains the physical G2 one-World Action budget of three and the per-Action typed readonly SelfBody S16 leases.
2. The Paper plugin adds a default-disabled `s50-mp11-multitrial-dev` config flag and a **console-only** `relaydevmp11next previous_marker next_marker` phase transition. Only an original complete 8-tick WAIT, exactly 8 original Paper-local samples, finished S15/POST_CLEAR phase, a unique next marker, and a global maximum of three trials permit resetting the per-trial *observation ledger*. Previous original World/source bytes remain immutable and separate. This command neither moves the player nor grants a new S49 Action. Historical non-MP11 Paper code behavior remains default-OFF.
3. Before each original S49 Action, the host freezes an intentionally simple **unlearned fixed slope 0.65** Paper-local predictor, tags it by that Action and original native session, and commands Paper to verify the existing grass 5x5 without changing floor blocks. After original S16 OUTCOME and clear, Paper samples eight actual World ticks and scores seven genuine pre-next-callback predictions. Only after a complete previous window can the next Action's phase begin.
4. An independent source-audit compares all three original Paper markers, the same **physical Paper World UUID and subject UUID**, original floor-source locks, per-trial PRE/POST, 24 WAIT and input rows, 21 pre-next-tick fixed / later scored records, and native Action IDs with three original S16 outcome/clear receipts. Both the server's complete stdout and original W3 Node stdout are retained.
5. An original frozen config is copied into the DEV artifact, with explicit M0.2 interventions enabled and Paper-local observation flags; **not** a passive real-world measurement. No G1 real Gemma/L2 provider, L1 learning admission, independent counterfactual goal or same-information cognitive advantage is asserted.

## Actual one-time physical DEV experiment

[GitHub Actions #41289358266](https://github.com/rinsakamo/relay-self/actions/runs/41289358266), executing HEAD `38e19c367eb6ef16e1f2cdef9a0b544128c6a762`, **SUCCESS**. Single new Paper 1.21.8 build 60 server (pinned SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`), one Mineflayer4.39.0 original session, no retry. Exact Paper World UUID `93104ce4-97f1-4819-87dc-7044977e816f`, subject UUID `dcae346d-e66f-331a-b459-a5a5370e9738`, native session `71d219ce-3da9-481c-8936-89647f25c5e1`. Java exit0, Node exit0, clean capture/cleanup.

| Original S49 Action | Native MOVE (m) | Paper S50 WAIT ticks | WAIT samples | Prequential fixed/score pairs | Total WAIT displacement (m) | Frozen 0.65 MAE (m) |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| s49-native-move-32 | 0.626907 | 299–306 | 8 | 7 | 0.064247 | 0.003858 |
| s49-native-move-60 | 0.626907 | 499–506 | 8 | 7 | 0.122879 | 0.006805 |
| s49-native-move-87 | 0.626907 | 699–706 | 8 | 7 | 0.122879 | 0.006805 |

Physical source totals: **S49 original native actions 3; S15 clear receipts 3; S16 interpreted OUTCOME 3; original Paper surface locks 3; original eight-tick windows 3; sampled WAIT 24; sampled input witness 24; pre-next-tick frozen predictions 21, later scores 21; prior-window sealed NEXT_ACCEPT 2**. All three share identical original Paper World UUID and one original native session. W3 native Node original 105 frames / 58,502 bytes with clean EOF, one shutdown ACK, matching independently recomputed SHA256.

### Negative evidence: fixed model did not beat a cheap baseline

The fixed 0.65 predictor was intentionally not trained on the run. Its seven-pair MAEs (0.003858 / 0.006805 / 0.006805 m) are **worse** than the same-information zero-next-displacement baseline (0.002108 / 0.004605 / 0.004605 m). First WAIT-tick displacement was ≈0.04949 m for trial 1 versus ≈0.09065 m in trials 2/3 despite the same surface and same original Action length. This is interesting evidence to present to future L2 for hypothesis generation, but does **not** identify the cause (start-state, clock phase, initial velocity, Paper callback timing, etc). The last reported input flags were OFF on Paper sampled callbacks; the effective physical S15 clear tick was **not independently attested**.

## Independently downloaded original source artifacts

GitHub Actions artifact `mp11-g3-paper-one-world-three-original-windows-41289358266-1`, ID `13076239081`. ZIP SHA256 `c58e423fecbb9bbbc70e86790b912330b756e1657a9422942d1b6500a904dc59`. Full original Paper stdout (653,636 bytes), SHA256 `22d867d4efdb17403dd6105bfdd5284d23bf0c65df35f054606af7e1f4516d03`; full original W3 Node stdout (58,502 bytes), SHA256 `4dd24b895dbd57ddb45366d0c730ea6b5ef3878f0f693dcc2e63951a544f0b54` matched sealed W3 receipt. Also original config, source report and independent postrun audit. [Machine-readable independent readback](evidence/issue653-mp11-g3-one-paper-world-20261101/run1/independent-native-paper-readback.json).

Offline prereqs source CI Python3.12 **98 PASS**, Ruff/compileall/contracts PASS; Java plugin Maven **BUILD SUCCESS**, default `s50-mp11-multitrial-dev: false`. Exact final evidence-report HEAD may differ from the physical executable HEAD; do not claim a post-run source change has run physically unless a later World is explicitly executed.

## Remaining gates / next development

- **G1** real L2 OPEN Gemma hypothesis choice and next-trial selection: NOT RUN. The Stage0 fake OPEN provider has only exercised the API and internal feedback ledger, not actual cognition.
- **G2** multiple original S49/S16 Actions on one server: physical DEV PASS.
- **G3** three original S50 eight-WAIT windows from **the same Paper World UUID**, tied to three original Action IDs: physical DEV PASS, without varying input duration, ice, initial velocity or model structure.
- **G4** freeze real L2's hypotheses prospectively; use observations from prior trials to choose a non-scripted subsequent experiment; independently heldout prediction/cheap-rule comparison: NOT RUN.

Recommended next: introduce real `RelayEngine.open` model provider as **read-only shadow** first, with exact source-coupled *previous* trial Paper/S16 diagnostic and bounded condition choices. Require the model to choose a next **physical condition** and predict the outcome **before** corresponding Action; do not let L2 issue motor commands or edit Paper physics directly. The current S49 near-zombie Action still has identical input duration and three controlled external stimuli; implement actually distinct SHORT/LONG movement if attempting causal experimentation. The Paper raw Source readback is only independently final after server shutdown; L2 online intermediate provenance must be bound to prior marker bytes and qualified callback count without waiting for final stdout.

Classification: `MP11_G3_ONE_REAL_PAPER_WORLD_3_ORIGINAL_S49_S16_3_S50_WINDOWS_DEV_PASS / REAL_L2_NOT_RUN / SCIENTIFIC_MODEL_LEARNING_NOT_ADMITTED / CHEAP_ZERO_BASELINE_BETTER / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. No main merge.
