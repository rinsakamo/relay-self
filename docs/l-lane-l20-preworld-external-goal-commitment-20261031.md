# L20 — Session-agnostic externally authored Goal commitment before S49 World

Date 2026-10-31. Base L19 docs HEAD `9a7a81358c862be86d2709b32faf99e2ceda1926`.

## Why this is a separate contract, not a disguised L14 Goal original

S49 allocates its Mineflayer `session_id` only after the disposable World starts and allocates its first `action_id` from real native event seq after the first WAIT decision. Existing `L14_PREDECLARED_SPATIAL_GOAL_V1` **requires** those two IDs in its original criterion *and* `created_before_seq`. Writing that original only after learning the two IDs is not an honest pre-World commitment, even if its `created_before_seq` field says zero. Reusing L16's operator plan as an independent external Goal also creates false independence.

L20 therefore introduces `L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1`, a **different** externally authored source contract. Before the World, it fixes:

- `criterion_id`, `external_goal_owner_ref` and `experiment_ref` (identifiers, no secret).
- Goal `target_x`, `target_z`, `tolerance_m`, `stable_probe_delta_max_m`; these must exactly match the L16 operator's prospective Goal plan.
- `session_scope = UNKNOWN_UNTIL_S49_SESSION_START` and `action_scope = FIRST_S49_PHYSICAL_ACTION_ONLY`. No session/Action IDs are retrospectively inserted into the immutable pre-World document.
- `independent_goal_observed = false`, `authorizes_learning = false`; all unexpected fields are rejected.

The independent goal reviewer must **author and preserve the canonical UTF-8 JSONL document separately** from S49, and externally anchor its SHA256 *before* World execution. The L20 code NEVER creates this reviewer original, signs on the reviewer's behalf, or fabricates a timestamp. A SHA supplied at review time is a **consistency check only**, not cryptographic proof of a past time or a separate reviewer. No external independent Goal result is produced by this contract.

After S49, `adapters.mineflayer.l20_external_goal_commitment_readback` uses the existing exact S7 + L17 saved first-Action readback and original operator plan, binds their actual `session_id`/`action_id`/received+sent SHA to the fixed external criterion SHA **as a new L20 read-only binding**. This result is *not* the old L14 pre-Action criterion. It must NOT be cast to the L14 format, nor asserted to satisfy L13's external Goal admission. Existing real L10 qualified training count remains zero.

## Reviewer-produced original format (example values only)

The external reviewer, **not S49**, authors one canonical JSONL row with exact keys and no whitespace outside the JSON separator format. The values below are illustrations, not real World coordinates:

```json
{"action_scope":"FIRST_S49_PHYSICAL_ACTION_ONLY","authorizes_learning":false,"criterion_id":"external-criterion-001","experiment_ref":"l20-experiment-001","external_goal_owner_ref":"paper-reviewer-A","independent_goal_observed":false,"schema":"L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1","session_scope":"UNKNOWN_UNTIL_S49_SESSION_START","stable_probe_delta_max_m":0.05,"target_x":0.0,"target_z":0.0,"tolerance_m":0.49}
```

The file must contain exactly that one JSON object followed by one newline, canonical `json.dumps(sort_keys=True, separators=(",", ":"))`. Select true prospective Goal coordinates **before** Minecraft starts; NEVER adjust to force a `REACHED` result. Keep the reviewer original outside the S49 capture directory. Store and independently timestamp/admit the SHA256 *before* the physical run (outside this code).

## CLI preflight and source readback

On the operator's WSL2 machine, after an independent reviewer has supplied the original and SHA, explicitly set the real target to the same prospective x/z:

```bash
cd ~/work/relay-self
git fetch origin
git switch integration/l20-preworld-external-goal-commitment-20261031
export PYTHONPATH=src:tests:.
export EXTERNAL_GOAL_ORIGINAL=/absolute/reviewer-owned/goal-preworld.jsonl
export EXTERNAL_GOAL_SHA256=<externally-published-64-lowercase-hex-sha>
export GOAL_X=<preselected-world-x>
export GOAL_Z=<preselected-world-z>

# BEFORE World: pure source consistency check; no Java, Node, Minecraft.
python -m adapters.mineflayer.l20_external_goal_commitment_readback \
  --external-criterion-original "$EXTERNAL_GOAL_ORIGINAL" \
  --admitted-sha256 "$EXTERNAL_GOAL_SHA256" \
  --target-x "$GOAL_X" --target-z "$GOAL_Z"

# Then run the existing explicitly granted S49 disposable World capture:
# See docs/l-lane-l19-native-goal-interleaving-world-readiness-20261031.md.
# Use the same GOAL_X/GOAL_Z, fresh --l16-capture-root and L16 confirmation.

# AFTER World: no new Action, compare sealed S7/L18 S49 original source.
python -m adapters.mineflayer.l20_external_goal_commitment_readback \
  --external-criterion-original "$EXTERNAL_GOAL_ORIGINAL" \
  --admitted-sha256 "$EXTERNAL_GOAL_SHA256" \
  --target-x "$GOAL_X" --target-z "$GOAL_Z" \
  --root /absolute/capture-root \
  --s49-report /absolute/s49-report.json
```

