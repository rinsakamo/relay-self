# W4 Protected Blob Adoption v2

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN / NO_NEW_WORLD_RUN.

Repository Owner/Admin `rinsakamo` approved prospective adoption in
[Issue #633](https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6356863445)
and [Draft PR #634](https://github.com/rinsakamo/relay-self/pull/634#issuecomment-6356864256).
The two read-back bodies, authors, URLs and SHA256 are retained in the
[versioned manifest](w4-protected-adoption-v2.json). This permission authorizes
review and adoption; runtime results must still pass their own gates.
No signature or additional approval system is introduced.

The genuine historical source is frozen PR HEAD
`1473c74e4448bb9a527747de0619c8e55ffbd827`. All 19 historical Git blob IDs
remain unchanged in `PROTECTED_BLOBS`. Each manifest row binds its old blob
to that exact commit and path. The guard resolves the path, checks object
type, reads its bytes and verifies its Git blob digest. An arbitrary blob's
existence is insufficient. The 15 non-adopted current files still equal
those original bytes, including S18 and Action/S10 owner sources.

The four adopted sources are the inspected bytes of existing local candidate
`f34ccc0bf86f271849034c21abd254e5e3de780f`:

- `adapters/mineflayer/process_session.py`: original single Node stdout reader;
  startup custody, cancellation, confirmed reap and raw receipt sealing.
- `adapters/mineflayer/s31a_real_server_ci.py`: original sole Java collector;
  three-argument API, raw OFF/ON, readiness failure and collector settlement.
- `adapters/mineflayer/s34_native_world_cognition_ci.py`: original S34 owner;
  abort the same session on failed/cancelled native spawn before handoff.
- `adapters/mineflayer/s49_normal_session_real_ci.py`: original S49 owner;
  supervised Node/Java/collector/temp cleanup, returncode consistency,
  fail-closed classification and atomic report publication.

For each path the manifest includes historical commit/path/blob, prospective
Git blob and content SHA256, change reason, owner, approval URLs, v2, source
application HEAD and related tests. Git blob SHA and content SHA256 are
separate. The guard also anchors prospective bytes to the existing source
candidate, rejecting a coordinated edit of current source and manifest.
The manifest does not contain its own final commit hash: the exact adoption
commit and test subject are recorded in external verification reports.

The original lease protection test remains active and preserves its owner
identity assertions. It now invokes historical and current adoption checks.
The adoption test module covers all 19 individual original-hash tamper cases,
all 19 current mutations (15 protected plus 4 adopted), substituted source
commit/history path, bad prospective blob/SHA256, coordinated unreviewed
source edit, missing/altered approval, unlisted path and attempted Action
adoption. No skip, xfail or historical-pin replacement is used.

The existing self-demo workflow retains every job, experiment and stop
condition. Its exact path allowlist gains only this adoption record,
manifest and the existing bounded recovery/adoption tests. The deterministic
focused job also runs the adoption and retained-owner guards. It does not
launch the opt-in native OS suite or a World. Actions remain uninvoked in
this transaction: commits carry `[skip ci]`, and actual push/PR triggers
were checked for events outside GitHub's skip mechanism.

The prior procedure's A/B/C owner/path/test decisions are satisfied by the
current explicit Owner/Admin approval, which expressly covers these four
paths and the scoped guard/path migration. Current GitHub policy has no
CODEOWNERS file or independent review requirement for the PR head branch;
the active main-only ruleset remains unchanged. The historical procedure
and prior failed-adoption report remain evidence of their earlier state.

Verification evidence is stored separately in
`/home/rinsa/w4-adoption-v2-evidence-20261023`. The prior evidence roots
`/home/rinsa/w4-pr634-final-evidence-20261023` (72 indexed files) and
`/home/rinsa/w4-recovery-evidence-20261023` (189 indexed files) were rehashed
successfully and remain unchanged. The old 584 PASS / 1 FAIL / 0 SKIP
result belongs to the pre-migration HEAD, and the prior 12 inert tests and
14 PID closures remain their original evidence. Fresh exact-commit focused,
inert Node/JVM, Node adapter, Ruff and repository-contract results are
recorded separately, including command, subject, exit code and SHA256.

The earlier real-Minecraft DEV run `1e86a714f3ea3374` at
`1b221d845e42ea0e8be003239525c50de20e7fef` is preserved as
DEV_LOCAL_OBSERVATION_ONLY_PASS for that subject only. It is not a PASS for
this adoption commit. This transaction executes zero new Worlds, Minecraft
servers, live Mineflayer sessions, physical Actions, OUTCOMEs, S10 writes or
grant consumptions. External custody/signer qualification and science remain
NO_GO / NOT_RUN. PR #634 remains Draft and unmerged; FULL is not run.

Local migration gate on the staged adoption tree: Python 3.12 focused
617 PASS / 0 FAIL / 0 ERROR / 0 SKIP; inert Node/JVM 12 PASS with independent
14/14 PID/starttime alive-and-absent confirmation, settled collectors and
no pending owner tasks. SelfBody 10 / SelfWorld 32 / S18 7 PASS. Node 22
adapter 37 PASS; Ruff, contracts and the actual repository path-policy case
statement PASS. These pre-commit results are `migration-*` evidence; the
`final-*` gate must independently confirm the exact committed subject before
push/integration. Initial Ruff import-order failure and a path-policy audit
script argument error are retained; both were corrected and rechecked.
