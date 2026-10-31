# S49 × SelfBody × L8 × M passive DEV integration

Integration base: M `df6c820b6a7978edf6b82a867bd2f93ba250f039`,
S `087fe095a87594505392262da1d341cf0c65b2b2`,
L8 `4defb6e8b78f2e050921b521eb2253a14bc260c4`.
S is merged on the isolated integration branch. Only eight added L-owned
modules and their eight tests are copied unchanged from L8; its alternative
bridge/S49 changes are excluded. Main and original branches are unchanged.

`qualify(slm_dev_owner=S49SLMDevOwner())` explicitly binds the existing host
and existing Executor supervisor. Default is off; concurrent Stage R or an
independent live_probe is rejected. No Executor, S14/S16, Motor, native reader,
STOP or interrupt implementation is replaced.

The existing pre-choice live_probe captures the exact probe into a bounded
lease. The decisive original `NormalWorldL0._check` selection runs once inside
the existing S42 coordinator, using the existing Executor supervisor's logical
ordering index (not elapsed time). The preliminary grant check remains as it
was. The returned choice is the exact object used by the original L0Step.
No DecisionEpochResult is reconstructed from a label or recomputed decision.
Three completed epochs at most retain their original native/retained/epoch
references; passive capture failures preserve the original choice.

After the native loop unwinds **and existing cleanup finishes**, the explicit
DEV owner makes its sole B0 ledger's decisions on the saved probes and invokes
`S49PassiveSourceLease.observe_after_original_s_epoch`, which reuses
`observe_optional_s_l_m_dev`. Ordinary S49 has no B0 ledger; this is the sole
explicit B0 model owner for this opt-in, not a duplicate physiological ledger.
No B0 step, recovery, credit, food or Minecraft body accounting is performed.
SelfBody composition uses the original B0 projection inside the M tap.

L8 receives an actual `advance_learning_epoch` result with an empty Memory,
no training episodes or Goal labels and retention OFF. It must report
`retention_off`; no learned benefit, Habit, policy change or physical Goal
success is implied. Probe SHA256 covers the decoded object only and is marked
as such; raw native stdout is captured separately by original S49 custody.
Epoch/session/probe/request IDs, the S choice, model tension and original
Action outcome rows are joined in `report.json.slm_dev`. WAIT has no issued
Action; an absent outcome is never filled with success.

Run only with a fresh per-run grant and absolute unused output directory:

```bash
PYTHONPATH=src:tests:. python -m adapters.mineflayer.slm_passive_dev_run \
  --output-dir /absolute/fresh/run \
  --confirm S49-SLM-ONE-DISPOSABLE-DEV-WORLD
```

The runner starts the pinned original S49 disposable Mojang Java 1.21.8 host,
not Paper. It uses the original WAIT / two MOVE_AWAY scenario and zero LLMs.
Paper WorldTick/M0/P1 integration, retained L1 candidate learning, independent
source qualification and scientific benefit remain unverified. DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. Coordinator/capture add bounded work;
zero scheduling overhead is not claimed. All expensive diagnostics occur after
Action and cleanup and cannot issue, interrupt or wait on an Action.

Original first failure: an unsorted L8 feature pair was rejected; retained in
external `owner-first.log`. Repaired to the original L8 lexicographic contract.
A mistaken regression filename produced a collection error, retained separately;
the corrected S49 owner/cleanup/startup/regression suite is the authoritative run.
