# G4.4 DEV — same issued S49 Action RUN→JOG→WALK

Branch `self/dev-g44-intra-action-gait-transition-20261029` from G4.3 HEAD `882e2441544e21eca781876189dbe15f40a46547`.

Explicit opt-in `--g44-intra-action-gait-dev` and `S49_G44_INTRA_ACTION_GAIT_DEV_ONLY=1` with inherited G4.3/G4.2/G4.1/G4 gates. The same issued S49 original Action, S15 sole native reader/writer and original T2/P1/M0 ledger are retained, and no new S49 Action is introduced.

Only a native observed RUN Action can schedule JOG at clearance <=1.95m, then WALK at <=1.55m; if within tolerance it requests original CLEAR. Each new phase is a strict `g44_gait_transition_dev` sub-effect with exact original `parent_action_id`, index 1/2, from/to states and deterministic ID. Original Node verifies active sprint Action, forward held, exact ordered parent and phase. Local native `sprint=false` then `sneak=true` actually change movement input while the original S49 Action remains open. Original S15 serially awaits each typed applied source-sequenced ACK; failure runs original CLEAR and marks Action UNKNOWN. The transition is not a second executor or self-authorized Action.

Original S16 after CLEAR and G4.3 quiet native samples still control Goal arrival; in-flight decision does not attest REACHED. Existing T2 per-tick gait candidate is from original Paper/Node observations, not claimed by command ACK; no R qualification. Each S49 pulse is still <=0.35s, so some original RUN Actions may have zero or one transition depending on live observations.

Focused Python 3.12, Ruff, Node typed-protocol negatives and disposable Paper 1.21.8 comparative DEV Worlds preserve original source and retained evidence. No QUAL/SCIENCE or main/Draft PR promotion.
