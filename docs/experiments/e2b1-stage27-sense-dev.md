# E2b-1 Stage27 SENSE DEV

`--stage27-enable-sense` opts in on the original Stage27h, i, or j DEV runner. The flag passes through the original preset runner to `OwnedResidentPhysicalBridge(enable_sense=True)`. Login, native session, dispatcher, original physical admission and ActionPort remain shared. The default remains disabled.

After verified login, the existing ProcessSession dispatcher decodes passive native JSONL into the owner-bound frame. Stage27h `pre_action` asks that same bridge for a current frame and records its L0 projection. It does not change MOVE selection, target, admission, STOP or WAL. Missing SENSE does not grant route clearance or cause a new STOP. AABB and route status remain UNKNOWN.

The CPU test uses original login, ProcessSession decoder and owner bridge with synthetic JSONL, then exercises Stage27h preflight. It checks source revision, position updates, coverage and expiry. Existing E2a tests cover two residents, rejoin, epoch, dispatcher errors, correlated probes and STOP ACK delivery; existing Stage27h tests exercise the original physical admission, ActionPort and terminal WAL with simulated native effects. These are not real Minecraft evidence. They do not yet combine the normal Stage27 motor hook, the real ProcessSession and a full simulated physical action in one test; E2b-1 OFFLINE PASS remains HOLD until that integration and its adversarial cases are demonstrated.

Freshness measures elapsed monotonic time after Python receives a line. It cannot establish time spent in the native or pipe buffers or the age in Paper ticks. Present consumer integration, Memory, full collision/routing and actual AABB, unlimited action-time reception, and overall CPU/child/pipe resource bounds remain HOLD. No real World was run.