Preflight output: `PREWORLD_SOURCE_ONLY_NO_TIMESTAMP_AUTHENTICATION`. Post mode: `POSTWORLD_FIRST_ACTION_SOURCE_ONLY`, exact criterion SHA, first Action/session IDs, S7 original hashes, source-shaped L16 Goal geometry, and unaltered L17 S16 original-present boolean. Any bad SHA, symlink, geometry mismatch, duplicate JSON keys, added `goal_status`, any forged pre-known session/action or learning-authority flag, tampered capture, foreign session/Action or missing files fails closed.

The CLI never writes any file or starts a World. If a real S49 run is authorized it is performed **separately by the existing physical S49 script**, and has its own Java/Node/EULA, fresh disposable World and actual test report. The current GitHub-only L20 task does not issue any real World test or consume a past grant.

## Remaining path to an actual L1-learning demonstration

1. Physical S49 DEV World produces source original S7 received/sent + first Action L18 S16 terminal + two Goal probes, and the external reviewer really precommits an independent goal document before the World.
2. Independent external observer produces an **actual per-Action Goal result original** after observing World and certifies source, nonintervention and action/criterion linkage. An independently reviewed session/action binding between L20's preregistration and the old L14/L13 contract (or a separately approved new goal contract) is still required; **L20 does not authorize that mapping**.
3. Admit real prior positive World/Body source plus new distinct current epoch under the existing L10 admission gates. Compare memory retention ON vs OFF, original S choice and next-epoch cheap advice. No automatic L0 promotion.

**Evidence ceiling:** `DEV_ONLY / L20_PREWORLD_EXTERNAL_GOAL_COMMITMENT_SOURCE_ONLY / EXTERNAL_OWNER_AUTHENTICATED_FALSE / TRUE_PREWORLD_CHRONOLOGY_UNPROVEN / NEW_WORLD_0 / REAL_PER_ACTION_GOAL_0 / QUALIFIED_L10_0 / S10_S11_WRITES_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.


## L20 opt-in now enforced at actual S49 pre-World entry

L20 preflight is also wired into the **original** `adapters.mineflayer.s49_normal_session_real_ci.qualify` as two optional paired arguments. If both are given, S49 validates external criterion bytes, external provided SHA, identity and exact L16 preselected Goal **before creating its S7 recorder or provisioning Java/Node**. Invalid or unpaired source yields `BLOCKED` without a Minecraft server. A passing preflight is included in the report as `l20_external_goal_preflight` with honest `authenticated_external_owner=false` and `externally_attested_before_world=false`. Default S49 without those arguments is unchanged.

When the experimenter separately grants a new disposable World, append the following two arguments to the existing L19 S49 run command (both must be supplied; L16 original capture must also be enabled):

```bash
  --l20-external-goal-original "$EXTERNAL_GOAL_ORIGINAL" \
  --l20-admitted-sha256 "$EXTERNAL_GOAL_SHA256"
```

This does **not** establish that the SHA was externally published before World; it only prevents accidental/posthoc goal geometry changes in the exact S49 process. Independently preserved reviewer original, anchored prior publication and subsequent genuinely independent Goal observation remain separate responsibilities. A S49 Python-preflight matching a SHA from its own command line cannot bootstrap independent physical Goal authenticity.

## Exact source revision validation (2026-10-31)

- **Successful exact code/test/workflow HEAD:** `a9fe9df42a3b802bd7344bd55784bb12b06e6fa2`.
- [GitHub Actions #41161798633 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41161798633): Python 3.12 **68 PASS / 0 FAIL / 0 SKIP**; Ruff, compileall and repository contracts PASS. These include explicit S49 pre-World Goal source injection controls, successful read-only preflight followed by deliberately BLOCKED Java startup, standalone preflight, post-S49 S7/L17 source binding and rejection controls.
- Preliminary failures are preserved: [#41161378223](https://github.com/rinsakamo/relay-self/actions/runs/41161378223) was an unused test import; [#41161660826](https://github.com/rinsakamo/relay-self/actions/runs/41161660826) was a fixture assertion mistakenly counting a deliberately placed foreign criterion as an S49-created file. The final test asserts the absence of S49-created operator Goal or native S7 files, not the absence of its test's own fixture.
- The resulting later documentation-only HEAD is not claimed to have a new CI test run. No real Java Minecraft server, physical Node/Mineflayer session, independent World observer, new independent per-Action Goal receipt or learning epoch was executed from this GitHub-only development turn.
