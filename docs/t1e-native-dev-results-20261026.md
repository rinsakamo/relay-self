# T1e S49/L0 — local native DEV result, 2026-10-26

**DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
Tested implementation: `7eba8ed4ac247225494ae319087f6a12b8492f01` on
`self/dev-t1e-s49-l0-integration-20261026`, based on the requested
`a6c0c96ed1352dfae8833b063f2d011477e78e77`.
This report is a subsequent documentation commit; executable source is unchanged.
Refs #150, #627, #537. No merge or update to PR #545, PR #634 or main.

## Verification

- Python **3.12.3**: **344 PASS** in focused FAST, including T0–T1e,
  Action/Skill lifecycle, supervision, admission/binding, native protocol/process,
  original execution and adjacent Paper snapshot consumers. FULL not run.
- Node **22.22.2**: **52 PASS**: tick channel, shadow, local deadlines,
  protocol, bridge hooks and V6 native clock. Bridge syntax check PASS.
- Java runtime/compiler **21.0.12.1**, Maven **3.9.11**, Paper API
  **1.21.8-R0.1-SNAPSHOT**: plugin JAR **BUILD SUCCESS**.
- Ruff for changed Python and repository contracts: PASS. These are local
  checks, not an assertion of a new GitHub CI result.

The first Python invocation lacked pytest; a verified existing Python 3.12 venv
was used. The first Maven invocation selected an older compiler; explicit
JDK21 fixed the tool selection. Two failing negative tests were fixture bugs:
modified fields were overwritten before reaching the already strict decoder.
The fix preserves the injected values; the decoder did not need weakening.

## Physical measurement

Five fresh Paper **1.21.8** Worlds, Mineflayer **4.39.0**, loopback only,
configured default **20 TPS**, no TPS actuator. Existing bootstrap libraries
were copied read-only; no existing World was copied, started or modified.
Each test explicitly issues one fixed MOVE_BACKWARD through the existing
operator issuer and S49 physical Executor. This does not establish autonomous
`NormalWorldL0` policy competence or a Full Self product loop.

| Case | Expected Executor result | Node L0 emission → actual clear | Python L0 receipt → clear ACK | Paper-sent / accepted Node tick / emitted shadow | Active shadow ticks |
| --- | --- | ---: | ---: | ---: | ---: |
| Normal MOVE_BACKWARD | EXECUTED; probe displacement 0.626907 m | N/A | N/A | 40 / 39 / 39 | 4 |
| LOW_HEALTH during movement | FAILED: interrupt | 1.358770 ms | 1.121976 ms | 40 / 39 / 39 | 5 |
| KNOWN_NEAR_HOSTILE during movement | FAILED: interrupt | 2.945492 ms | 3.024508 ms | 41 / 40 / 40 | 4 |
| UNKNOWN during movement | FAILED: interrupt | 1.961299 ms | 1.743242 ms | 52 / 51 / 51 | 17 |
| Clear ACK consumer loss after LOW_HEALTH | FAILED; cleanup receipt absent | 1.383734 ms | Not delivered to Executor | 51 / 50 / 50 | 4 |

Normal hold is 0.2 s; hazard fixtures allow up to 1.0 s of held input so the
console stimulus can reach the native client. LOW_HEALTH uses native damage;
near-hostile uses a stationary zombie; UNKNOWN uses 130 marker entities to
exceed the bounded cache scan. These are explicitly staged DEV conditions.

The timing journal uses one **Node monotonic clock** for both shadow emission
(after L0 evaluation) and effect-result emission (after `clearControlStates`).
It measures the existing Python handoff and return path, but omits the small
interval between L0 evaluation completion and shadow emission. Python timing
uses its own clock separately. **JVM and Node epochs are never subtracted**;
absolute Paper-send-to-Node-receive latency remains UNKNOWN. Maximum measured
shadow evaluation was **0.244187 ms**, a bounded cache scan, not a fresh sensor.

