# S49 native Java/Node custody — DEV-only no-World probe

Authority: original S49 #392, SelfWorld #633, W4 Draft #634, S18 freeze #354.
This probe does **not** authorize a protected-source exception, W4 live lease,
Minecraft World, Mineflayer Action, learning update, or scientific run.

## Evidence boundary

- Branch: `self/product-self-one-command-s49nativeos-20261021`. Record and verify
  its *exact* HEAD from GitHub before invoking. Use a detached isolated worktree.
- Test: `tests/test_s49_native_os_custody.py`. Four native tests exercise real
  Linux (including WSL2) child processes, with no Minecraft JAR and no network.
- Java fixture is an inert `javac`-compiled class that logs BOOT and sleeps.
  Node fixture is an inert JS timer. Both must be created in `tmp_path`.
  No Minecraft Java server, Mineflayer bridge or outbound connection is started.
- Cases: (a) Node and (b) Java canceled after OS child creation but before
  returned Process handoff; (c) original Node `MineflayerProcessSession.launch`
  canceled during waiting for `adapter_started`, W3 incomplete seal; (d)
  original Java `_ready_server` canceled during readiness with its *one*
  original stdout collector. The latter redirects the Java command to the inert
  fixture without changing the production command construction.
- Verify PID/starttime in `/proc/<pid>/stat` while alive, integer exit code
  and `process.wait()`, and PID absent under `/proc` after reap.
- The earlier no-World fake matrix and inert Python subprocess tests remain
  separate. This probe does **not** attest real Java server World startup, real
  Mineflayer adapter_started or spawn protocol, nor PID provenance under
  other OS users or a host crash.

## WSL2 independent execution contract

Use one fresh checkout/worktree, a dedicated evidence directory outside repo,
and Python 3.11 **and** 3.12. If either version, `javac`, `java`, `node` or
Linux `/proc` is absent, stop `BLOCKED`; do not silently skip or pass.
Pin Node and Java/JDK versions/hashes as environment evidence.
No automatic rerun of a failed qualification is permitted; DEV repairs must
create a new run ID with all old evidence retained.

1. Fetch the approved isolated branch and verify its exact HEAD and clean
   worktree against the GitHub report. Do **not** checkout in the user's active
   working tree, merge, change source guards, or rewrite protected expected SHA.
2. Capture UTC time, OS/WSL kernel, Python versions, absolute Java/javac/Node
   binary paths + `--version` and binary SHA256, git commit, complete
   19-source protected-file manifest from the existing source guard, and raw
   original/candidate content SHA values. Record before/after identities.
3. Run (with `PYTHONPATH=src:tests:.`, `PYTHONDONTWRITEBYTECODE=1`,
   `-p no:cacheprovider`) `python3.11 -m pytest -q -vv
   tests/test_s49_native_os_custody.py` then separately Python 3.12. Set
   a bounded outer timeout and capture entire stdout/stderr/exit code.
   **4/4 PASS**, **0 FAIL**, **0 SKIP** for each version is required.
4. Verify all fixture PIDs are absent; check no new Java or Node child
   belongs to this test after process exit. Verify repository dirty/untracked
   status, protected originals unchanged **within the run**, logs/checksums,
   source guard still refusing candidate integration as expected.
5. Deliver exact-head receipt plus independent log/source validation to #392
   and #633. If everything above succeeds: `NATIVE_OS_DEV_PASS` *only*,
   retaining `PROTECTED_SOURCE_CHANGE_NO_GO`, `W4_LIVE_NO_GO`,
   `QUALIFICATION_NO_GO` and `SCIENCE_NOT_RUN`.

A returned `CancelledError` alone is insufficient: a native PID must be
identified, reaped and shown gone. An integer `returncode` without a matched
`wait()` and settled original collector is also insufficient.

## Review decision and stops

- All inherited four protected source edits (original S49, S31A, S34 and
  process_session) require **independent owner** evaluation; the 15 untouched
  protected blobs must remain identical to their baseline.
- On cleanup unconfirmed, additional live PID, missing receipt, mismatched
  expected SHA, unexpected child, missing tool, unbounded wait or test failure:
  keep raw evidence, stop NO_GO, do not continue to W4.
- Once reviewed, a **separate** one-time live World permission and W4 exact
  single-receiver/single-action-issuer lease proof are still required.
