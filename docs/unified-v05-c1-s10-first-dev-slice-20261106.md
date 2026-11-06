# Unified v0.5 — first C1→C4 motion-learning DEV slice (2026-11-06)

**Classification:** DEV / SOURCE-SHAPED OFFLINE FIXTURE ONLY. No real World, new Minecraft Action, real Gemma, autosave, persistent Memory write, Habit/L0 promotion, QUALIFICATION or SCIENCE.

## Source baseline

- Unified design #717 / Draft #718 @ `9709e41e` remains docs-only; protected main @ `4348a614`.
- Branch was started exactly from Bug-0 D3 #752 @ `fa17b9eddc00c58a85b91af64bf34bacef868c1a`; the existing S49 ATTACK/killer/loot/600tick work is **not** modified.
- Reused: original `NormalActionReceipt` (S49/S16), `IntentCommitment`, `WorldConsequence`, `LearningPreferenceState`, `read_retained_preference`, `propose_learning_update`, `commit_learning_update`. No second Action issuer, Memory store or learning owner.

## Implemented thin seam

1. The current Learning owner supplies a read-only exact-instance snapshot. The motion expectation is read as a bounded, **DEV-only decimeter scalar** and tied to a native pre-Action source sequence. This is a forecast about displacement, **not a prediction of Goal attainment**.
2. After an already committed execution Intent reaches a terminal transition, group 1–8 distinct original MOVE Action receipts into **one Intent attempt experience**, not one experience per S16. Require matching Intent/session/Action/native source/ordering, finite observed displacement and a pre-outcome forecast. Mixed/stale/foreign/missing evidence rejects or remains UNKNOWN.
3. Produce structured increase/decrease/hold feedback from the prediction error, then route it through the **existing** S10 revision/authority-checked commit API. This technical owner-authority does not mean per-experience human approval; it is not authority to issue an Action.
4. A later **different Intent** can read the exact returned owner snapshot: e.g. prior expected motion `0.7m`, source-shaped observed `0.31m`, S10 revision 0→1/value 7→6, next forecast `0.6m`. This demonstrates a deterministic offline *forecast change* from an experience, **not** actual live Self behavior, improved prediction quality or novel learned physics.

The experience has a stable composite ID for caller-side deduplication. It is an immutable association of existing receipts; **there is not yet** a durable C1 experience registry, repeated-attempt owner or 60-second checkpoint. Original World evidence cannot be fabricated by this module, but its offline typed fixture is **not independently physically attested**; operator and S49 custody remain required for live use.

## Negative controls

Offline checks include unattempted/nonterminal Intent, two Actions counted as one experience, cross-session or cross-Intent Action, old/duplicated original S16 Action, post-hoc source sequence, stale native after read, UNKNOWN Action blocking learning, denied S10 owner authority, foreign target, exact retained instance mismatch and repeat-update rejection after owner revision advances.

## Following handoffs

- **S #537 / Bug-0 #742**: bind the same original `NormalSessionActionExecutor.intent` instance, qualified S49 close readback and a next-epoch native probe; do not turn this offline seam into an issuing executor. Obtain an Intent-level goal assessment separately from motion displacement.
- **WB #632/#633**: project fresh SelfBody/SelfWorld cues as fallible views (with source and UNKNOWN); do not expose real WorldBody physics to Self.
- **L #431**: carry retained exact owner identity/revision across consecutive original Intents, then link conditional cue/learning and, only as useful, Habit. Experience ≠ verified understanding ≠ beneficial behavior. No permanent L0 ban.
- **C1/C4**: integrate replay-resistant durable per-attempt evidence referencing the existing Memory writer, amendments to UNKNOWN, and checkpoint independent of the 60-second B autosave.
- **R/V #619**: qualify real source and do later scientific comparisons; not a DEV blocker.

The next physical experiment should observe an actually executed Intent in one World, commit retained feedback after authentic qualified terminal evidence, then show a **later genuinely selected forecast or Action** consuming the new exact S10 owner. A synthetic change in a test is only the first software seam.
