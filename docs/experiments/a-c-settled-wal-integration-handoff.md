# A + C settled WAL integration handoff

The first integration target is the existing Stage27h terminal run of one to
four Actions. A's Stage27m 5 m trial (#1059, head
`666a5dc4331cabe935d7555d9a36940c2330323b`) has nine Actions; I must reconcile
its Action sequence, budget and Target contract before extending this boundary.
The execution of that trial used `7198be44e08961abad3f96d249cbb7d0b68c5647`.

Read-only path: A physical outcome → original owner's clear, settled WAL →
`prepare_stage27hi_multi_review` → `execute_evaluation` → EvaluationReadout.
Reuse the existing owner, physical admission and resident lane; this path does
not introduce another ActionPort, owner or database.

I must preserve and verify the same Self, World and epoch; original SkillRun,
Intent, invocation, Target and Preset; ordered Action IDs and canonical WAL
digest; Native session and accepted CURRENT probe/revision. The terminal probe
must match the final settled WAL row. The original lane issues scoped GPU
tickets and unique Task references; each result and HTTP receipt is checked
against its own ticket, source and generation. The readout applies only to that
qualified terminal source and Task, and does not establish Goal or Skill success.

Skill, Intent, Memory and WAL remain unchanged by evaluation. On expiry or
source mismatch, HOLD the cognitive result and preserve completed axes and HTTP
receipts as audit evidence, not an adoptable readout. A newer CURRENT alone
does not requalify an old SkillRun; a changed session or epoch cannot borrow
old WAL Actions. A valid new run must supply its own settled evidence.

Test entry points: `tests/test_c_lane_stage27hi_multi_action_review_dev.py`,
`tests/test_c_lane_l1_evaluation_engine_dev.py`, and
`tests/test_c_lane_evaluation_readout_dev.py`. These are synthetic Native/HTTP
tests, not a real World or model integration. Source-admission representative
coverage and a new-run T2 recovery remain open until independently demonstrated.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
