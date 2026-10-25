# S49 fourth native L0 epoch — isolated DEV actual-World result (2026-10-25)

**Status: DEV_WORLD_ORIGINAL_S49_NEXT_EPOCH_WAIT_AND_MOVE_PASS / DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** Not a merge or source-owner qualification.

Branch: `self/dev-s49-native-next-epoch-20261025`, forked from
`581c1c1ed703a77707fcde3aec24e1380f916a8f` (existing S49→Paper→P1 DEV).
Initial source candidate changed the **protected**
`adapters/mineflayer/s49_normal_session_real_ci.py` blob
`9b624be92258c2d0e15c87474a8f4211b73e8531` into the isolated DEV
candidate `6030098a9f130769c237234f4af482904a3ea0`.
That change is **not** historical original-blob equivalence or R source adoption.
Original `normal_action.py`, P1 model, S14/S16 executors, main, Draft
#545/#634 and historical qualification evidence remain untouched.

## Product-level difference

The default `qualify()` path remains 3 original L0 native decisions with
2 Actions. The **explicit** `dev_next_epoch="WAIT"|"MOVE_AWAY"` gate also
requires `S49_NEXT_EPOCH_DEV_ONLY=1` and rejects Stage R combination. It
extends the **same single original NormalWorldL0 instance** to 4 events,
allowing 2 actions on WAIT or 3 actions on MOVE, while retaining original
`run_session()`, `on_action`, full S14 admission, independent S49
authorization, `NormalSessionActionExecutor.execute()`, S16 terminal and
original cleanup/report finalization. No second receiver, new L0 host or
second Action issuer is installed.

The disposable runner's second original Action callback observes Paper idle
8 tick callbacks and obtains one native post-WAIT probe. It clears the old
zombie by native readback, then stages a **new** zombie, but *does not*
receive its fresh event/probe itself in `--actual-next-epoch` mode. The
original L0 host resumes, receives the new event, correlates its own native
probe, decides and (for MOVE) executes its usual S14/S16 authorization path.
This is deliberately different from earlier read-only DEV shadows.

## Exact runs

- Focused Python 3.12 / syntax / Ruff / negative tests:
  [40175337735](https://github.com/rinsakamo/relay-self/actions/runs/40175337735)
  **SUCCESS**; final correction focused
  [40175637484](https://github.com/rinsakamo/relay-self/actions/runs/40175637484)
  **SUCCESS**.
- Far stimulus **10m**: actual Paper/Java21/Node22
  [40175424468](https://github.com/rinsakamo/relay-self/actions/runs/40175424468)
  **SUCCESS**, source HEAD `149a51562e4d82b3a2e87298b2249430b4dc566f`,
  [original source artifact 12592320105](https://github.com/rinsakamo/relay-self/actions/runs/40175424468/artifacts/12592320105).
  Original decision sequence **WAIT → MOVE_AWAY → MOVE_AWAY → WAIT**,
  2 native MOVE Action outcomes, new Action 0; original same-host decision
  count 4, Action request count 2, Java/Node exit 0.
- Near stimulus **2m**: actual Paper/Java21/Node22
  [40175674198](https://github.com/rinsakamo/relay-self/actions/runs/40175674198)
  **SUCCESS**, source HEAD `d913f5852a29b9fd0b8cebb96f3c2dde3539f0dc`,
  [original source artifact 12591629545](https://github.com/rinsakamo/relay-self/actions/runs/40175674198/artifacts/12591629545).
  Original decision sequence **WAIT → MOVE_AWAY → MOVE_AWAY → MOVE_AWAY**,
  3 original S49 MOVE Action outcomes including the real fourth L0
  action. The workflow checked the final native movement >0.05 block,
  exact event/probe/action join, typed native execution evidence,
  S16 closure and Java/Node exit 0.

## Limits, protected evidence and next step

- The existing P1 model computes an **uncalibrated hypothesis** from the
  **second original MOVE**, Paper post-clear WAIT and one native probe;
  the model is not native fatigue telemetry. In the near run, the **third**
  MOVE occurs later. Its fresh P1 fatigue debit is **not** yet modeled,
  credited or carried to another Self epoch.
- The original L0 choice remains S42/native-geometry based; P1 did not
  cause the fourth WAIT/MOVE choice or serve as its S14/S16 authorization.
  Same-epoch P1/SelfBody is preserved as an explicitly fallible read-only
  hypothesis. Real paper/native full-tick equivalence is not attested.
- `SourceBoundTick(WAIT)` is absent; R-qualified admitted WAIT ticks =0,
  R P1 recovery =0, no S10 update, no V science, no LLM/GPU claims.
- **This source-modified candidate requires owner review before any adoption
  into Draft #634/#545 or main.** Do not loosen the historic protected SHA
  guards or relabel these DEV executions as R qualification.
- Next DEV milestone: close the **third** MOVE into a new post-action
  SelfBody/SelfWorld epoch, debit P1 from its new observed distance, and
  hand it to a subsequent bounded original L0 epoch. Keep a single native
  receiver/issuer, original authorization and explicit DEV controls.
