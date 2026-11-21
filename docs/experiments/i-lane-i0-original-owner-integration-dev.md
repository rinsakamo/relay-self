# I Lane I0 — original-owner integration baseline (DEV)

Tracking: #1061. Authority: #828 §27, #1047, #1054, #951, #839, #966.

## Pinned sources and role
I0 is an isolated B-anchored branch. Initial B #1050 HEAD `7c49070f04e8a9e06267858be828c692dee6384e` (B #1027 model-audited baseline `a552e7b5592053e125071be5ea8903ddeb1aadbb`).

| Source | HEAD reviewed | Integration status |
| --- | --- | --- |
| A #1059 5m MOVE | `666a5dc4331cabe935d7555d9a36940c2330323b` | real flat-world MOVE, no generic route CLEAR |
| C #1060 evaluation | `914c4f92fbdfa42b816d9c392a5ceefa5afe8157` | synthetic B PASS; A/C HOLD |
| D #1043 exploration | `0eb3dc88b5cfa6326b3666642c95077c178a35c6` | D11 real trial held before L1 POST |
| E #1053 SENSE | `b3524a6a37b711747b07b962d29a762dfdaccc36` | composite source adapter; E2c HOLD |

Review fresh exact HEAD before importing changes. B/E diverge from merge base `6f8defd7b74b38c2758998ed61b97898477deb98`, with conflicts in bridge, persistent cognition, native adapter and owner runtime. D and A also diverge. Do **not** blindly merge/copy older owner/bridge modules.

## Canonical ownership
- B: original `CheckpointedCognitiveOwner` and `ResidentCognitiveWorkOwner`, `ResidentLlamaInferenceLane`, Paper/native source qualification, World+A/B checkpoint and WAL.
- E: read-only native SENSE projection, separate immutable `mineflayer:<session>:<seq>` revision. Cannot authorize motion, upgrade to Paper proof, or create a second source owner.
- D: Question/Need and L2 attempt proposals; mutation only by B original owner.
- A: original CPU L0 control, STOP/settled WAL, sole physical issuer.
- C: source-qualified Intent→C1 and L1 evaluation proposals. B alone adopts approved Memory, not an autonomous learning DB.

## Implemented I0 slice
`read_i0_owner_cpu` yields a **read-only ephemeral** pair of B's current CPU Present and optional `CoverageInquiryProposal` at the same qualified Native/Paper revision. It acquires B's resident lock, calls B's existing `read_present_cpu` and `build_coverage_inquiry`, then reprojects and requires identical source/result before return. It never accepts an externally forged Present, adopts a Question, calls a model, writes Memory, schedules another CPU loop, or permits physical Actions. Consumers must revalidate this snapshot at later admission time.

I0 tests reuse B's *synthetic* actual Owner/Resident/Bridge fixtures: A/B isolation and unchanged files, absent Need, source mutation during inquiry, forged inquiry, stale World epoch, fenced Owner. This alone is not real Paper/Gemma or E2c certification.

## I1 next bounded diff (not implemented in I0)
1. Review/port E's existing original ProcessSession receiving and `sense_for_composite_source`, **without** replacing B's owner or Paper/native verification.
2. While holding B resident lock or taking an equivalent atomic versioned snapshot, correlate `current_sense` to B's exact Self, native session, World/branch/epoch and Paper session. Recheck passive SENSE revision before returning. Its provenance remains Native.
3. Build `ThreeSelfProjection` and `PresentFrame` with exact composite `(native, paper, mineflayer)` revision; missing SENSE retains B current behavior, with UNKNOWN for absent terrain/negative coverage, never CLEAR.
4. Connect normal original event/decision epoch to existing `cpu_schema_epoch` then `assemble_l1_select`, preserving CPU-only bounded Schema, optional Need/Goal/Constraint, one L1 selection and existing GPU owner. No per-tick GPU requirement or invented target catalog.
5. Adversarial integration: two Selves, stale/foreign session, Paper receipt change, passive update mid-projection, logout/reJOIN, unknown AABB/collision, missing Action catalog, forged negative entity coverage, unrelated observation vs selected Target validity, owner/memory/Action WAL mutation absent.

## Next gates
I2 original-owner D Question ADOPT/L2 reservation and typed reJOIN; I3 source-bound bounded real Gemma L1→original Intent/SkillRun→A L0/ActionPort/settled WAL; I4 C1/C2 evaluation and next-epoch Memory reuse; I5 consistent World+A/B restore and separate 60s autosave proof; I6 L2 hypothesis→bounded CPU validator→Self accepted versioned learned pattern. Issue #1061 is the work ledger.

