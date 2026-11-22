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

## C-Real1d-3f partial follow-up

The source integration now also exercises synthetic movement toward and away
from the Target through the original ActionPort, settled WAL, Stage27h and
source admission before building candidates. An immobile synthetic Action
instead produces `NATIVE_PLACE_MOVE_NO_PROGRESS`; the settled-only source
validator rejects it. This is not proof of a comparable unchanged-gap settled
case. Missing Target comparison and valid-but-incomparable cases remain open;
frame-only tests do not close them. A remains HOLD.

The existing Stage27 handoff requires no existing Intent or Skill histories.
The Stage27h loop starts with zero Actions and requires the entire canonical WAL
to contain exactly its own rows; its source validator repeats this requirement.
Checkpoint capture preserves the WAL. Consequently, a second run after S1's
settled rows is not demonstrated by the existing path. No WAL was cleared,
transferred, or reassigned and no new Owner was introduced. T2 and its independent
scope, Action IDs, WAL and GPU tickets remain unproven; C remains HOLD. A valid
second-run lifecycle and the admission boundary need separate reconciliation.
The existing partial evaluation B remains subject to its regression tests.

### C-Real1d-3g: source admission classification

The synthetic original Owner → Stage27h → ActionPort → Native → canonical WAL
path admits settled observations with comparable PLACE gaps, including a
nonzero displacement at equal distance, and a vertical mismatch with no
comparable gap. The Native source emits all positions before the WAL is written;
no WAL or review frame is rewritten to manufacture either result. OUTSIDE and
TOO_CLOSE gaps have different meanings and are not compared. Missing Target
contract fails at Stage27h construction before Action admission; a foreign
session, inconsistent position or provenance fails source admission. A valid
source with no comparison retains an unavailable comparison and UNKNOWN choice.
Empty retained Memory leaves novelty unknown; observed movement does not prove
Skill success or its applicability or stop cause. NO_PROGRESS is a terminal WAL
outcome but is excluded by this settled-only review. These results concern the
bounded synthetic integration; they do not prove real World causality.

B's mixed and interrupted evaluation regression is independent of A. C's
second SkillRun / new Task lifecycle remains an I-lane dependency: the original
Owner and whole-WAL scoping must be reconciled before a separate run is claimed.
Neither A/B nor this handoff awards overall DEV settled-WAL evaluation PASS.
