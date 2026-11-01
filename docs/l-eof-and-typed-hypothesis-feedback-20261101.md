# RelaySelf L — future Paper EOF and previous L2 hypothesis feedback (2026-11-01)

Child of Draft #677; owners #431/#653. The 2026-11-01 previous actual World produced 2 actual Gemma OPEN responses, but its original Paper EOF lacked a final newline and its original World and mandatory independent audits FAIL. That report and its negative classification are unchanged. **Do not retroactively requalify the previous run.**

## Future-run Paper EOF envelope

A default-OFF new opt-in CLI flag --l-mp11-paper-eof-dev, coupled with L_MP11_PAPER_EOF_DEV=1, must be set before a new physical World; this is only accepted alongside original L live-source G3 mode.

Keep raw Paper bytes and raw SHA unchanged. After Paper server exit, the owner creates a typed report envelope: full-original SHA and length, complete-line SHA and length, exact EOF suffix hex, end-state label. Only two final forms are recognized: newline-terminated source, or newline-terminated source plus exact two-byte JLine prompt hex 3e20. Unknown suffix, partial line, malicious extra prompt, malformed UTF-8 and source/manifest mismatch must fail closed. No rstrip, append-newline, rewriting an original or broad parsing relaxation.

Original audit_multi_trial_paper retains the strict complete-line contract. Only the new source owner and independent future G3 reader may interpret the complete-line view from the predeclared envelope. The independent G3 audit independently checks the envelope fields from full original bytes and requires full original hash identity. A terminal prompt is not itself evidence of complete World success, correct sensor semantics, or any L2 adaptation.

## Typed previous L2 feedback, no future leakage

First OPEN: no earlier L2; prior_hypothesis_relation = FIRST_HYPOTHESIS. Second OPEN: strictly require previous proposal SHA, first original Action ID/Paper prefix SHA, World/session/subject identity, and one additional completed trial. The second input contains previous hypothesis/model-family/reconsideration/unapproved proposed test, previous NEXT-trial WAIT8 TOTAL displacement prediction in meters, observed second WAIT8 TOTAL in meters, and absolute forecast error in meters (or explicit NO_NUMERIC_FORECAST). The original next-tick single-pair error and its CHEAP next-tick MAE are *different targets*, never interchangeable with the WAIT8-total forecast error.

Require 1–4 typed numeric citation objects with metric_role, trial_ordinal, pair_index and value_m. Allowed roles: WAIT8 total, one Paper pair prediction, one Paper pair absolute error, Paper cheap next-tick MAE, or (only on second OPEN) the previous L2 NEXT-WAIT8 prediction/absolute error. Every reference must match past source to 1e-8m, with correct target, original trial number and pair index. Reject duplicate/future/nonfinite/incorrect metric citation, malformed JSON and extra action commands.

Possible second-call relations are KEEP_PRIOR, REVISE_PRIOR, REJECT_PRIOR, ABSTAIN_ON_PRIOR. A REVISE_PRIOR candidate requires previous non-null forecast and at least one newly completed second-trial citation. It is still an *unadmitted* hypothesis, not an actual structural model revision, persistent learning, L1 Habit or an L0 promotion.

Numeric citation checks cannot prove that free-text causal interpretation is correct. Model suggesting SURFACE_DEPENDENT on unchanged grass remains a physical hypothesis awaiting a controlled different-surface experiment. Future heldout evaluation and CHEAP comparisons remain separate.

## Developer evidence / next bounded physical gate

New modules: adapters/mineflayer/l_mp11_paper_eof_envelope.py and adapters/mineflayer/l_mp11_typed_feedback.py. Updated optional original S49 owner runner, future G3 original auditor, live L2 request/parser, tests and workflow. Offline CI checks historical FAIL nonpromotion, exact raw-file hash, malformed EOF, strict numeric role/target and prev-proposal SHA, existing source/S49 regression.

No new real Gemma or World run in this increment. A separate authorized exact-HEAD run is needed for live source requalification: one disposable original Paper World, at most 3 original S49 Actions and 2 genuine Gemma OPENs, source-verifiable original Paper/W3/hash and model identity, before/after native sequence, no later outcome leakage, full cleanup and mandatory independent auditor SUCCESS. No second Action issuer, no automatic L0 promotion and no new L2-controlled physical test is added here.

Classification: FUTURE_EOF_AND_TYPED_FEEDBACK_OFFLINE_ONLY / HISTORICAL_WORLD_FAIL_UNCHANGED / REAL_NEW_WORLD_0 / REAL_NEW_GEMMA_0 / NO_ACTION_OR_LEARNING_ADMISSION / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
