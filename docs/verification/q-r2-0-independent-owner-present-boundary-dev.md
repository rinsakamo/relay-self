# Q R2-0 — independent exact-source and Original Owner Present boundary

Scope: independent **CPU/Git only**, neither real R2 World Shadow execution nor
R2 product routing. This Q branch derives from Q R1 Draft #1130 and does
not edit R1, R2-0, Original I U31 or original Q B/Owner/WAL code.

Exact inputs:
- Original I U31: `d3034026a8eea3d2d4927527f5bc0d6ad0455457`
- R1 read-only Shadow: `06349c7a216b042511a90e05ad0196f4a7164378`
- R2-0 responsibility-only refactor: `a8d1492a1e54f3f647109da183cf71179c7b5932`
- Historical U31 readback: LocalCodex previously reported
  `Q_R1_U31_WSL_ORIGINAL_READBACK_DEV_PASS`. This CI does **not** remount
  or reread `/home/rinsa/evidence/i-u31/`.

The dedicated `.github/workflows/q-r2-0-pinned-boundary.yml` uses a
separate exact R2-0 Git worktree and independent Q test file, plus the
previous Q R1 runtime probes. It requires full commit SHA identity and
zero Git checkout mutation.

The Q Git inspector checks all intermediate R1→R2-0 commits, preserving
every pre-existing R1 path except its explicit read-only Shadow module,
allowing only three R2-0 new files, and checks the helper's nine stable
diagnostic code constants, source imports/call sites and no obvious
execution/memory/physical writers. This is a **bounded negative static
audit**, not formal proof of arbitrary indirect noninterference.

Independent runtime probes exercise both A and B original Owner read paths,
no file/Owner/Skill/Intent/Question changes, all nine mismatches with a
separately retained reference CURRENT, and cached comparison invalidation.

**Signal provenance qualification:** initial R1 CURRENT inherits
`signals=legacy.present.signals` from the original Owner's Present. Thus
a mutated *but otherwise valid* legacy Signal selector is accepted into a
new initial CURRENT; it is not an independent Schema recomputation. When
comparing to a *previous* CURRENT, the nine-field helper detects the
different Signal, and `r1_shadow_is_live` must reject that prior cached
MATCH. Do not turn this known R1 data-flow fact into an imagined initial
inconsistency or a claim of independent Signal producer authentication.
The first 27-case Q run had 26 passes and one overstrict test expectation
here; Q corrected the test interpretation without changing R2 source or
disabling cached-staleness rejection.

The only possible bounded positive classification is
`Q_R2_0_PINNED_GIT_AND_RUNTIME_CPU_DEV_PASS` when the final independent
GitHub Actions run is green, with explicit
`R2_1_HOLD / R2_2_HOLD / R2_3_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
