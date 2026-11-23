# Cognitive v0.1 — Bounded Skill IR / CPU L0 Interpreter (#843)

Parent: #828. Base: #844 HEAD b7e043ff4897051e53635b327c8f928feef70ef7 (controlled REAL_EAT_PASS).

**Classification:** offline DEV shadow only. No live physical issuer added, no real Skill execution, no Skill/Intent completion, no QUAL/SCIENCE.

## Existing owners retained

The existing IntentCommitment owns current Intent; SkillExecution owns lifecycle and state; ActionSupervisor owns issued Action and Outcome; Physical ActionPort owns the nonissuing physical proposal. skill_ir_l0.py is an ephemeral sequential CPU interpreter, not a second Action owner, grant source, native issuer or learner. The #844 EAT journal/issuer code is unchanged. Full historical S49 is not imported.

## Candidate and compile contract

A SkillIR is an immutable versioned task/generation-scoped artifact with pinned Self/World, Goal, Target and at most 32 steps. Up to 10 physical Action requests and up to 60s host-monotonic duration can be declared. The limit is not a promise of timely execution.

Three step kinds:

- CheckStep: exact trusted predicate-ref, TRUE/FALSE/UNKNOWN branches; UNKNOWN is never silently FALSE.
- ActionStep: request an existing, versioned WorldBody capability and advance only after supervised Action OUTCOME. UNKNOWN/TIMEOUT/denied are STOP, never speculative reissue.
- EndStep: success/failure/unresolved *candidate*, not an authoritative Skill/Intent or Experience outcome.

parse_skill_ir_json decodes strict, bounded, duplicate-key-free model JSON with exact step kinds/fields. Scope, task id, generation and provenance are supplied from an externally qualified envelope, never L2 text. It cannot execute source code or introduce new physical affordances.

compile_skill_ir checks a caller-supplied trusted PhysicalCapability catalogue and predicate whitelist, known target kinds, nonmissing transitions, reachability, cycles, longest action path and budgets. Typed catalogue entries are NOT independently authentic evidence; gateway must attest them. CompiledSkillIR is revalidated on L0 entry. Parsing and compiling do not automatically register or install an L2-generated Skill.

## CPU-only cursor

L0SkillInterpreter requires an already committed Intent and a current STARTED SkillExecution, with matching pinned version/generation/scope; it does not commit the Intent. Each tick processes one graph node and returns NEED_OBSERVATION, ADVANCED, PROPOSE_ACTION, AWAIT_ACTION, STOP or TERMINAL_CANDIDATE.

Check requires a new source-qualified PredicateWitness matching current Self/World, exact target/predicate and increasing native seq. One Action step produces a stable scoped Action ID only once and then waits. After physical issuance, only the *existing ActionSupervisor* OUTCOME can move to the next step. UNKNOWN, TIMEOUT, owner change, deadline, interrupt and Body conflict stop further requests without falsely cancelling an already issued physical effect.

propose_pending constructs a PhysicalActionBinding from the existing pinned IR Target, current Intent/Skill, registered WorldBody capability, and native PhysicalReadback; it calls the existing propose_bound_physical_action function, producing PROPOSED only. This cannot authorize, prepare WAL, issue a native command or declare success. A physical owner must still perform independent grants, fsync-before-ISSUE, ACK/Outcome verification and replay protection.

## EAT representation and next gates

The real-World-proven EAT@1 remains one *compound WorldBody parent capability*, internally equip_item then consume_held (two unique native effects). L0 does not split these into unrelated transactions or invent food strategy. Later sequential Action requests can use registered capabilities, but ATTACK/MOVE/REST must first have source-audited physical issuers; simply naming an Action in IR cannot authorize it.

Offline tests cover normal proposed/OUTCOME flow, two sequential stable Action IDs, no duplicate proposal, stale/foreign observation, unsupported/malformed capability and source, cyclic/hidden graph, deadline, owner/Skill/version changes, UNKNOWN/TIMEOUT/interrupt, and strict untrusted JSON.

**Still open:** authenticated Self acceptance, physical process-wide owner and channel arbiter, non-EAT canonical issuer, runtime L0 persistence/restart reconciliation, physical STOP/settling, L2 Skill synthesis and adoption, real World trials for IR, QUAL/SCIENCE. Prior #844 REAL_EAT_PASS is the baseline only, not evidence for this new interpreter.


## 2026-11-14 — Opt-in L1 → L0 → original EAT issuer DEV composition (#847)

In the existing one-turn Minecraft/Gemma CLI, the optional
`--physical-eat-dev --l0-skill-ir-dev` uses the same grant and journal
requirements as `--physical-eat-dev`. The new flag without the WAL EAT
mode is refused **before** launching a World; the legacy `--execute-native`
and `--s49-readonly-shadow` routes remain incompatible.

1. The **actual** L1 choice, fixed selected Goal/Skill/Target and two fresh,
   source-correlated post-L1 Mineflayer probes still pass the pre-existing
   nonissuing S49-shaped handoff (observation admission only).
2. After committing the chosen Intent and starting the corresponding
   SkillExecution, a **fixed innate EAT@1 bootstrap IR** is bound to those
   refs and a registered EAT parent capability. This is *not* a generated,
   accepted or remembered learned Skill.
3. L0 emits a single `PROPOSE_ACTION` instruction and calls the existing
   `propose_bound_physical_action`, obtaining one
   `ActionLifecycle.PROPOSED`. The Action ID is the stable L0 step-local
   ID; duplicate requests await the same pending action, never recreate it.
4. Exactly the **original** guarded `issue_selected_eat_dev` receives
   that Action proposal; the original WAL/ISSUE/native ACK/food/inventory
   checks and fail-closed behavior remain unchanged. EAT is still a
   single parent compound capability with equip and consume child effects.
5. After that issuer returns, L0 checks the **original ActionSupervisor**
   for `OUTCOME`, advances once, and returns a read-only
   `TERMINAL_CANDIDATE`. The existing SkillExecution remains STARTED,
   and no Intent COMPLETED/learning success is claimed. The CLI reports
   `l0_skill_ir_trace` and `l0_skill_ir_terminal_candidate_only`.
   It does not report logical ActionLifecycle timestamps as measured
   host latency.

Tests use fake typed Mineflayer/LLM transport and cover the full original
physical EAT success composition with the intermediate L0 cursor,
no Target/expired bread (no Action or WAL reservation), equip/consume/after
probe ambiguity (durable PREPARED_UNRESOLVED, restart STOP), legacy issuer
flag combinations and the unchanged legacy positive path. The real #844
controlled `REAL_EAT_PASS` is the **baseline only**: a *real-world run of
this new L0 switch has not occurred*.

No new native issuer, journal owner, operator authentication source, L2
candidate installer, general ATTACK/MOVE/REST support, or persistence of
the L0 cursor was added. Qualification remains
**OFFLINE_DEV / QUAL_NO_GO / SCIENCE_NOT_RUN**.
