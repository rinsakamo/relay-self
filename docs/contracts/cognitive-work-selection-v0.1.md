# Cognitive Architecture v0.1 / 04b — Present + Schema to L1 Work Selection

> Parent #828, child #841. Stacked on #835 PR #836 → #833 PR #834 → #831 PR #832 → #829 PR #830.
>
> **DRAFT / OFFLINE PURE CONTRACT / NO WORLD, GEMMA, GPU GRANT, S49 OR QUALIFICATION.**

## 1. Why this boundary is needed

Schema output is a conditional cognitive pattern, **not** a chosen Goal/Intent
and not an Action script. Motivation-producing Schema may emit a Need; temporal,
causal, and metacognitive Schema may also produce evaluations, predictions or
Question candidates. Present is a transient projection of 3Self plus already
retained owner Goal/Question/Intent refs and eligible Schema outputs.

A Self must decide **what cognitive work to undertake next**, including whether
to revisit a Goal, review a Question, wait, or seek open L2 reasoning. Assigning
this choice to a hard-coded central Task Selector contradicts the Self-owned Goal
principle. Assigning it to L2 every epoch wastes scarce hardware.

The key recursion is: a regular #835 Task requires an already-adopted Goal,
Question or Intent; but the work **of deciding whether to adopt one** must start
before such a reference exists. Therefore a CPU-owned, ephemeral L1 **meta
selection task** is explicitly constructed from an already projected Present,
without creating a new owner or an adopted Goal.

## 2. Narrow interface

1. Existing #833 projection validates 3Self owner references, Schema mode,
   scope/session, source revision and registry revision to produce PresentFrame.
   Schema outputs are **already included** in Present; they are not independently
   accepted twice by the selection module.
2. An existing Self/Present cognition owner supplies a finite list of
   CognitiveWorkCandidate values:
   - candidate_ref and description, scoped to the observed state/understanding;
   - origin_kind+origin_ref to an active Goal, Question or Intent **or** a
     qualified Schema signal event_ref when origin_kind is None;
   - proposed downstream cognitive requirement SELECT_FINITE or OPEN_REASONING;
   - source provenance. No innate Minecraft-specific skill, item, policy or
     priority ranking is preinstalled.
3. If zero candidates exist, **no model call** is warranted.
   If at least one exists, the pure builder adds the exact explicit option
   NO_NEW_WORK and constructs one #829 CognitiveTask(SELECT_FINITE) and one
   existing RelayEngine.BoundedChoiceRequest. The meta task has no Goal/Intent
   reference, is bound to frame/owner/registry revisions, and is not an action.
4. Existing CPU ProfileSelector and actual runtime must separately admit L1.
   The request sets think_allowed=False, preventing hidden THINK escalation.
   A resource snapshot or profile route is **not** proof of GPU acquisition.
5. One L1 model result is validated against the original task, proposed
   choice set, source/session, task generation, deadline, frame/registry/owner
   revisions, and verified compute admission. The output is solely a
   WorkSelectionProposal.
6. The Self owner **may** accept or reject that proposal. A selected
   Schema-origin work proposal must first go through the ordinary explicit
   Question/Goal adoption contract, because its signal is not an adopted Goal.
   A selected already-active owner origin may proceed to the existing
   #835 bind_present_task, with a separately assigned task ID, resources and
   deadline. None of these steps are auto-issued by this module.

The no-work outcome is legitimate: constant signal generation does not force
constant cognition. Original emergency L0 FastCue bypass remains independent.
Abstention/timeout/DEFER does not auto-escalate to L2; the owner may formulate a
new Task in a later decision epoch if warranted.

## 3. Minimal shape

    PresentFrame
      - three_self: MySelf / SelfWorld / SelfBody references
      - eligible Schema signals (including Need / Question candidates)
      - active Goal / Question / Intent owner refs
         |
         v
    WorkCandidate[] (owner-supplied, grounded, not action sequences)
         |
         v
    CPU constructs Meta CognitiveTask SELECT_FINITE
      + RelayEngine.BoundedChoiceRequest
      + explicit NO_NEW_WORK
         |
         v
    Existing L1 backend / compute admission (not implemented here)
         |
         v
    L1 choice or UNRESOLVED
         |
         v
    source / revision / generation / deadline / grant checks
         |
         v
    WorkSelectionProposal (not a commitment)
         |
         v
    existing Self owner adopts / holds / declines
         |
         v
    #835 regular CognitiveTask -> #829 Profile -> L0/L1/L2
         |
         v
    cognition result / original S49 for any actual physical Action

No recursive selection task. No new Goal registry, action issuer, cache manager,
universal priority function, or mandatory per-tick L1 calls.

## 4. Prompt/cache orientation

The pure example puts transient model-facing context in a deterministic
serialization order: Present projection refs, then Schema signals sorted by
event ID; choices are sorted by candidate ID, with no-work last. Identity can
be supplied via the existing RelayEngine identity_context. A later proper
context compiler may use:

    [shared stable Identity / rules / Schema definitions]
    [less-variable selected Memory / persistent Goal context]
    [volatile Present + Schema signal values]
    [task-specific L1 choice suffix]

This is a **semantic/token ordering candidate**, not actual measured KV reuse.
Changing a token in the shared prefix, using a different model/tokenizer,
evicting the cache, or disabling llama.cpp cache_prompt prevents a KV claim.
RelayLM current v1 production cache policy remains OFF; no new backend policy
is enabled in this PR.

## 5. Key negative controls

- One grounded work candidate and NO_NEW_WORK; zero candidates does not
  trigger provider work.
- Multiple candidate kinds and Schema-sourced candidate from a qualified
  Present; no implicit Goal commitment.
- Unknown/unadopted origin, wrong Self or World session, duplicate candidate,
  native L0 FastCue disguised as L1 work -> rejected.
- Stale Present, source, owner/registry revision, generation, deadline,
  fabricated choice, L1 UNRESOLVED or no verified compute admission -> rejected.
- No implicit L1→L2 fallback, World effect, memory write, actual Intent release,
  Skill selection, physical Action or World/Gemma run.

## 6. Integration still missing

- Real current owner-provided candidate generation/ranking and its provenance,
  beyond the typed pure interface: not a hidden script or global priority
  algorithm. Need weights/temperament/temporal predictions are future inputs
  from #831/#833, not mandatory fields in a universal Score.
- Real L1 runtime resource admission/preemption from #828/05 and actual
  RelayEngine model wiring; no fake GPU grant.
- Real Goal/Question lifecycle and candidate owner decision from #833;
  actual S49 and Learning/Memory remain original owners.
- Connected end-to-end World/Gemma test is separate from successful offline CI.

**Status:** concept and bounded contract implemented in this Draft only.
Passing tests demonstrates interface coherence, not self-directed agency.
