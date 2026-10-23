# Product #537 — passive native SelfBody + SelfWorld join (isolated DEV candidate)

**OFFLINE DEV VALIDATED / PHYSICAL NOT RUN / NOT INTEGRATED INTO PR #634 / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Source base: PR #634 exact HEAD `f0751b915411e89f1d3dffe941461a308fcf2512`.
Candidate branch: `dev/self-product-passive-bodyworld-20261024`.

## Why this is product integration, not another W4 cognitive experiment

Product #537 prioritizes a self that operates as a continuous owned physical
session before separately optimizing curiosity or information value.
The existing `s49_normal_session_real_ci.qualify` already accepts a
`live_probe` callback for *previously received* correlated S49 native
probes, without granting observation or Action issuance to the callback.
The new `--mode DEV --dev-scenario native --run-disposable
--self-passive-views` path reuses exactly this read-only callback.

Each original S49 probe yields the existing `MinecraftPresent`, the original
`project_body_present`, `compose_self_body_view`, `project_self_world_present`
and `compose_self_world_view`, all sharing the **same session / native seq /
request ID / provenance and transient epoch**. The SelfBody/World composition
validates that join and preserves zero observations as unknown, not proof of
World absence/safety. The audit sidecar `self_views.jsonl` contains one row
per original probe plus a summary with count and errors. The product DEV receipt
compares sidecar request IDs, seqs and observed-entity counts to the already
persisted original S49 `source_pair_trace` and fails closed on mismatch.

The new observer never calls Mineflayer, does not observe a fourth time,
does not select an L0/L1/L2 policy, does not request a provider, does not
authorize an Action, and has no Memory, S17, S10 or reward privileges.
An observer projection error is retained in its sidecar but cannot veto the
original S49 sole Action issuer. An incomplete sidecar is not certified by the
outer DEV receipt. Its ephemeral fixed observer-self ID is **not** an
independently authenticated durable Self identity.

## Execution gate

This path is mutually exclusive with Stage R S10 development, W3 raw capture,
live L2, Stage L/N/O and other World scenarios. Normal dry-run behavior stays
unchanged. `--self-passive-views` outside explicit `--mode DEV` is rejected.
The original S49 remains a fixed three-native-decision/two-Action demonstration;
the addition **does not** turn it into long-running autonomous Self 1.0.
The existing `--confirm`, disposable World, output root, Java/Node and source
owner requirements remain applicable.

## Tests and remaining work

Static tests use fixed typed fake native probes and monkeypatch only the
original S49 `qualify` delegate (no JVM, Node, model or World). Required
checks: same-source join across three probe epochs, zero-selected semantics,
duplicate/stale/cross-session/uncorrelated provenance denial, mode isolation,
original Action owner independence, errors preserved, and receipt sidecar
binding. Existing `test_self_dev.py`, `test_self_world.py`,
`test_self_body.py`, `test_self_live_think.py`, S18/contracts are regression
dependencies.

The GitHub code authoring session cannot access the independent WSL2 runtime,
strict saved physical source or 82 protected / 770 historical SHA archives.
**No Python 3.12, Ruff, contracts, real S49, CI or integrity result is claimed.**
Before using the new flag, LocalCodex must independently inspect the final
candidate HEAD, run focused Python3.12 tests and Ruff/contracts, ensure all
new test cases really validate the receipt, validate existing source ownership
and protect the historic manifests; failures should be corrected and retained
on the isolated branch only. An authorized disposable DEV World run, if later
selected, requires the existing #537 local explicit opt-in; it is never
QUALIFICATION or SCIENCE.

PR #634 remains Draft and is **not updated, merged, or rebased** by this work.
Only after local source validation should the original product owner decide
whether to adopt this narrow passive observer into #634; it must never
silently modify the W4 cognition/information-value research classification.


## Independent local DEV verification (2026-10-24)

The fixed candidate `c69b53a8f518b496a4f0c99575b4ba331c5f924d` was
checked in an isolated Windows 11 / WSL2 Python 3.12.3 worktree. Initial
failures are retained externally at
`/home/rinsa/work/self-passive-evidence-20261024`.
The synthetic probe fixture now uses the protocol's derived provenance;
a hostile typed subclass exercises foreign provenance rejection. A supported
non-probe kind exercises observer rejection. The default DEV delegate keeps
its existing call signature when passive views are disabled.
Additional controls reject mismatched Body/World epoch/session/source and
exercise the outer DEV receipt for sidecar/source/Action substitutions.
These are offline tests with stub owners, not a new physical S49 execution.
The external report records final counts, integrity checks, and commit identity.

Remaining product work: separately authorized physical verification of this
flag, independent native-source attestation and durable Self identity, then
owner-reviewed adoption and a continuous decision/outcome loop. The fixed
three-probe demonstration does not establish autonomy or adaptive learning.
