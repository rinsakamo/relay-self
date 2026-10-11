# Self 1.0 — bounded continuous host (S49-owned callbacks, no real World run yet)

Authority: #537; third Golden native S49 success #588; replay viewer #589
exact HEAD `bda89ca2204fff006b6682125f9fc8349407eeed`.
This child adds the **foreground, one-session session-budget controller** in
`adapters/mineflayer/self_continuous_host.py` with a new, append-only
`SELF1_BOUNDED_WORLD_EVENT_V1` JSONL stream for future RelayUI.
This is NOT an unattended daemon, an autonomous L1, nor an executable
Minecraft launcher. **No new physical session is authorized.**

## Runtime division of responsibility

Existing `NormalWorldL0` remains the only native World-based selector.
Existing `NormalSessionActionExecutor.execute` remains the only path that
can issue/propose/authorize a physical S49 Action. Caller must provide:

- the already connected source-owned one-session Mineflayer observation stream,
  with strict `session.started.session_id` matching the existing L0 owner;
- a fresh correlated native `probe(event)`;
- an independent typed `grant(choice, event_seq)` owner, never from L2;
- `on_action(step)` which **delegates** to the existing Action executor and
  returns its original typed `NormalActionReceipt`, not text or arbitrary JSON.

Driver never creates an Action or a grant. It validates native session,
strict fresh entity IDs and source sequence with `NormalWorldL0._check` and
`NormalWorldL0.decide`, then records "requested, not issued" to disk
*before* the external Action callback. Only an original typed
`NormalActionReceipt` with matched source session/ID,
`ActionState.OUTCOME`, `WorldConsequenceStatus.EXECUTED` and actual
positive movement can become `action_outcome`.
Callback exception, timeout or malformed closure records
`action_outcome_unknown` and stops without replay. An output file/write
failure also prevents issuing a new Action.

`SessionBudget` explicitly bounds event count (at most 100), Action
requests, native frame count (at most 10,000), wall-clock time
(at most 600 seconds) and poll interval. The controller responds to
`pause()`, `resume()`, `stop()`, and the explicit budgets, with no
implicit restart, model invocation or reconnect. World owner controls actual
Mineflayer/Java teardown separately. Pausing does not claim backend STOP ACK
or guarantee a physical command already in progress is undone.

Its JSONL event kinds include `session_started`, `world_decision`,
`action_requested_not_yet_issued`, `action_outcome`,
`action_outcome_unknown`, `session_terminal` or `session_failed`.
Each event includes ordered index, source session and typed provenance
tags; measured event/Action fields are taken from existing owners.
The stream is new and exclusive and always closed in the foreground
lifetime. It can later be consumed by RelayUI with an independently scoped
read-only adapter.

## Run only deterministic offline CI for now

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m pytest -q tests/test_self_continuous_host.py
ruff check adapters/mineflayer/self_continuous_host.py tests/test_self_continuous_host.py
```

Synthetic fixtures exercise one far zombie -> WAIT -> distinct near zombie ->
one existing typed S17 Action closure, no repeated Action after budget,
foreign session refusal, false Action closure -> UNKNOWN/no replay,
operator pause/stop and bounded input. This is a **source-shaped offline
contract**, NOT certification of the new controller on real Minecraft.

## Physical continuation (not implemented or authorized here)

After offline tests, a separate future product adaptation must pass an
actual already-owned S49 Mineflayer process and the exact original S49
`NormalSessionActionExecutor` callback into `BoundedSessionDriver.run`.
It should use **new** source-timestamped read-only append-only events,
not the hard-coded S49 zombie-staging coroutine; never create grants from
L2 output, synthetic goal labels or Lane A/B/C toy research.

A separately authorized bounded physical run with explicitly pinned JAR,
GGUF/llama/World and EULA provenance is required before calling the new
driver a genuinely **continuously running Self**. Legacy Golden #588
receipts and the reported 69-file SHA256 index
`57f0f55079943f8a9c714f166213917ca625ab5e143c4102a927fa4de7195fb0`
remain unchanged.
