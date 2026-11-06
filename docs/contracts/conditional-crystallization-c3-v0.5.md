# Unified v0.5 — Contract C3: Conditional crystallization and re-escalation

> **Status: C3 DESIGN PROPOSAL / USER REVIEW OPEN / NOT IMPLEMENTED.** Prepared 2026-11-06. Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), [C1 Intent Experience](intent-experience-c1-v0.5.md), [C2 Understanding Revision](understanding-revision-c2-v0.5.md), [A Intent/Action](intent-slots-action-authority-v0.5.md). Owner references: [#431 Learning/Habit](https://github.com/rinsakamo/relay-self/issues/431), [#426 development](https://github.com/rinsakamo/relay-self/issues/426), [#537 Action](https://github.com/rinsakamo/relay-self/issues/537), [#619 science](https://github.com/rinsakamo/relay-self/issues/619).

## C3.0 Core definition and Grand Null

**Crystallization = preserve a useful understanding while making a suitable, condition-scoped part of its prediction or decision executable by a lower-cost cognitive mode, with an explicit boundary and re-escalation path.** It is not blindly copying L2 text into code, turning every correct episode into a habit, or ranking L2 superior to L1/L0.

**Grand Null:** for familiar, stable conditions, the existing fixed L0/S49 behavior may already be best. It is legitimate to keep it unchanged. Use existing owner-local Memory/Learning/Habit, `HabitCue` / `HabitRule` / `HabitRepertoire` / read-only `select_habit` patterns where appropriate, not a new distillation service or universal policy database by default. The audited WB DEV branch does **not** establish full executable cross-layer crystallization in main.

An experience from C1 may yield C2 revisions; C3 only determines **how retained meaning might be reused**. Thus:

```text
Qualified Intent Experience (C1)
  -> conditional understanding/candidate revision (C2)
  -> retain/propose via genuine owner (C4 governance)
  -> bounded retrieval and shadow candidate
  -> qualified L1 conditioned preference / prediction reuse
  -> optional independent formal L0 proposal (NOT automatic)

Mismatch, unfamiliar cue, source staleness, unexpected cost or failure
  -> abstain / fall back to proven safe control / reconsider / L2
  -> new C1 experience and C2 revision as appropriate
```

The important property is **reversibility of selection**, not erasure of the old evidence or rewrite of a reflex in place.

## C3.1 Different layers are different jobs, not stages of worth

| Mode | Normal role | Crystallization meaning |
| --- | --- | --- |
| **L2** | Explain unknown observations, compare hypotheses, plan tests, revise model structure/conditions | Generates or evaluates candidate understanding; not an automatic action or learning authority |
| **L1** | Contextual anticipation and conditional low-cost selection from retained experience | Applies cue-scoped preferences/predictions; the first target for ordinary crystallization |
| **L0** | Bounded low-latency guard/closed-loop skill and existing tested reflex | Only narrowly formalized, deadline-safe and owner-authorized routines; may be excellent with no learned change |

Development is **not a compulsory L2 -> L1 -> L0 pipeline**. L1 can learn from its own C1 experiences; L0 outcomes can raise a question for L1/L2. A learned L1 habit may never become safe to promote to L0. A runtime may employ L0 to survive an uncertain condition while keeping the L2 investigation pending.

## C3.2 Condition-scoped reusable candidate

The minimum *logical* representation (not a new Python class/API) connects:

- **What was learned:** references to retained C2 model/selection update and C1 source experiences; version and hypothesis/assessment state.
- **When applicable:** typed cue conditions (e.g., floor class, surface uncertainty, bodily capability/viability, obstacle/threat coverage), positive/negative examples and source freshness; known-UNKNOWN must not silently match.
- **What is reused:** source-qualified prediction or guarded Intent/Plan/Skill candidate, never a grant to physically issue an Action.
- **Why trust it enough for this role:** corroborated outcome or explicit tentative/shadow status, known counterexamples, independent next-episode reuse evidence and expected compute/body/time cost.
- **When to stop using it:** mismatch, source changed, contradiction, OOD/unknown cue, viability constraint, expiry/stale owner revision, unsafe deadline, unexpected repeated failure or worse-than-cheap costs.
- **What to do next:** safe fallback, explicit abstention, reconsideration, or bounded L2 escalation with trigger/evidence refs and finite cost/deadline. Emergency L0 cannot be blocked waiting for L2.

One reusable item should preserve the link between the *original understanding* and the cheaper result. It may summarize without carrying every original datum into runtime; the source evidence remains retrievable in existing owned stores. Typed cue matching and version checks are preferable to an unconstrained LLM-generated natural-language action rule.

## C3.3 Four distinct readiness states (do not conflate)

| State | What is shown | What is *not* implied |
| --- | --- | --- |
| **CANDIDATE** | A model/conditional habit hypothesis inferred from one or more C1 experiences | Truth, generalized rule or authority |
| **SHADOW_REUSE** | Reads matching cues and compares a candidate against current cheap choice without acting through the candidate | World policy improvement or new S49 authority |
| **L1_RETAINED_REUSE** | Existing governed owner has admitted a condition-limited low-cost L1 selection/readout, which is later consulted | Independent proof of benefit or safe L0 execution |
| **L0_PROMOTION_PROPOSED** | Explicit *proposal* for a formal reflex/Skill with guard, known errors, deadlines and rollback | Executable code, verified timing, physical admission or automatic promotion |

An actual **L0 implementation/adoption** requires a *separate* owner-reviewed safety/authorization gate (C4, S/Skill contracts and DEV/QUAL rules). Calling an L1 habit 'L0' or observing repeated success does not satisfy that gate. An L2 answer selected in one episode is not a reusable Skill merely because it can be read back.

## C3.4 Learning cost and useful long-horizon behavior

Compare the cheaper candidate against simple fixed L0, no retained experience, exact episode lookup and (where useful) deliberative L2 under the same actually available cues and acceptable cost constraints. Distinguish:

- **Acquisition cost:** exploration attempts, missteps, L2 token/latency/compute, WorldBody energy and physical losses during learning.
- **Expression cost:** retained L1 lookup, source validation, error/fallback, execution overhead and later L2 requests.
- **Outcome:** actual Intent-level World success/survival/goal satisfaction, not simply number of L2 calls avoided.
- **Transfer and retention:** reuse in an independent next opportunity; shift detection, abstention and recovery when context changes.

**A single-episode L1 > L0 score is not a required DEV gate.** If existing cheap L0 does equally well, report `CHEAP_EQUIVALENT` or no demonstrated incremental benefit and do not force extra machinery into execution. Reduced L2 calls alone can be a resource saving when safety/outcome remains acceptable, but cannot prove generalization, learning-induced behavior change or an improved World outcome by itself.

Fixed iteration/episode counts are not a biological constant or a free pass: a narrow low-risk hypothesis can become useful with fewer experiences than a dangerous L0 guard, and success evidence must be independent where the claim requires it.

## C3.5 Decrystallization, fallback and return to inquiry

On mismatch or invalid source, **do not mutate World observation or pretend a known-habit cue is valid**. Treat the existing habit as `NO_MATCH`, stale, contested or temporarily not applicable under the actual owner semantics; preserve original rule history. Prefer bounded source re-observation and safe available Skill/Intent checks. Where safe and budgeted, escalate a specific explanation/question to L2, carrying both the unexpected C1 outcome and the retained model's prior expectation.

A previously accepted habit can later be constrained, versioned, suspended or rolled back via its legitimate owner. **Decrystallization means losing present applicability/selection privilege, not deleting past experiences or automatically rewriting learned rules.** The Self may maintain multiple contradictory context-specific hypotheses until evidence discriminates them.

## C3.6 Bug-0 examples

| Situation | Suitable behavior | Re-evaluation trigger |
| --- | --- | --- |
| Ordinary floor repeated walking | Existing low-cost L0 movement stays default; no need to invoke L2 on every step | New slip, unmodeled displacement, source shift |
| On an unfamiliar icy floor, EVADE outcome differs from prediction | C1 episode -> C2 surface/body hypotheses -> read-only L1 cue prediction candidate; later validate/apply narrow floor condition | Unknown floor, wrong gait, excessive error, missing source |
| Eating while threat nearby | Retained L1 cue may suggest 'threat response before EAT' while preserving independent committed EAT; S49 still arbitrates real channel | Hunger urgent, unseen enemy, inability to flee, bad outcome |
| REST with qualified fatigue signal and measured recovery | Retain condition-limited estimate of when rest is useful; zero-action REST may still be a genuine Intent experience | Body reading/viability mismatch, recovery effect UNKNOWN |

These examples describe possible learning routes; they do not claim new learned behavior currently exists in RelaySelf.

## C3.7 Acceptance controls proposed (C3-01–C3-13; NOT RUN)

| ID | Case | Expected result |
| --- | --- | --- |
| C3-01 | Already-stable, low-cost L0 handles known floor | No forced L2/L1 or spurious promotion |
| C3-02 | L2 produced one plausible explanation without independent source confirmation | Candidate only; no automatic learned L1/L0 policy |
| C3-03 | Same physical evidence but source/coverage omitted | No falsely confident habit applicability |
| C3-04 | Context cue matches and candidate is retained under proper owner | Lower-cost L1 readout may be used, S49 grant still independent |
| C3-05 | Multiple rules tie, cues conflict, or critical cue is UNKNOWN | Explicit TIED/NO_MATCH/ABSTAIN fallback, no arbitrary high-priority physical issue |
| C3-06 | A cheap prediction equals learned candidate at that opportunity | Report CHEAP_EQUIVALENT, not proved learning benefit |
| C3-07 | Model predicts standard floor motion, new ice disobeys | Preserve error, disable wrong scope, escalate when safe |
| C3-08 | Repeated performance failure after L1 retention | No silent overwrite; owner-governed suspend/rollback request |
| C3-09 | L1 habit has strong repetitions but unsafe/unbounded worst-case time | No L0 promotion |
| C3-10 | A formal L0 candidate lacks safety/authority verification | Proposal only; current S49/Safety L0 unchanged |
| C3-11 | A later independent attempt reuses a rule but outcome fails | Reuse evidenced, improvement not claimed; C1 new failure episode |
| C3-12 | Same source after World/session reset or expired owner revision | Old cue/action permission invalid, historical memory may remain |
| C3-13 | L1 learns directly after observed failure, L0 triggers upward investigation | Both allowed; no compulsory L2-origin stage |

## C3.8 Implementation direction and remaining C4

Start with **read-only/shadow conditional retrieval** reusing existing `HabitCue`, `HabitRule`, `HabitRepertoire`, `select_habit` source checks where applicable; compare with fixed-cheap behavior and later C1 experience results. Only if owner-approved and grounded should condition-limited retained L1 use be attempted; keep L0 auto-promotion out of Bug-0. Model and Skill/Action authority must remain independent. C4 will define the write authority, rollout, rollback and learning-validation admission, without reclassifying DEV success as QUAL/SCIENCE.

**Classification: C3 DESIGN PROPOSAL / NO TESTS EXECUTED / NO NEW MEMORY, LEARNING OR ACTION OWNER / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
