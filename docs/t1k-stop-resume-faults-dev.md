# RelaySelf T1k — bounded two STOP/Resume cycles and restart-fault DEV injections

Source: `self/dev-t1j-explicit-resume-20261027` at
`8b02e27bf9ec11a10077b39e41bfa850c52a5f9d`.

**DEV_ONLY / OFFLINE_IMPL_ADDED / T1K_NATIVE_UNVERIFIED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
Prior **T1j** successful 2/2 disposable Worlds remain independently
`DEV_WORLD_OBSERVED`, not a claim for this new T1k code.

## Bounded multi-generation implementation

The existing T1f multi-epoch loop, original S49 ActionSupervisor/Executor,
Mineflayer **single native receiver and Motor writer**, real EAT once,
T1h high-level **scoped DEV** STOP ACK, T1j explicit Paper→native→Paper
gate and T2 M0/P1 accounting are retained.

One isolated `t1k_stop_resume_twice` case attempts:

1. two normal MOVE OUTCOMEs → genuine EAT OUTCOME/credit once;
2. third MOVE stops through original S49 clear ACK and Paper 8 consecutive
   idle transitions → first limited DEV STOP ACK; old STOP owner remains latched;
3. **separate** T1j R1 explicit grant + Paper→native→Paper → first resumed
   MOVE, interrupted by second explicit STOP request → original S49
   `clear_controls` exactly once → independent Paper marker and scoped
   **second** DEV STOP ACK using a distinct `T1K_R1_AFTER_CLEAR` Paper marker (never reuse `T1I_MULTI_AFTER_CLEAR`); first and second STOP owner remain latched;
4. **another separate** R2 explicit grant + fresh Paper→native→Paper
   → second resumed MOVE OUTCOME and post-clear idle; neither UNKNOWN
   interrupted MOVE is retroactively promoted to OUTCOME.

The native session keeps a permanent set of *all sent* resume Motor Action
IDs instead of resetting the T1j boolean. The `T1kStopResumeLineage`
requires two distinct STOP IDs, two distinct one-time permits, fresh owners
and exact generation sequence. It rejects same-owner/replayed-ID and
foreign-session STOP. Only the bounded R1→STOP2→R2 chain is implemented;
no general unbounded resume API is implied.

`t1j_resume_native_dev` stores **separate** frozen M0/P1 ledgers under
`t1k_old_ledgers[T1J-R1|T1J-R2]`; the previous segment remains frozen.
Each rebase carries last known *virtual* M0/P1 values and already booked EAT
credit IDs, starts after a newly admitted Paper tick, and explicitly
records missing unobserved WorldTicks. **No retroactive metabolism,
displacement, P1 WAIT recovery or EAT credit**. World metabolism does not
actually stop during the missing interval.

This multi-generation case is explicitly granted only with BOTH CLI
operator tokens, in addition to ordinary disposable-DEV World permission:

```sh
PYTHONPATH=src:tests python3.12 -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1K-MULTI-RUN \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/BUILT/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --t1j-reauthorize T1J-DEV-EXPLICIT-REAUTHORIZE-ONCE \
  --t1k-second-reauthorize T1K-DEV-EXPLICIT-SECOND-REAUTHORIZE-ONCE \
  --loop-moves 2 --cases t1k_stop_resume_twice
```

LocalCodex must verify the exact argparse contract and native assets
before using this command. It must never run on any previously used World.

## Three native fault cases (all expected to refuse, NOT clean PASS)

The T1j-like R1 protocol can be faulted in fresh individual disposable
Worlds by replacing only the case name (omit the second-generation token,
**retain** the separate T1j first-grant operator token):

- `t1k_fault_before_send`: after consumed explicit R1 permit but **before
  resumed Motor write**, inject actual Minecraft `kick`; zero new Motor
  sends required. Prior three MOVE set_control are not new resumed actions.
- `t1k_fault_set_ack`: after sending new R1 Motor effect once, inject a
  real Minecraft disconnect. Expected no second set_control, no forged
  OUTCOME/STOP ACK, fail-closed source and cleanup metadata preserved.
- `t1k_fault_clear_ack`: drop R1 `clear_controls` ACK **only at Python
  consumer** while retaining original Node JSONL bytes. Expect timeout/
  UNKNOWN/failed run, no repeated clear or resumed MOVE, no additional
  generation.

A fault-injected run may have `report.status=FAIL`, Node exit3 or no
normal `shutdown_ack`. **Do not turn abnormal transport shutdown into
normal-case PASS** merely because refusal was expected. The
`t1k_fault_audit` separately reports Motor send count, duplicate IDs,
source/cleanup and whether there was any safety violation. Keep the full
raw journal and exact failure category.

## Required verification sequence

1. Check isolated branch, expected HEAD, Python3.12, Node22, JDK21,
   existing Paper1.21.8 plugin/bootstrap. Confirm untouched
   main/#545/#634/R/V/S18 and prior World originals.
2. Python 3.12 focused tests:
   `tests/test_t1k_resume_lineage_dev.py`,
   `tests/test_t1k_segment_lineage_dev.py`, T1j
   `tests/test_t1j_resume_gate_dev.py`,
   `tests/test_t1j_resume_accounting_dev.py`,
   `tests/test_t1j_native_rebase_dev.py`, and T1i/T1h/T1f related.
   Repair test/code failures while retaining fail-closed guards.
   After module completion FAST; FULL only if main merge, not here.
3. One or two clean multi STOP/Resume Worlds. Verify same native session,
   two distinct permit IDs/STOP ACKs, old owner latch retained,
   genuine single EAT receipt/credit, 5 expected set_control and
   clear_controls operations with `--loop-moves 2`, exactly one
   final MOVE OUTCOME. Save all original paper/native source and
   separate frozen M0/P1 segments. No replayed ACK or unknown-gap credit.
4. Individual fault Worlds as needed: first pre-send, then set/clear
   ACK boundaries. Preserve refused raw World/Node/Java and audit
   whether shutdown/connection_end/exit/PID/port-rebind succeeded
   separately. Do not treat malformed source or source loss as qualified
   STOP or P1 WAIT.
5. Only after completing the bounded T1k stability and fault checks,
   plan a longer continuous source/ledger DEV soak in an independently
   scoped task. This commit does not claim multi-minute stability.

### Verification actually completed with ChatGPT tools

Branch/source publication through GitHub and read-back, source contract
review and isolated DEV test authoring. **New T1k tests have NOT been
executed in the user's Python3.12/WSL2 runtime here. No fresh T1k
Minecraft World, full Node/Java or FAST run has been performed.**
Classification therefore stays `T1K_NATIVE_UNVERIFIED`.

The intended positive result is *two STOP/Resume generations under S49
ownership*, not proof of R-qualified STOP, every-subtick stillness,
authenticated source or scientifically general agent autonomy.