Across the short startup-inclusive Paper windows measured effective TPS was
**20.799–21.449**, despite the unchanged 20-TPS target (startup/catch-up timing
is included). This is not a stable-throughput test or high-TPS motor approval.

## Post-clear physical behavior and counters

All five cases sent **one set_control and one clear_controls**, with applied
clear evidence in original Node bytes. In the ACK-loss case only consumer
delivery was dropped; the Executor retained `cleanup_receipt=None` and never
resent the consumed clear ID. Its expected failure is a successful negative
control, not successful Action execution.

After observing the ACK (or the loss timeout), the runner requested a Paper
console snapshot, then examined later server ticks. All cases retained **15**
post-marker pose/input samples. Their last **8 consecutive server ticks** had
all movement inputs false and **0.0 m** pose change:

- Normal and LOW_HEALTH: server ticks **44–51**.
- KNOWN_NEAR_HOSTILE: **45–52**.
- UNKNOWN: **56–63**.
- ACK consumer loss: **54–61**.

There was residual physical movement after clear: marker-to-final pose change
was 0.122879 m normal, 0.058632 m LOW_HEALTH, 0.230263 m hostile and 0.137983 m
UNKNOWN; ACK-loss marker was already stationary. **Clear ACK is not immediate
Paper stop.** The observed later stationary window proves only this bounded
DEV behavior; it does not admit P1-qualified WAIT or prove whole-tick custody.

Total **224 Paper-sent** ticks vs **219 accepted tick/shadow receipts**.
The five unmatched shutdown-tail ticks are **52, 52, 53, 64, 62**, scoped to
their respective separate Worlds. None is credited as L0 success. The
`node_received_ticks` JSON field counts accepted/emitted tick receipts; raw
callback delivery before a budget refusal is not separately instrumented.
All fresh-World-tick attestation flags remain false. Receipt cadence, local
processing budget, missing ticks and native source freshness stay separate.

Missing/duplicate/reordered ticks, local deadline exceedance, post-first-shadow
silence, missing clear ACK and late post-clear hazards are also covered by
focused negative tests. Broken wire timing was tested offline; the physical
runs did not intentionally drop or duplicate Paper TCP messages.

## Repairs and retained attempts

- Reject active shadow discontinuities; a **150 ms** silence watchdog prevents
  one old benign shadow from masking a stopped stream. It is a DEV policy,
  not a certified physiological bound.
- Ignore late hazards for the motor that has already cleared; keep subsequent
  Action checks and the strict protocol intact.
- Add bounded opt-in Paper pose/input samples and a same-Node-clock DEV journal.
- Restrict timing aggregation to the actual dispatch-to-clear interval. An
  earlier hostile report incorrectly selected a startup UNKNOWN even though
  its original consequence correctly showed KNOWN_NEAR_HOSTILE interruption.

`run-001` (one normal World) and `run-002` (four hazard Worlds) remain intact;
`run-002/hostile` remains FAIL with its original raw evidence. The corrected
runner's `run-003` independently executed all five cases on the committed
implementation and all five PASS their stated DEV acceptance conditions.
Ten disposable DEV World executions total; no historical R/V grant was reused.

Every final case has Java/Node return code **0**, PID absence, port **25565**
rebind and original `shutdown_ack`/`connection_end`. All server collectors
finished through the existing shutdown owner.

## Evidence and next stage

Original logs, commands, Node/Python timing, reports and hashes:
`/home/rinsa/work/t1e-integration-evidence-20261026/run-003/`.
Machine-readable measurements and raw-artifact SHA256 values are in
[t1e-native-dev-results-20261026.json](t1e-native-dev-results-20261026.json).
Existing earlier evidence and primary checkout are preserved.

Next: admit genuinely source-bound fresh per-WorldTick observations into L0,
measure queue freshness and deadlines separately, then connect the bounded
DEV behavior to the ongoing S49/product loop and T2 M0/P1 tick accounting.
Adaptive TPS actuation and high-rate Motor remain disabled. Independent
R qualification and V science require their own later decisions and evidence.
