# S11 Bounded Retained Cue-Conditioned Habit Selection

## Purpose

S11 defines HABIT as deterministic read-only reuse of an owner-local retained
cue-conditioned repertoire. Given one explicit structured cue and one explicit
retained repertoire, HABIT returns an immutable candidate suggestion.

HabitSelection is not Current Intent, SkillExecution, Action proposal,
authorization, issue, or World truth.

## Retained ownership

HabitRepertoire is the semantic owner-local retained structure. It contains a
repertoire identity, revision, immutable HabitRule tuple, and provenance.

The repertoire is not a generic HabitStore, global policy dictionary, scheduler
table, hidden action cache, or central behavior controller. HABIT reads it and
never mutates it.

Capability OFF does not delete or reset the repertoire. Capability ON does not
create one.

## HabitRule and HabitCue

Each HabitRule contains habit identity, one or more exact CueFeature
requirements, a stable non-authoritative candidate_ref, explicit non-negative
integer priority, and provenance.

HabitCue contains structured cue identity, an immutable unique-key CueFeature
tuple, and provenance. Cue values are limited to bool, int, or one structured
string token. Natural-language cue parsing is not implemented.

## Exact matching

A rule matches only when every required cue feature is present and has exactly
the required value. Missing required features and explicit value differences are
ordinary non-matches. Malformed inputs fail closed before matching.

## Selection semantics

With zero matching rules the result is NO_MATCH.

With one unique highest-priority matching rule the result is SELECTED.

If multiple matching rules share the highest priority the result is TIED and no
candidate is selected.

Rule order never resolves a tie. Age, recency, usage frequency, candidate name,
and hidden strength never affect selection.

## Determinism and read-only behavior

select_habit(repertoire, cue) is pure/read-only. Same repertoire plus same cue
produces the same HabitSelection. Selection does not alter repertoire revision,
rules, priority, usage count, cue, or candidate references.

## Capability and descriptors

HABIT has no capability dependencies and has exactly one retained state scope:
owner_local.habit_repertoire.

The only operator is habit.select, implemented by relay_self.habit.select_habit,
with READ_ONLY effect and no hidden persistent state. It writes only a transient
habit selection.

The criterion habit.explicit_priority_orientation is COGNITIVE_ORIENTATION:
after exact cue matching, retained explicit priority orients preference among
valid matches. Syntax, type, and duplicate-key checks remain contract validation.

## HABIT versus PLAN

PLAN compares transient explicit alternatives under an explicit
PlanningCriterion. HABIT directly reuses retained cue-conditioned mappings.
Neither owns execution authority.

S11 qualifies a deliberate disagreement: PLAN can select WAIT while HABIT selects
MOVE_AWAY. Both outputs remain independent. HABIT never calls PLAN; PLAN never
reads HabitRepertoire implicitly; S11 adds no arbiter.

HABIT is therefore an alternative branch rather than a serial stage after PLAN.

## HABIT versus LRN

Habit use is not habit learning. HabitSelection is not LearningFeedback.

S10 LRN can update a separate LearningPreferenceState under its own authority.
Such an explicit LRN update leaves HabitRepertoire and HabitSelection unchanged.
S11 does not acquire, reinforce, weaken, extinguish, or reprioritize habits.

## ON/OFF and no fallback

PLAN ON plus HABIT OFF still executes PLAN, suppresses HABIT work, preserves the
repertoire, and fabricates no HabitSelection.

HABIT ON plus PLAN OFF still executes HABIT, suppresses PLAN work, and fabricates
no PlanSelection.

NO_MATCH does not invoke PLAN. Unavailable PLAN does not invoke HABIT. No hidden
fallback or arbitration loop exists.

## Provider boundary

ProviderExpression text does not become a HabitRule, HabitCue, or
HabitSelection. S11 adds no natural-language habit extraction and no
provider-created retained rule.

## Authority boundaries

HABIT does not mutate PersistentCognition, Memory, Current Intent,
SkillExecution, ActionLifecycle, AttentionSelection, BeliefAssessment,
ConceptRepresentation, PredictionResult, PlanSelection, LearningPreferenceState,
or HabitRepertoire.

Existing PROPOSED, AUTHORIZED, and ISSUED Action states remain unchanged. A
selected candidate_ref remains inert metadata.

## Why HABIT is not a central executive

HABIT has no scheduler, background cue monitor, action issuer, plan arbiter,
learning loop, mutable policy controller, recency heuristic, model/provider call,
or dynamic descriptor dispatch. Caller/source owns why work is due and supplies
the exact cue and retained owner snapshot.

## Deferred

S11 intentionally defers automatic habit acquisition, reinforcement, priority
learning, extinction, usage-frequency adaptation, recency heuristics,
LLM-derived habits, natural-language parsing, PLAN/HABIT arbitration, automatic
Intent commitment, Skill start, Action proposal/authorization/issue, policy
learning, RL/TD, global behavior control, and background habit execution.
