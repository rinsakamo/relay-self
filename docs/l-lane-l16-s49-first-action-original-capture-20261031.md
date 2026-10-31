# RelaySelf L16 — single S49 Action original-source Goal capture (2026-10-31 JST)

## Intent and boundaries

L15 closed the compatibility gap between the original S49 `set_control(Action-ID)` and S15 `clear_controls(Action-ID-s15-clear)`. L16 implements the *source producer* required by the next prospective physical DEV trial, without creating an Action issuer, learning/Memory/Habit owner, new Mineflayer reader, or qualifying a Goal reward.

The S7 `NativeStreamReceipt` implementation from branch `self/s-lane-s7-native-original-receipts-20261012` is reused **unchanged**. A narrow optional recorder is added to the existing `MineflayerProcessSession` read/write boundary and passed through existing `s34._new_session()`. S49's original normal operation is the default when no L16 opt-in is passed.

The physical S49 session itself already supports two authorized MOVE Actions. For L16, only its **first** terminal S16 Action gets a source-prefix window:

1. Before starting Java/World, the S49 operator provides a fixed spatial target (x,z), tolerance and stability bound; an original JSON plan file is exclusive-written and fsync'd. The plan is **operator-owned, not independently preregistered by an external Goal authority**.
2. A *single* existing Mineflayer subprocess and S7 source recorder capture exact received bytes immediately after `stdout.readline()`, before decoding, and exact sent bytes before `stdin.write()/drain()`. This starts at `adapter_started seq=0`; no reconstructed JSON, second child, or second source owner is used.
3. Existing S49/S15/S16 runs the original `MOVE_BACKWARD`: pre-Action native probe, `set_control` ACK, separately named `clear_controls` ACK, post-Action native probe, terminal S16 OUTCOME.
4. Before the host schedules another Action, the **same existing session** receives two new correlated `observe` probes (distinct request IDs). S7's first-Action prefix is then sealed (SHA, lengths, counts) and detached from the original session. Original S49 can continue later without recording its second Action in the *first-Action* prefix.
5. The read-only `inspect_l16_first_action_prefix()` verifies the complete bounded prefix, session and native sequence, single Action + exact cleanup, effect ACKs, sent command order, terminal request correlation and static pre-World plan. It calculates two position errors against the operator target, with `REACHED` / `NOT_REACHED` / `UNDETERMINED`. A mutable, unstable or incomplete source fails closed. It **does not** create L13 independent external Goal originals or L10 approved training data.
6. On early abort, preserve the S7 bytes and an `INCOMPLETE_NO_GOAL_LABEL` index where possible. Failed captures cannot silently become learning pairs. The source prefix is **not** the full physical session (later S49 work is outside this original recording).

### Explicit DEV World opt-in (not run here)

Requires preexisting fresh canonical absolute physical output root, an authorized standalone disposable S49 DEV World/environment and a distinct operator confirmation. For example, only with an authorized S49 setup:

```bash
PYTHONPATH=src:tests:. S49_REAL_SERVER_CI=1 \
python -m adapters.mineflayer.s49_normal_session_real_ci \
  --report /absolute/output/s49-report.json \
  --server-log /absolute/output/server.log \
  --l16-capture-root /absolute/fresh/physical-root \
  --l16-goal-target-x 0.0 --l16-goal-target-z 0.0 \
  --l16-goal-tolerance-m 0.49 \
  --l16-goal-stability-m 0.05 \
  --l16-confirm L16-S49-FIRST-ACTION-ORIGINAL-DEV
```

The coordinates above are placeholders, **not a valid goal for an arbitrary World**. The S49 real runtime still requires its existing Java 21, Node/Mineflayer, EULA, and permission arrangements. No shared historical S6 permission may be reused. This branch does not trigger any physical World, and CI explicitly has no physical run permission.

### Fresh original files

- `l16_pre_world_goal_plan.json`: immutable local operator plan; does **not** prove independent physical Goal ownership.
- `native_bridge_received_original.jsonl` and `native_bridge_sent_original.jsonl`: existing S7 owner-recorded original bytes for the sealed *first Action* prefix.
- `native_bridge_source_receipt.json`: S7 SHA256, counts and capture-boundary index. This index has no server TCP authenticity, independent intervention proof, or V/R qualification.

### Qualification still missing

The first real DEV capture must subsequently be inspected by separate S/R/V source reviewers, including actual event ordering, authentic pre-Action SelfWorld/SelfBody, an **independent prospective per-Action Goal owner/criterion**, absence of unrelated environmental intervention, and a later current epoch. A string, self-asserted SHA, JSON typed position, stable in-window observation or apparent Goal coordinate is not external reward. No L10 retention or next-epoch L1 advantage is inferred by this module.

Historical G4.13: 11 real executed S16 Actions / 182 Paper ticks; **0** independently labeled per-Action Goals and **0** qualified L10 real pairs. No historical raw source is repaired.

**Classification:** `DEV_ONLY / L16_S49_NATIVE_SOURCE_CAPTURE_OPTIN_IMPLEMENTED / SYNTHETIC_PROCESS_TEST / NEW_WORLD_0 / REAL_GOAL_OWNER_0 / L10_REAL_PAIRS_0 / S10_S11_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
