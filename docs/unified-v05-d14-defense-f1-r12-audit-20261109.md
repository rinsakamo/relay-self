# R12 original W3: Defense-F1 source-only diagnosis

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. No World or action was run.
The base is Defense-F1 #823 `a1abbd148db08c021c46b44343255689d4d85b7d`.
The R12 World was `a7fec96a-7d56-493c-8b34-7620b736dbb8`, session
`4e7c41f5-a293-4162-aa25-da9f7df42e3f`. The sealed W3 SHA256, measured
from the original, is `a13f85fcb518cdbfa07388024fc15777ab28472671cf83f93c4e9236fc919a52`.
Receipt is COMPLETE_NODE_STDOUT, 354 consecutive frames 0–353; death is seq 302.
The original manifest verified 16/16 and all 18 original files including the
manifest were separately hashed before and after analysis without change.

Of 18 paired decisions, R9 and F1 source candidates are both zero. Within
pairs health fell in 3 decisions (4, 14, 17); comparing consecutive fresh
probes shows 8 decreases. Counts overlap: total registry entity count is not
exactly one in all 18, oxygen is unknown in 6, no recent health-loss witness
in 10, zombie range fails in 2, and one pair lacks a visible zombie in both
probes. No pair exceeds the F1 movement limits, has an ID change when both
zombies are present, or has truncated coverage. Counts are diagnostic, not
independent authorizations. Registry contains sheep as well as zombie 48:
the existing rule requires exactly one *total* entity, not one zombie among
other entities. Altering this constraint requires a separate safety analysis.

Paper recorded attacks at ticks 63, 92, 118, 151, 180, 200, 220, 240,
260 from UUID `948fec9e-af35-43a1-a03d-19340b1020d0`. Gaps are 29, 26,
33, 29, 20, 20, 20, 20 ticks. Health 20→17 in decision 4, 8.333→5.333
in 14, and 3.333→0.333 in 17 are consistent with Paper's damage records;
native integer entity ID to Paper UUID and cross-stream timing are not
independently attested. Causal assignment remains NOT_ATTESTED. Paper's
post-tick 261 health 20 is post-death/respawn and does not undo death.

Original S49 issued no ATTACK/MOVE/EAT. Because no F1 candidate exists,
its counterfactual PROPOSE/ISSUE decision was not exercised and cannot be
claimed as approved; grant, budget, persistent PREPARE, S16 and STOP still
apply. No physical counterfactual action or survival is established.

Mineflayer 4.39.0's installed `breath.js`/`entities.js` assigns oxygenLevel
from received entity metadata; protocol.mjs serializes an undefined value as
null. Absence of a metadata value does not prove normal air, so UNKNOWN is
preserved. W3 has no per-probe wall-clock timestamps, so pair latency cannot
be measured from these records; the Paper tick gaps do not establish it.
A future passive timestamped probe study could measure latency, without adding
an issuer or relaxing S49. No World authorization is supplied here.

The replay writes only a new external derivative and adds overlapping
read-only diagnostics. Candidate computation and physical admission are
unchanged. Diagnostic counts use the two existing possible witnesses and do
not imply that all other F1 predicates or S49 gates are satisfied.
