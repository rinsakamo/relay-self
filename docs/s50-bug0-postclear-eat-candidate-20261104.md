# S50 → Bug-0 EAT — one Paper-original tick/input join (2026-11-04)

> **STATUS: OFFLINE S-OWNER READBACK / NO PHYSICAL STOP OR EAT AUTHORITY.** Parent [S50 #627](https://github.com/rinsakamo/relay-self/issues/627), S50 input witness [Draft #642](https://github.com/rinsakamo/relay-self/pull/642), original physical Bug-0 join [Draft #719](https://github.com/rinsakamo/relay-self/pull/719), unified architecture [#717](https://github.com/rinsakamo/relay-self/issues/717).

## The actual missing join, not a missing motion/wait implementation

Existing S50 owner already has:
- [`s50_p1_wait.py`](../adapters/mineflayer/m02_paper_dev/s50_p1_wait.py) to parse one source-bounded `S50_DEV_WAIT_BEGIN` and exactly eight contiguous `S50_DEV_WAIT_TICK` callbacks. The rows include native pose, cumulative motion packet/distance counters, combat/swing counters, and basal ticks. The reader identifies **sampled** activity and *never* grants P1 recovery.
- [`s50_input_witness_source.py`](../adapters/mineflayer/m02_paper_dev/s50_input_witness_source.py) to parse eight contiguous `S50_DEV_INPUT_TICK` callbacks with seven last-reported input flags and bounded `PlayerInputEvent` counters. It reports `effective_client_clear_tick=NOT_ATTESTED`, since callbacks do not prove all packets over the entire tick.
- [`s50_client_packet_source.py`](../adapters/mineflayer/m02_paper_dev/s50_client_packet_source.py) for *one client.write path only*. A write-return is not server reception, a cross-clock tick, or server-effective clear.
- Paper DEV [#642](https://github.com/rinsakamo/relay-self/pull/642) and integrated client-write [#643](https://github.com/rinsakamo/relay-self/pull/643) observed post-clear displacement even while all seven last-reported input flags were OFF. That is a real observation of **inertia**, not a STOP certificate.

**New only:** `s50_bug0_postclear_eat_candidate.py` invokes the **two existing unmodified S50 readers** against the **same bounded Paper stdout original bytes**. It checks matching marker, World, exactly eight co-ticked samples, terminal `outcome`, and the existing negative admission flags. It returns an immutable diagnostic view with the Paper-original SHA256 and separate sampled input-active/body-active tick lists:

- `SAMPLED_QUIET_INPUT_OFF_DEV_CANDIDATE_ONLY`: eight Paper tick callbacks look quiet, seven input flags were OFF, no observed PlayerInputEvent. The result is **not** a server-effective clear, complete activity census, or any EAT/P1/Goal grant.
- `SAMPLED_ACTIVITY_OR_INPUT_CHANGE_NO_WAIT`: at least one sampled motor/combat/pose change or input-ON/update was observed; this cannot be called a quiet WAIT candidate.
- Corrupted source (missing/duplicate tick, wrong World/marker/subject, altered coverage, forged effective clear, source too large or invalid terminal) rejects, rather than silently aligning adjacent unrelated streams.

**Never emitted by this module:** `physically_stopped_proven=true`, `eat_action_authorized=true`, `p1_wait_ticks_admitted>0`, authenticated principal, independent qualification, training evidence, or a “post-MOVE resume” token. The S49 owner retains `_post_move_settling_unqualified=True`. This result is **read-only and cannot release that fence**.

## Archived genuine World original replay (no new World)

The 2026-10-31 S50 #642 **already saved genuine Paper console** at `docs/evidence/s50-input-20261031/run2/server.log` is now read by the same source join in a new regression case. Original SHA256 is pinned and verified against the existing `SHA256SUMS` manifest: `0e1fc41d0c64ed871506e59252556f01320f3ac53e1b4d9239312a26dd3f1f05`.

Actual source marker `s49-native-move-19-3e63cfbc-1011-4dd1-b1ca-f3a6f596f5bf`, World `6993349a-b2c3-433f-b2c8-7f32b5fe64c8`, subject UUID `dcae346d-e66f-331a-b459-a5a5370e9738`, WAIT begin tick 251. The join reports **`ACTIVITY_OBSERVED` at ticks 252, 253, 254**, while `sampled_input_active_ticks=()`, `input_event_count_final=0`, `effective_s15_clear_tick=NOT_ATTESTED`, `physically_stopped_proven=false`, and `eat_action_authorized=false`.

This is a **regression on historical genuine DEV observations**, not a new live experiment, full packet witness, independent STOP proof or R source authentication. It demonstrates why input-OFF alone cannot unlock EAT and why the single-source motion rows matter.

## Existing user-approved DEV versus R/SCIENCE policy

[Issue #627](https://github.com/rinsakamo/relay-self/issues/627) explicitly relaxes *research qualification* requirements for S-owned disposable DEV physical experiments, but still requires the original S49 sole issuer, owner permissions and cleanup. This read-only S50 candidate is **not a new physical trial**, permission, or R-grade source. For a future DEV EAT attempt, the S owner may predeclare a bounded behavior-specific physical safety envelope and collect authentic input-release/motion evidence; formal cross-clock tick attestation remains independently reviewable by R. **DEV feasibility and R qualification must not be conflated.**

## Tests and effect budget

- New source-join tests reuse the **existing S50 WAIT and input test fixtures**, not a copied Paper log parser. Positive fixture checks co-ticked eight rows and zero authority. Negative fixtures include input ON, input event, sprint activity, corrupt/foreign source, duplicate/gapped row, counterfeit effective-clear label, and missing original terminal.
- Exact child branch: `dev/s50-bug0-postclear-eat-candidate-20261104` atop S50 [#642](https://github.com/rinsakamo/relay-self/pull/642) `33275fc5221fd18bbdc47b167fc0a83fe7cf8ad4`.
- Latest offline CI: [#41729904168](https://github.com/rinsakamo/relay-self/actions/runs/41729904168), Python 3.12, repository contract + compileall + Ruff **PASS**, **68/68 pytest PASS** (existing S50 readers, new join and original S50 Paper evidence replay).
- **World=0, S49 Action=0, additional Paper/Node=0, Gemma=0, P1 recovery writes=0, M energy=0, L memory/learning=0, retry=0** in this code-only iteration. Main, existing S50 #642, S49 #674 and Bug-0 #719 branches are unchanged.

## Next owner-owned physical proof boundary

1. S50 owner pre-registers what DEV-only physical pause sufficient for first **non-moving** EAT means; do **not** demand generic full self-driving STOP certification for Bug-0.
2. Actual post-MOVE release on a fresh source requires distinguishable native `clear_controls` delivery/callback effects, genuine per-tick movement and no ongoing motor input during a bounded window. The old samples currently cannot certify server-effective S15 clear.
3. S49 owner must independently issue a fresh EAT-specific PROPOSE/ISSUE grant, check two native food/threat observations, physical occupation and source generation at actual ISSUE, preserving unique Action IDs and one original issuer; neither this S50 readback nor an L2 narrative may grant EAT.
4. After native equip→consume, reuse S51 original food+inventory outcome. Rejection/timeout -> UNKNOWN, no free energy credit, retry, learning or falsely inferred nutrition.
5. Keep S-owned DEV World result separate from source R qualification and V science. Preserve SHA/source/JAR/Paper/world cleanup originals and both successful/failed trials.

**Verdict:** S50 already has both source readers. The newly added piece is exactly their bounded original-compatible *join*. `DEV_OFFLINE_SOURCE_JOIN_PASS / EFFECTIVE_CLEAR_NOT_ATTESTED / PHYSICAL_STOP_UNPROVEN / EAT_AUTHORITY_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
