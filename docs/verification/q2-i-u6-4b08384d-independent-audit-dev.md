# Q2 — independent read-only audit: Unified I U6 exact HEAD `4b08384d`

Date: 2026-11-22. **Independent Q inspection of immutable GitHub objects and exact-HEAD CI**. This document does not perform a World, Native, Paper-source, Owner, L1/L2 GPU or physical action run. The scope is integration provenance and fail-closed CPU semantics; it is **not** real original-source qualification.

- Unified I [Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124): `4b08384dfd928f0e5788038ec721064df6353bff`; Git tree `ec517e846b84399ce25d332a8aed26d67beeb1bc`; parent `474086e8e0ec01127bdf61f0e52b780849d79660`.
- U5b baseline: `82ac3bced9da7ee3175627bd745811b664608348` (618 Git blobs).
- R import: `2ca64e1c5816bf505586ce75cb038cbd872b1d79` (624 blobs), derived from R [Draft #1128](https://github.com/rinsakamo/relay-self/pull/1128) `00229bd2e68257a4ef5e26608cdf075904c18820`.
- Structural Q/B import: `474086e8e0ec01127bdf61f0e52b780849d79660` (624 blobs), derived from B/Q [Draft #1126](https://github.com/rinsakamo/relay-self/pull/1126) `38243d4cd15f30453eacd3e17df4c80bd664a0ed`.
- Final commit adds only `docs/architecture/i-unified-r06-schema3-handoff-dev.md`: 625 blobs. All recursive trees untruncated.

## Independently reproduced Git tree/source custody

Compare the *actual GitHub recursive tree blob SHAs*, not PR prose: **618→625; 7 added, 3 modified, zero deleted original paths**. Exactly seven R-authored paths in the selective R commit had byte-identical blob SHAs at R source `00229bd2`, and exactly two B/Q paths in the selective strict-JSON commit matched `38243d4c`. The final documentation commit has one added path, no source file changes. No original B/physical/I2 source path was deleted/replaced in these three commits.

R match, 7/7:
- `src/relay_self/r0_cognitive_context_dev.py`
- `src/relay_self/r05_context_compat_preflight_dev.py`
- `src/relay_self/r06_unified_context_preflight_dev.py`
- `tests/test_r05_context_compat_preflight_dev.py`
- `tests/test_r06_unified_context_preflight_dev.py`
- `docs/architecture/r05-context-compat-preflight-dev.md`
- `docs/architecture/r06-unified-bi-current-preflight-dev.md`

Q/B match, 2/2:
- `src/relay_self/bd1b_schema3_source_readback_dev.py`
- `tests/test_bd1b_schema3_source_readback_dev.py`

These verify **same-blob selective transfer**, *not* real Original Owner production chronology, independently held S1 witness, or honest Git publisher/source attribution.

## Actual implemented semantics reviewed

- R0.5 `audit_r05_initial_owner_context` reads the original resident Owner's Present and schema-only CURRENT under the resident lock, compares scope/source/source revisions and repeats Present before returning a non-authorizing audit record. Rejects reJOIN reuse of initial Stage28. `R1_EXTERNAL_HOLDS` and `r1_shadow_allowed=False` are intrinsic to the typed result.
- R0.6 `audit_r06_unified_b_i_current` directly reads the existing `read_i_unified_b_current`, compares original B resident/owner identity, schema/source, UNKNOWN coverage and zero I signal injection. Performs a second I read and repeats R0.5. It does not call `prepare_i_unified_exploration_turn` or authorize any I adoption, physical child, GPU ticket or R1 shadow. CPU synthetic A/B tests check foreign owner/session/epoch, mutation-free retained state and adoption turns.
- The B/Q source `_json` now uses `object_pairs_hook=_unique_source_keys` and `parse_constant=_reject_nonfinite` for producer report, Schema3 Prelogin, original initial Native/Paper JSON and original logout receipts. Four role-specific duplicated-field tests and one NaN hostile test recalculate exposed pins and still require HOLD. **The raw issuer's physical WAL is parsed elsewhere** (`physical_action_journal._read` uses ordinary `json.loads`); do not mislabel source JSON hardening as WAL-producer authentication.
- The original `PhysicalIssueAdmission` and its U5b gate-held S1 lease/child checks remain at unchanged blobs from U5b. The existing test `test_quarantine_after_start_is_a_stop_safety_hold` explicitly asserts that, after LOOK+START and resident quarantine, MOVE_PLACE `clear_controls` is rejected. The gate code's `quarantine_stop` exception applies only to `effect_family == "MOVE"`, **not MOVE_PLACE**. Thus real MOVE_PLACE enablement remains unsafe. There is also no atomic coupling of final gate check with external Native stdin write.
- **Documentation inconsistency:** `R06_EXTERNAL_HOLDS` still includes `B_SCHEMA3_DUPLICATE_JSON_SOURCE_AUDIT_NOT_IN_UNIFIED_HEAD`, despite the strict parser and tests being byte-identically present in this U6 HEAD. This blocker text is stale. Keep R1 physically and cognitively HOLD; rename only to a truthful *producer source custody not attested* reason in the owning R/I lane. Do not treat the stale label as a revoked safety gate.

## Exact-head CI independently checked

[GitHub Actions run #44983926420](https://github.com/rinsakamo/relay-self/actions/runs/44983926420), `head_sha=4b08384dfd928f0e5788038ec721064df6353bff`, **attempt 2** `completed/success`. Five individual job statuses independently fetched: pytest, lint, repository-contracts, mineflayer-adapter, paper-tick-witness all success. Pytest log literally reports **`2865 passed in 110.76s`**; Paper job log contains **`BUILD SUCCESS`**. Attempt 1 had Paper failure fetching Maven `org.apache.maven.plugins:maven-resources-plugin:3.4.0` from Central; its other four jobs succeeded; attempt 2 succeeded at the **same SHA**. The failed attempt is not concealed or interpreted as a successful original-world run.

## Independent Q disposition

- **`Q2_U6_GIT_TREE_AND_SELECTIVE_SOURCE_BLOB_CPU_OFFLINE_DEV_PASS`**: 9/9 transferred blob identities, tree preservation and exact-HEAD CI independently read.
- **`Q2_R06_B_I_STAGE28_READ_ONLY_CODE_REVIEW_CPU_OFFLINE_DEV_PASS`**: bounded initial-stage code/test inspection; not an independently authenticated Native/Paper trial.
- **`Q2_SCHEMA3_STRICT_JSON_STRUCTURAL_SOURCE_REVIEW_CPU_OFFLINE_DEV_PASS`**: raw format parsing only.
- **`I4A_REAL_ORIGINAL_S1_S2_SOURCE_HOLD`**, **`CROSS_PROCESS_STDIN_ATOMICITY_HOLD`**, **`EMERGENCY_MOVE_PLACE_STOP_AND_SETTLING_HOLD`**, **`ORIGINAL_OWNER_NATIVE_PAPER_PRODUCER_AUTHENTICATION_HOLD`**, **`HISTORIC_I2_I4A_SUITES_NOT_ALL_INCLUDED_HOLD`**.
- **`PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`**. No real Minecraft World or Gemma/Native invocation was made for this independent review. Original R, B/Q and integrated I Drafts remain unmerged.

Q2 does not mutate unified I, R, B, C, E or the Original Owner. Review records are Q-owned and use immutable evidence source SHAs.
