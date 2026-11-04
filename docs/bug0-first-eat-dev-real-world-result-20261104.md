# Bug-0 first physical EAT: one-world DEV observation (2026-11-04)

## Outcome

One **real disposable Minecraft 1.21.8 World** reached food consumption through
the existing S49 `NormalSessionActionExecutor` + `ActionSupervisor` and existing
S51 `IssuedEatingExecutor` on [GitHub Actions run #41772769416](https://github.com/rinsakamo/relay-self/actions/runs/41772769416),
exact running HEAD `fe1152d6836dd521e99233c088e345152886d0c3`.
The S51 runner created one fresh S49 owner instance in this DEV session; this
does **not** demonstrate attachment to the general long-running S49 normal
runner or independent sole-issuer attestation.

Original S51_REPORT, captured after native EAT and teardown, states:

| Field | Observed |
|---|---|
| Original S49 EAT Actions | 1, `bug0-first-eat-bbf449c2-5f75-4ba2-a4b6-768ca987fd38` |
| Action terminal | `outcome` (`ActionState.OUTCOME.value`) |
| Minecraft food before -> after | **13.0 -> 18.0** |
| Original bread item count before -> after | **3 -> 2** |
| Same ActionSupervisor | true |
| Original native after-probe seq | 128 |
| Original native food pre-probe seq | 120 |
| Same-session earlier probe seq | 119 |
| Pre-EAT sampled position change | 0.0 m |
| Equip + consume commands | 2 |
| Node / Java process exit | 0 / 0 |
| World count for this run | 1 |
| M energy credited / learning | false / false |
| Independent external operator grant attested | false |
| Qualification / science | NO_GO / NOT_RUN |

The World was operator-staged with bread and hunger, not self-acquired food. It
used a local explicit DEV approval in lieu of externally authenticated
PROPOSE/ISSUE; this is **not** production permission. No pre-EAT MOVE was issued.

## Why the GitHub Actions job was red

The physical runner step completed **successfully** and returned `status=PASS`.
The following independent workflow assertion expected the string `"OUTCOME"`
instead of the actual enum wire value `"outcome"`, producing an
`AssertionError` (the other report fields passed until that line).

This is a **post-run test typo**, not a failure of native consumption or
ActionSupervisor termination. The original red workflow and its artifacts
are retained. The after-run patch changes **only that assertion's case** and
adds the exact terminal value to offline tests. No second physical World is
necessary or authorized by this maintenance edit; the one-shot workflow remains
commit-message-gated and will report `SKIPPED` on ordinary follow-up pushes.

### Source links

- [DEV physical run #41772769416](https://github.com/rinsakamo/relay-self/actions/runs/41772769416)
- [Artifact: original S51 report, native/command JSONL, Paper log and SHA256SUMS](https://github.com/rinsakamo/relay-self/actions/runs/41772769416/artifacts/13295312530)
- [Child Draft PR #723](https://github.com/rinsakamo/relay-self/pull/723)
- [Previous no-EAT Node constructor failure #41771166049](https://github.com/rinsakamo/relay-self/actions/runs/41771166049)

## Evidence ceiling and next focus

This is **DEV-first-physical-EAT-positive** evidence only. It proves an operator-
staged bread can be consumed in a genuine Minecraft World via an S49 owner
instance delegating to S51 and yields an original native food/inventory delta.
It does *not* prove autonomously finding food, learned eating behavior,
general owner connectivity, a full S49 physical issuance qualification, complete
safe tick alignment, metabolism credit, or SCIENCE.

There is no need to delay DEV work on more signature machinery. The next
functional milestone should be a second independent *capability*, such as REST
or ATTACK, or initial decision integration, rather than repeating the
already-positive bread EAT trial for a cosmetic CI gate.

`DEV_REAL_WORLD_FIRST_EAT_S49_S51_OUTCOME_PASS / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
