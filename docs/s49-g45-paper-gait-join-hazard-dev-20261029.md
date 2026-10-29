# G4.5 DEV: source-bracketed gait ACK / original Paper-T2 and in-stage danger
Parent G4.4 HEAD `0304df61b4ce0371eee373ffe1dcb44c09350506`. Isolated branch `self/dev-g45-paper-gait-ack-join-hazard-20261029`; main and sibling Drafts unchanged.

`--g45-paper-gait-join-dev` (requires G44, `S49_G45_PAPER_GAIT_JOIN_DEV_ONLY=1`) compares original S49 sub-effect ACK source sequence with original Paper/G1 rows and existing T2 owner receipt source sequence, over each interval before the next typed ACK or CLEAR. Explicitly record `NO_STABLE_FRAME` when the two-sample Paper cadence does not establish one stable gait candidate. Source ordering and one T2 owner do **not** prove exact native packet→Paper WorldTick causality, full-tick gait or a new P1/M0 debit.

`--g45-hazard-during-gait-dev` (plus `S49_G45_HAZARD_DURING_GAIT_DEV_ONLY=1`) in separate disposable World injects one zombie as operator World change after **source-confirmed** original RUN→JOG ACK. L0 must independently observe the real zombie in the next native probe, interrupt the same Action, and original S15 must apply CLEAR, then S16 mark UNKNOWN; no further action issued. DEV failure rather than fabricated hazard/qualification if the observation misses. No independent Paper tick input-off claim.

CI: focused Python 3.12, Ruff, Node22, Java21, pinned Paper1.21.8, 3 fresh disposable Worlds (G4 baseline, G4.5 successful Goal and Paper source join, G4.5 hazard fail-closed). Preserve native reports, Paper files and hash receipts. DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
