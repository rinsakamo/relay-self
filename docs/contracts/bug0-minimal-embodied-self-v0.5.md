# RelaySelf v0.5 — Bug-0 Minimum Embodied Self («流暢にしゃべるゾンビ»)

> **STATUS: BUG-0 CONCEPTUAL SCOPE FROZEN (2026-11-07) / OWNER INTEGRATION AND END-TO-END TESTS OPEN.**
> [v0.5 freeze handoff](../unified-v0.5-design-freeze-20261107.md). #742 now tracks real zombie loot/pickup/eat/600-tick respawn and repeat cycles; past DRAFT/open review questions remain technical work, not blockers to v0.5 design closure.
> Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), Draft [#718](https://github.com/rinsakamo/relay-self/pull/718). This is a bounded **initial scope**, not a new action grant, code authority, physics model, learning approval, proof of success, or revision of main. Applies only to existing legally authorized owners.

## 0. Why this slice

The first Self is an inexperienced Minecraft avatar with unusually fluent language but **limited embodied competence**. Do not demand a sophisticated internal World simulator, autonomous training, broad planning, or strong cognition before it can act and learn in a small observable niche. The first target is an attributable loop:

```text
qualified World/WorldBody observation
    -> minimal SelfWorld / SelfBody / MySelf projections
    -> multiple candidate Needs/Goals and retained Intent commitments
    -> bounded Goal/Intent arbitration
    -> admissible existing Skill/primitive Action path (single physical issuer)
    -> native clear + qualified consequences / UNKNOWN
    -> separately authorized experience integration
    -> later epoch: conditionally different decision
```

The sequence is a **proposed integration target**, not a single observed end-to-end run.

## 0.1 Existing code reuse (source audit, no new owner)

The initial Bug-0 behaviors already have significant code in `main` and in S/WB/P1/M/L Draft branches. [Existing-assets audit](../bug0-existing-assets-audit-20261103.md) records exact source paths, branches, existing tests and the Grand-Null verdict. **EAT and ATTACK are existing Mineflayer native effect classes, not proposed additions.** The missing work is scoped source-correct **composition/admission/experience** into Bug-0, not reimplementing Skills. Physical S49 readiness and live owner qualification remain separate.

## 1. Six basic behaviors — vocabulary, not six new primitive APIs

| Behavior | Semantic level | Initial eligibility / preconditions | Evidence after attempt | Fail-closed / negative case |
|---|---|---|---|---|
| **MOVE / STOP** | MOVE Skill and authorized primitive commands; STOP requires confirmed input clear and settling qualification | Fresh position, movement feasibility, current Intent, action/grant/resource admission | S49 primitive Action ID, S15 clear, S16 result, positions, post-clear movement if relevant | Closed Action ≠ stopped body; unknown settling blocks unsafe reuse |
| **EVADE** | Goal-dependent conditional Skill, initially decomposed into existing MOVE actions | A currently grounded threat and a feasible retreat direction | Threat distance and motion after MOVE, not mere issue | No invented safe route when obstacle or threat position unknown; may DEFER |
| **EAT** | Need/Goal -> retained Intent -> food-use Skill; **existing Mineflayer equip/consume primitives and controlled EAT Skill**; S51 owner extension exists in an unmerged Draft, **not yet part of MOVE-only S49** | Fresh hunger/food/inventory/hand availability and safe enough moment, valid food-use authority | Inventory/item-use/hunger or other qualified WorldBody readback; explicit failure/UNKNOWN | No food / stale hunger / hand conflict -> no use; issue ≠ eaten |
| **ATTACK** | Threat-dependent Intent -> attack Skill; **existing Mineflayer attack primitive and controlled FIGHT Skill**, **not yet part of MOVE-only S49** | Fresh legitimate target, geometry/range/cooldown/hand availability, issuer grant | Attack issue, hit/damage, target death **separate facts** | No target/out-of-range/stale source -> DENY/DEFER; issue ≠ hit |
| **REST** | Resource-maintenance Goal/Intent/Skill; may emit **no primitive physical Action** | Need for rest, risk of delay, observable resource/viability context | Elapsed time and native body/resource readback; progress vs failed recovery | REST ≠ WAIT; WAIT does not prove energy/health recovered |
| **WAIT / OBSERVE** | Low-cost non-issuance / observation; can be a phase of another Intent | No body Action currently justified, or awaiting safe admission | No Action claim; observations separately source-qualified | No fabricated physical outcome or budget refund |

**Action-class boundary:** a label in a plan, synthetic ControlFrame, or LLM response is not a native executable action. The current S49 implementation is MOVE-only with a single current owner/one in-flight primitive. The v0.5 longer-term model retains **multiple independently live body-directed Intents** and one legitimate physical issuer, without requiring multi-channel ControlFrames in Bug-0. Start with **serial physical admission**; retain independent Intent identities for deferred work.

**REST ownership:** exhaustion/energy is not a universal Minecraft-native resource. The existing P1 physical-fatigue model ([#626](https://github.com/rinsakamo/relay-self/pull/626)) defines fatigue recovery from **externally qualified, fully inactive World-tick WAIT**, not from a REST command, mere lack of issued Actions, or blocked movement. M0/M0.2 still accounts for basal/body costs on WAIT independently and is not an automatic credit. Qualified readback and source admission are still unmerged owner concerns. Do not infer replenishment from the word WAIT, hunger, host time or command silence. Native Minecraft HP recovery has separate prerequisites and must be observed. Food and rest remain different Needs even when they interact.

## 2. Minimal three-model projection (B slice)

No three new independent memory databases or truth authorities.

| Projection | Initially necessary | Must never assert |
|---|---|---|
| **SelfWorld** | Observed nearby threat, distance, coarse obstacle/surface, available escape direction, observation source and age | Complete map, certain enemy intent, simulated alternate-history fact |
| **SelfBody** | Observed motion/velocity or measured displacement, hand/input occupancy, grounded or unknown, food/hunger, health, **M-measured or UNKNOWN fatigue** | Equating body estimate with WorldBody truth; energy recovery without readback |
| **MySelf** | Current viable Needs, retained Goals/Intent references, recent success/failure and tentative competence/condition beliefs | Normative Identity Specification, universal planner, long-horizon skill-growth optimum |

One observation may affect all three **views**, but ownership of Evidence, Belief, Self-Model, Capability Model, Goal/Commitment and Memory remains with Persistent Cognition's existing governed meanings. Projection changes from new evidence do not imply authorized Memory writes. Every projected claim needs `source_id`, `world_revision / native_seq` when meaningful, `observed_at` or bounded age, and `observed | inferred | unknown` origin. If a source lacks a field, represent UNKNOWN rather than manufacturing one.

## 3. Bounded arbitration and physical issuance (A slice)

1. Read **current** source-qualified observations and owner-validated current Intent commitments; keep Goals, Needs, Plan, Skill and Action distinct.
2. Check hard viability, threat immediacy, finite time and resources. Urgent protective L0 may fence ordinary actions; **not** silently delete EAT/REST/EXPLORE Intent.
3. With currently supportable evidence, choose a **single serial body operation** (or WAIT/DEFER). Multiple Intent candidates remain independently attributable and may later be reconsidered; no mandatory merged global Intent.
4. Check fresh preconditions, permission/grant, actual available physical channel, one issuer, source identity, action deadline and in-flight/settling occupancy. Admit only through existing/current owner-supported SkillExecution + ActionLifecycle / S49 authority or an owner-reviewed extension.
5. Record candidate -> authorization -> issuance -> clear -> independently qualified OUTCOME/TIMEOUT/UNKNOWN. A Skill's end, an Action receipt, and effects such as feeding/hit/recovery are **not the same event**.
6. Reconsider retained commitments at qualified next observation. Preemption, loss of source currentness, partial effect, unsafe physical quiescence and expired deadlines fail closed. Logical cancellation is not STOP ACK and does not prove backend/GPU/resource release.

**Minimal provisional policy** (not a universal priority score): if immediate threat is strongly grounded, prefer an admissible EVADE/ATTACK response over food/rest; if safe and hungry with food, EAT may proceed; if safe and resource-depleted, REST may proceed; if evidence is inadequate, WAIT/OBSERVE or ESCALATE without new physical Action. A hungry but endangered Self may defer food. No requirement to always attack, always flee, or always eat before resting. Goal choice should be attributable to observations, confidence, current resources and viability guards, not language fluency.

## 4. Minimal experience and conditional learning (C slice)

A qualified example is **not** necessarily an improvement:

```text
episode source: World/session, original Action ID, relevant native seq
before:      observed condition + prediction (or NO_PREDICTION)
decision:    selected Intent, Skill and action request, with alternative/defer reason
execution:   authorization, issue, clear, original terminal status
after:       separately sourced WorldBody observation(s), elapsed time, confounders
comparison:  prediction error / unknown / noncomparable
integration: retained evidence OR authorized candidate model update OR no update
reuse:       next independent opportunity, same/shifted condition, changed decision?
```

Minimum research gates:
- **Decision-change gate**: a next-epoch decision differs for a grounded reason referencing earlier experience; distinguish learned policy from an unchanged or hard-coded L0 rule and from an L2 story about experience.
- **Improvement gate (separate)**: predeclared safety/performance measure on new opportunity improves versus relevant cheap baseline. Failure to improve does **not** erase a true decision change.
- **Transfer/applicability gate**: distinguish known surface/conditions, altered conditions and UNKNOWN/ABSTAIN; never claim success in an untested environment.
- **Promotion gate**: no automatic L0 crystallization or broad authority grant. L2 hypothesis, L1 reusable conditional judgment and L0 native guard remain distinguishable, with proof-gated promotion and decrystallization/re-escalation.

Read-only World/Body experiences and L2 output alone never authorize belief/memory/Skill policy mutation. Owner L #431, WB #669, M #616, S #537 and general qualification #619 retain their respective independent review gates.

## 5. Offline-first acceptance cases (design obligations, not test results)

| Case | Setup | Required result |
|---|---|---|
| B0-01 | Threat near, hungry, food present | Threat response eligible; EAT retained/deferred, not silently cancelled |
| B0-02 | Threat gone, hunger fresh and food present | Deferred EAT reconsiderable; do not assert eating before physical outcome |
| B0-03 | No food or stale inventory | EAT action not issued, preserve reason |
| B0-04 | Target missing/out-of-range/cooldown uncertain | ATTACK cannot become assumed hit; DENY/DEFER |
| B0-05 | Rest needed, unsafe surroundings | REST may defer; idle WAIT not mislabeled recovered |
| B0-06 | Awaiting physical clear or post-clear settling | No unsafe resource double-use; closure/UNKNOWN distinction |
| B0-07 | Model proposes food use or attack but no current grant | Never issue; proposal may remain cognitive |
| B0-08 | Old observation / mismatched World session | No action authorization from stale source |
| B0-09 | Two valid Goals compete for hand/control | Body arbitration serializes/fences, preserved independent Intents |
| B0-10 | Threat disappears during action | Reconsider after actual outcome/clear/unknown, no invented instant abort |
| B0-11 | World result unavailable | Preserve UNKNOWN, do not award hit/food/recovery/learning success |
| B0-12 | Observed slip vs prior movement prediction | Source-bound prediction mismatch stored as evidence candidate; update separately gated |
| B0-13 | Same condition, next independent episode | Decision change and physical outcome independently measured; no automatic advantage claim |
| B0-14 | Different floor or new enemy configuration | Learned condition not overgeneralized; fallback/escalation allowed |
| B0-15 | STOP requested, input ACK missing | No quiescence/GPU release/energy refund inference |
| B0-16 | L2 fluent explanation but no action/result | No synthetic physical experience, evidence upgrade, or capability claim |

Offline acceptance requires executable checks with both positive/negative cases using original owner APIs where feasible. **All 16 are currently proposed, NOT RUN as this contract.** Synthetic fixture outcomes never stand in for live World/S49 source attestation.

## 6. Staging and review owners

- **B0-D0 / design-only (this document):** fixed initial behavior vocabulary and no-goals. A/B/C are **still open** for owner review.
- **B0-A0 / offline owner mapping:** reuse the already existing `main` Mineflayer `equip_item`, `consume_held`, `attack_entity` and controlled EAT/FIGHT/FLEE runners; inspect S46/S51 owner code, P1 WAIT-fatigue, M source and existing tests. Resolve their **distinct** authorities before composing. Do not reimplement native effects or grant new Actions.
- **B0-A1 / owner-approved extension:** connect **one existing behavior at a time** to the legitimate S49 serial Action owner, first S51 EAT and then controlled FIGHT if owner-approved. Preserve original native evidence, no new physical issuer, no universal action adapter. REST initially remains an Intent selecting verified inactivity rather than a new primitive.
- **B0-B1 / three projections:** read-only provenance-aware narrow SelfWorld/SelfBody/MySelf views; no new Memory owner.
- **B0-C1 / experience loop:** test one conditional next-epoch decision shift, separate from improvement and L0 promotion.
- **B0-DEV live World:** only with explicit lane-authorized execution conditions and preflight for actual supported operations; maintain DEV_ONLY / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN until evidence supports reclassification.

### Explicitly deferred D/E

**D:** high-fidelity SelfWorld × SelfBody joint counterfactual simulation and broad branching search.

**E:** MySelf long-term competence valuation, autonomous training goal generation and optimization.

Neither is a prerequisite for Bug-0. Preserve interfaces and provenance so a future version can incorporate them without rewriting Action or Memory authority.

## 7. Review questions that remain legitimately OPEN

1. Which existing **main controlled EAT/FIGHT**, **S46/S51** and **S49** hooks can be reused directly? Which additional owner-approved binding is needed so native food use and attack outcomes remain valid under the sole product issuer? See [existing-assets reuse audit](../bug0-existing-assets-audit-20261103.md).
2. REST begins as a Goal/Intent-level safe pause using verified WAIT, **not** a new motor command. Who qualifies consecutive full idle World ticks for existing P1 recovery and independently preserves M0/Paper costs and native HP observation?
3. How are multiple retained body-directed Intent identifiers represented before S49 supports more than one live current owner, without shadow-granting model output?
4. Are existing projection adapters sufficient for all minimal 3Self fields, or are narrowly scoped observational additions necessary?
5. How can L judge *learned* action selection separately from copied L2 explanations or fixed cues without leaking future World information?
6. What independent source qualifies stop/settling, per-command consequences, and cross-epoch evidence before approving the first Bug-0 World run?

**Completion criterion:** a small source-qualified, owner-reviewed real World loop demonstrates an initial behavior, outcome, retained experience, and a conditionally different later decision. Expansion to EAT, ATTACK, and REST must be demonstrated separately. The diagram, vocabulary and this design contract are not such a demonstration.
