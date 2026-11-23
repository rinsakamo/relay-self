# B-NP1b-2e — Original Resident normal CPU Present scheduler (DEV)

Extends #1097: normal CPU Present/Inquiry refresh is no longer only a
manually invoked poll. The original `OwnedResidentPhysicalBridge` starts
**two coroutine tasks owned by the existing `ResidentCognitiveWorkOwner`**,
one task per Self. These are read-only, strictly scoped periodic polls:
no second cognitive Owner, new physical issuer, GPU ticket, MessagePort,
ActionPort, Learning/Memory commit, L1/L2 or synthetic World clock.

## Runtime sequence

1. Complete A original logout/reJOIN, B continuous Native and owned Paper
   post-reJOIN PRESENT + main-thread ACK; register original per-Self Schema.
2. Bind immutable *history* once with
   `bridge.bind_normal_rejoin_present_cpu(initial_receipts=...,
   historical_composite=...)`. As previously, this does not cache current
   authority. Any invalid Native/Paper/Owner source yields HOLD.
3. While the original asyncio loop is running call
   `scheduler = bridge.start_normal_present_cpu_schedule(interval_s=0.05)`.
   The interval is restricted to 0.01–30 seconds, and there may be only
   one scheduler on the original resident for these two Selves. No task
   can be scheduled without an already-qualified A/B Present source.
4. The original Owner registers a task for A and B with `start_cpu_task`
   and epoch-bound `ResidentWorkToken`; the existing `state.tasks`
   remains the canonical task ownership ledger. Each task polls through
   `bridge.poll_normal_present_cpu()` under the existing resident lock.
   It stores only an immutable in-memory `ScheduledPresentCpu` tagged
   with source pair revision and per-Self token/iteration.
5. Call `bridge.require_scheduled_present_cpu("A" / "B")` to read an
   observation. It checks the original Self epoch, task identity/active
   state and **re-runs the whole current A/B source qualification**
   before returning. An older cached poll is NOT an adoption credential.
   `scheduler.status(sid)` exposes diagnostics only: PENDING, CURRENT,
   HOLD or STOPPED, with iteration count.
6. B can acquire new same-session Native observation through the existing
   `update_fresh_native(bridge=..., self_id="B",
   initial_receipt=initial_receipts[1])`. While this operation holds
   the original receiver claim, polls can HOLD. Once adopted and
   independently requalified, the periodic CPU task publishes new
   source-pair and Present/Inquiry revisions without re-binding history.
7. Original `bridge.quarantine`/ `logout` fence the respective Owner
   epoch synchronously before any wait. `ResidentCognitiveWorkOwner.
   retire_self` cancels and awaits its registered CPU task, maintaining
   the original retirement receipt. The remaining Self may remain ONLINE,
   but no old pair result can be served if either Self is absent or
   the full Native/Paper/Schema cut is no longer qualified.

`await scheduler.stop()` is an explicit DEV halt (tasks are cancelled and
results cleared); it retains the original Owner task ledger for later
retirement auditing, and cannot be restarted in that same unretired epoch.

## Trust boundaries

- This is a genuine periodic coroutine runtime using the **original CPU
  task owner**, but it is an **opt-in DEV entrypoint**. It is not yet wired
  into the production default startup or continuous multi-reJOIN World
  service. No promises of real-time scheduling / physics rates.
- Tasks access the original Bridge's current projection only; all source
  authority is recomputed, never inferred from the cached sample or an
  independently supplied hash.
- Even a CURRENT diagnostic is not source authority: only
  `require_scheduled_present_cpu` can return a revalidated result.
- An invalid B Native update, Paper log growth without newer ACK, Owner
  swap, schema loss, epoch fence or process retirement invalidates
  readout immediately. The in-memory worker can mark HOLD while remaining
  CPU task stays available for later independently qualified observation.
- Native and Paper clocks remain independent; no simultaneously sampled
  cross-clock cut or physical Action is claimed.

## Evidence boundary

Focused adversarial and full pytest exercise original Bridge logout and
Owner retirement, per-Self task ownership, async periodic refresh,
readback vs stale cache, independent B Native update, Paper source HOLD
and recovery, epoch/owner/Schema/decoder faults, and unauthorized starts.
Both original Mineflayer decoder and synthetic owned Paper subprocess
remain in use. No actual Minecraft World, GPU or real inference executed.

**Remaining HOLD:** default runtime/production startup wiring, automatic
multi-reJOIN task rearm, independently audited real Paper/Gemma,
restored Schema authentication, E2c SenseFrame, L1/L2, Question ADOPT,
Physical Action, QUAL and SCIENCE. Parent Issue #1047, stacked PR #1097.
