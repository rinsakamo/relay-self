# E2b-1 Stage27 SENSE DEV

`--stage27-enable-sense` opts in on the original Stage27h, i, or j DEV runner. The flag passes through the original preset runner to `OwnedResidentPhysicalBridge(enable_sense=True)`. Login, native session, dispatcher, original physical admission and ActionPort remain shared. The default remains disabled.

After verified login, the existing ProcessSession dispatcher decodes passive native JSONL into the owner-bound frame. Stage27h `pre_action` asks that same bridge for a current frame and records its L0 projection. It does not change MOVE selection, target, admission, STOP or WAL. Missing SENSE does not grant route clearance or cause a new STOP. AABB and route status remain UNKNOWN.

The CPU test uses original login, ProcessSession decoder and owner bridge with synthetic JSONL, then exercises Stage27h preflight. It checks source revision, position updates, coverage and expiry. Existing E2a tests cover two residents, rejoin, epoch, dispatcher errors, correlated probes and STOP ACK delivery; existing Stage27h tests exercise the original physical admission, ActionPort and terminal WAL with simulated native effects. These are not real Minecraft evidence. The subsequent E2b-1B integration below combines the normal Stage27 motor hook, original ProcessSession and a full simulated physical action in one test.

Freshness measures elapsed monotonic time after Python receives a line. It cannot establish time spent in the native or pipe buffers or the age in Paper ticks. Present consumer integration, Memory, full collision/routing and actual AABB, unlimited action-time reception, and overall CPU/child/pipe resource bounds remain HOLD. No real World was run.

## E2b-1B CPU/offline motor integration

`tests/test_e2b1b_motor_integration.py` invokes the unmocked
`stage27h_real_a_motor_hook` with the original resident login, real
`MineflayerProcessSession` decoder and dispatcher, original L0 loop, Intent,
Skill, PhysicalIssueAdmission, ActionPort, native ACK matcher, STOP settling,
and WAL. The model endpoint, Paper log and Mineflayer JSONL are synthetic;
no physical World is involved. The Paper sample does not independently
attest this synthetic movement or Action causality.

For SENSE enabled, the hook's preflight reads `mineflayer:native-A:11`;
the test checks the corresponding original captured JSONL row and position.
AABB and route remain UNKNOWN, and the preflight adds no physical authority.
The same test verifies one parent Action, its LOOK/START/STOP child IDs and
applied ACKs, all settling probes in raw stdout, a terminal
`NATIVE_PLACE_MOVE_SETTLED` WAL row and no unresolved Action. A passive move
interleaves START ACK and STOP. The same hook succeeds with SENSE disabled;
a rejected STOP ACK leaves the original PREPARED WAL unresolved. The
existing E2a suite covers resident separation, foreign sessions, epoch,
freshness, delayed rejoin callbacks and bounded queue HOLD with evidence
preservation. These tests do not prove unlimited action-time receive or all
overflow cases. This is CPU/OFFLINE evidence only; real World, collision
clearance and Present integration remain HOLD.
