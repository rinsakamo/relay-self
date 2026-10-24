# SelfBody S49 live_probe host-clock adapter — isolated offline DEV

**SOURCE_STAGED / LOCAL_PY312_NOT_RUN / OWNER_HOOK_NOT_CONNECTED /
DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Parent: verified passive clock **`5a64df726a9afad995e193ad1092c6c23e270327`**.
Scope: additive `experiments/`, `tests/`, `docs/` files **only**.
No S49, SelfBody, Body/World owner, existing product observer, or workflow
source changes. PR #634/#545/main remain protected.

## Exact original-owner seam

Original `s49_normal_session_real_ci.qualify` receives a correlated native
probe in its existing `reprobe` function then optionally calls
`await live_probe(reading)`. This adapter exposes one matching awaitable
`S49PassiveHostClockDEV.observe(reading)` method but **does not install it**
into S49 or `self_demo`. All tests use **fake-original-S49** callbacks or
synthetic MineflayerObservation fixtures. No World or native session is started.

The adapter first calls the existing `PassiveSelfViews.observe(reading)`
(the source/Body/World admission used in prior product DEV). This method
currently returns `None`, not `SelfBodyView`. Once it has accepted exactly
one new row, the adapter uses the *same received Python object* to perform
pure `project_mineflayer_present` → `project_body_present` →
`compose_self_body_view`, and checks the original passive row's
Self/session/native seq/request/Body source/World source. This repeats a
**pure in-process projection** but never fetches another native observation,
starts a receive loop, sends an observe request or changes World.

The existing `PassiveHostCallbackTimer.enter(view)` is called **after
both projections**. The interval measures only the optional additional
Python observer coroutine (defaults to read-only health/food access), including
any await/scheduling, until `exit(ticket)`. It does not include native probe
transport, decoding, passive admission, projection, S49 L0, Action issuer or
World movement. It is wall-clock duration, not CPU time. Injected clocks
remain labelled `SYNTHETIC_DEV_CLOCK` (never physically attested).

## Ordinary exception vs cancellation — chosen owner policy

Prior `self_demo.observed_source` catches ordinary `Exception` thrown by
`PassiveSelfViews.observe`, records an error and **does not veto** the original
S49 L0. A direct `S49.reprobe` callback exception would otherwise propagate.

This *candidate* retains the existing policy:

- Original passive view admission failure: record failed source, **return**
  on ordinary `Exception`, with no timing sample.
- Typed view/source join failure or clock enter exception: record and **return**
  on ordinary `Exception`, original passive admission remains unaltered.
- Additional observer coroutine failure: `abort(own_ticket)` (no successful
  sample), record failure, then **return** for ordinary `Exception`.
- A failed/reversed clock on `exit`: abort ticket, keep terminal clock
  failure, record error and **return** for ordinary `Exception`.
- `asyncio.CancelledError`, `KeyboardInterrupt`, `SystemExit` and other
  `BaseException`: abort when ticket exists, record interruption, **re-raise**
  without fabricating an OUTCOME. Original S49 cleanup/finally must run.
  An abort failure is recorded separately and must not mask cancellation.
- Rows from existing passive admission are not rewritten on later callback
  failure; **the sidecar summary must show missing timing, failed reason and
  disqualified status** rather than implying a joined success.
- Failures have bounded retained records and a separate overflow counter,
  not an unbounded in-memory logger. Timer attempts, including aborts, retain
  the verified capacity bound.

This adapter may be called by a trusted owner, but it **is not** an issuer,
authority verifier or independent physical source attestor. The optional
observer itself must be owner-reviewed read-only; arbitrary injected Python
code is not an isolated security boundary.

## Tests and next gate

Source-staged offline tests exercise fake S49 passing previously received
native probes; negative examples include duplicate/stale/foreign source,
bad request, native subclass, injected origin, forged/nonasync observers,
capacity, backwards/error clock, aborted callbacks, ordinary non-veto, fatal
cancellation, original fake-owner cleanup, bounded failure ledger and output
claims. They are not a physical World trial.

**These new files have not been tested on WSL2 Python3.12 yet.** Independent
LocalCodex exact-final-HEAD focused tests, Ruff, repository contracts,
Protected82/770/historical-index and adoption v2 (19/15+4), negative history
and after/before SHA are required before an adoption decision. Preserve
initial failures and fix/retest only these additive isolated DEV files.

For future actual owner integration, separately review `self_demo` flag
exclusivity, S49 original `live_probe` invocation, original collector
lifetime and cleanup, sidecar atomic write, errors vs cancellation and
unchanged L0/Action results. No second native reader, `observe` request,
S10 or Memory writer can be introduced. An actual disposable DEV World run
requires its own owner authorization and source-qualified native evidence;
QUALIFICATION and SCIENCE remain separately gated. The true cognition,
Action-to-motor and physical displacement clocks are **not** delivered by
this callback duration.
