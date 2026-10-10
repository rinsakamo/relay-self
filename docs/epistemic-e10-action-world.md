# Lane A E10 one-episode Action/World composition

Issue #559; stacked directly on frozen E9
`527da1585f24df65694937b12b8b8dafca578ba6`. This apparatus is an explicit caller
function, not a launcher, controller, new cognition owner, or E5 authorization.
E5–E9 source/evidence and their manifests remain unchanged.

## Executable boundary

`experiments.epistemic_e10_action_world.run_episode` accepts the current,
S23-supervised terminal Action3 and its original EXECUTED World consequence,
current recovery Skill/Intent, retained rev1/value4, explicit S29 grants, a sole
reader cursor, and caller-owned consumed session/reset identity sets.

E0 uses only `price_quarters` and `prior_ref=uniform-nearfar-v1`. NO_OBSERVE and
expensive CHEAP_EXACT issue no pre-decision probe. Forced OBSERVE and cheap
CHEAP_EXACT consume exactly two source-correlated reads: far180cm first, then
caller-granted second evidence for existing S24. The first receipt is passed
through S29's existing `previous_receipt` ancestry check; the second is the
only evidence supplied to the S24 decision. The caller supplies measured
observation/inspection times in the same monotonic domain, plus an appropriate
max_age_ns (the inherited test default is 5ns).

Two minimal typed seams were missing. E3 now forwards an optional existing S29
`previous_receipt`; its default one-read behavior and policy are unchanged.
S24 now returns the exact internally produced ControlCandidate, RouteDecision,
AdmissionDecision and ExecutionAdmissionCriterion in its immutable trace.
No route or admission is fabricated from `selected_candidate`. ADMITTED still
issues zero Actions and cannot build a Mineflayer command.

For MOVE_AWAY, S14 validates these exact values, starts a distinct Skill
execution, and proposes a distinct bound Action4. A separate caller authority
must return that exact Action's AUTHORIZED descendant. ActionSupervisor issues
it, existing S15 executes bounded MOVE_BACKWARD, and the existing
`require_fresh_second_consequence`, S16 interpreter and supervisor close it.
`propose_explicit_recovery_action` remains the Action3 proposal seam; it is not
reused for Action4 because its S22 FAILED-original-Skill assessment does not
represent S24's new decision.

Frozen E5's auditor explicitly requires a distinct S15 session ID. Action4
therefore receives a separately caller-owned execution adapter with the same
declared host/port/avatar configuration, distinct session ID, and exclusive
native cursor beginning at seq1. This does not independently prove World or
avatar continuity; offline doubles only prove mechanical linkage. The caller
must acquire/qualify that session under future explicit physical authority;
this function never starts, reconnects or copies a bridge. The E9 read-only
operator pipe cannot supply the required execution interface.

Native frames retain original objects/session/seq, exact dispatch/cleanup IDs,
and request IDs. Session/reset identities are consumed even by WAIT or failed
attempts and cannot be reused by another arm. WAIT neither starts a Skill nor
calls Action authorization/issue. Source contamination and late results fail
before OUTCOME promotion. Caller-owned supervisor state remains inspectable
when a rejection occurs after issue; no retry is provided.

S16 meanings remain separate: EXECUTED -> OUTCOME; explicit rejected dispatch
-> known failure OUTCOME; transport failure -> UNKNOWN; complete but
unqualified movement -> UNAVAILABLE. UNAVAILABLE cannot close the Action.
E10 subsequently services the existing deadline and records TIMEOUT separately
while preserving the UNAVAILABLE interpretation. Frozen E5's synthetic receipt
schema represents UNAVAILABLE as pre-timeout ISSUED; this complete E10 receipt
is not silently relabelled or claimed to be an E5 audit_bundle receipt.

The independent evaluator requests a different native ID strictly after the
final Action/WAIT and at or after a fixed declared horizon from decision.
Default horizon is 1 second; event times use an injected monotonic clock,
with production perf_counter_ns by default. Total elapsed, the sum of the two
policy transport durations, and evaluator transport duration are measured
separately with perf_counter_ns. Its health/position sample never enters E0 or
S24. Missing evaluator evidence leaves damage/movement None, never zero or
safety. Health delta is signed baseline health minus later health; it is not
attribution of harm to this Action. Movement is 3D displacement from Action3's
post-observation, not cumulative travelled distance. Hunger/energy are absent
unless separately measured. Native objects are structured evidence, not original
wire bytes or independent source authentication.

## Separately authorized future physical episode

Before any live transaction the operator must approve the exact disposable
World, fixed budget and configuration; E10 has no live launch entrypoint. The
existing E9 Creative/NoAI World and all original evidence stay preserved.
The proposed new isolated baseline is Java1.21.8 / Mineflayer4.39.0, Survival,
normal difficulty, mob AI enabled, flat enclosed level surface, no other mobs,
health20/food20 at baseline, no armor/effects/invulnerability, same declared
seed/scenario as the selected frozen `e5.planned_trials()` entry. Use a fresh
reset/session per arm; do not turn one episode into three arm trials.

For the single golden engineering episode, recheck native far1.8m and
near0.2m under these conditions, with the exact target ID and measured positions
in each source receipt. Collision/knockback must be recorded and a target that
is not at the declared distance is a failed geometry condition, not silently
repositioned or reclassified. Keep the test bounded to the declared one-second
post-decision evaluator horizon, one Action3 and at most one Action4; stop on
unexpected entities, death, displacement outside the enclosed area or cleanup
failure. An evaluator arriving late retains its actual timestamp/latency and
cannot be represented as exact-horizon physical evidence. This proposal is
not a frozen 36-episode design change or an execution grant.

The authorized caller must capture PRE and POST original server configuration
and saves, original Java/Node/adapter logs and raw JSONL, process/build/session
identity, both request IDs/sequence, Action lifecycle/binding/authority chains,
independent evaluator bytes, measured timestamps and SHA256 manifest in a
private Git-external evidence root. Capture rejected/unknown/unavailable
attempts too. The E5 auditor and all ten E6 interlock capabilities still apply;
E10 does not set them PASS from a local receipt or digest. Independent review
is needed to authenticate the source and avatar continuity.

## Evidence ceiling

Focused fake-World tests and exact-head CI establish deterministic wiring and
negative controls only. No physical Action3/Action4, server/Node bridge launch,
E5 scientific trial, LLM or GPU is executed here. E5 physical status remains
NOT_RUN / UNDETERMINED. After this Draft, the next decision is a separately
authorized single genuine episode, with no automatic 36-trial successor.