## Validation and claims
Offline test+exact final HEAD CI are required for I0. Full relevant repo regressions, Ruff, Node/Mineflayer and Paper where available. A CI green is not a real World, model, L2 or qualification proof. For real DEV LocalCodex owns and starts shared WSL llama-server with measured PID/GGUF/GPU/single slot; isolated World DEV and EULA consent are already approved. No physical World or GPU execution occurs in this I0 slice. No main merge until owner review, integration tests and appropriately scoped real independent audit.

## I1 partial CPU seam (new; E2c still HOLD)
`prepare_i1_cpu_schema_probe` consumes **only** an I0 requalified, original B-held Native observation under the same resident lock. It creates a bounded `WorldPercept` from available native body food/oxygen and an explicitly source-recognized possible zombie cue, plus the B Present-qualified exploration Need. It invokes the **existing** `cpu_schema_epoch` and `assemble_l1_select` without a GPU POST. No verified Action catalog or Target binder is currently integrated, so `allowed_skills=frozenset()` and `targets=()` guarantee that the finite L1 proposal has only cognitive ESCALATE_L2/DEFER options. A readback checks that the original Owner/Source did not change during CPU Schema work; no writes or Actions are issued. Partial scope does not claim that absent native entities means an empty World, or that unbound observed entities are actionable Targets.

Tests use B's original synthetic Bridge/Owner/Native fixture: A/B independent CPU Goal candidates, no executable Skill/Target, no Need fabrication, changed observation during Schema computation, stale World and owner fence, and non-rounded native food. CPU Schema and Present are *on-demand* in these tests; normal event-loop scheduling, E passive SENSE→B Present integration, verified Action catalog, full 3Self RECENT, real L1/World/physical effects and I1 PASS remain HOLD.

## I1 E2c original Native → B Present integration (CPU/offline; real World HOLD)

Reviewed E #1053 `b3524a6a37b711747b07b962d29a762dfdaccc36` against I B base, rather than wholesale branch merging. E's original process-session single-decoder/dispatcher and **native-only** SENSE fanout are ported, without E's unqualified terrain request code. B's own `forbidden_native_sessions`, original first Native probe, owner and GPU attachment, native/Paper source checks, and *patched* self-oxygen source remain intact; E's older bridge file could not safely replace them.

With explicit `enable_sense=True` and B cognitive resident present, the original bridge subscribes to passive Native stream **after verified login**. Passive SENSE and Present reads share B's resident RLock; updates cannot interleave a B projection inside that lock. The existing ProcessSession remains the **single Native JSONL decoder** and retains normal owner messages/ACK through its bounded queue. Default remains disabled to preserve existing Stage28 behavior until its caller opts in.

`build_bd1b_owner_present` now uses **B original Native/Paper qualification first**, then an optional fresh SENSE from that same original session and scope. In SENSE mode it composes the immutable revision tuple `(native, paper, mineflayer:<session>:<seq>)`, retains E claims as **native** provenance, does not attribute them to Paper and rechecks the current SENSE identity after Present/Need projection. Missing SENSE keeps original two-source B projection. The existing coverage inquiry still uses the unique original B bounded Native coverage claim, not the new E observed-registry summary. It is not an Action/Target catalog or World coverage negative proof. `prepare_i1_cpu_schema_probe` can use the exact same-revision E Native body snapshot for food/oxygen and possible entity cue; no Skill/Target action authorization is granted, so bounded L1 request remains ESCALATE_L2 or DEFER.

Synthetic original B Owner/Resident/Bridge tests exercise the same actual Python ProcessSession JSONL decoder with a generated Native event stream (spawn/probe/move/effect ACK), original B source qualification → composite Present → B coverage inquiry, Next Native revision, read-only files, A/B independence, mismatched scope/revision, SENSE revision change during Present, updated current food for CPU Schema, old World epoch and fenced owner. These are NOT real Mineflayer, Paper or Gemma observations.

**Remaining HOLD**: link the optional SENSE enable flag into the actual normal Stage28 start/reJOIN runner and demonstrate automatic CPU Present consumption; original Paper current receipt refresh during real World movement; fully exercised causal Native/Paper SENSE single-stream audit; Body AABB, collision/route clearance and finite source-age across native buffering; GPU L1 and physical motor integration; autonomous Question ADOPT and cognitive Checkpoint restore. The original CPU readout still needs explicit caller invocation. The E2c end-to-end normal runtime/real World gate and overall I1 Gate remain HOLD until verified. The classification for this slice must be narrow: `I1_E2C_COMPOSITE_CPU_OFFLINE_PARTIAL`, never `REAL_E2C_PASS` or `DEV_INTEGRATED_CLOSED_LOOP_PASS`.
