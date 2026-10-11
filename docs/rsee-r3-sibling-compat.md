# RSEE R3 — S3 / L1 / V1 pinned source compatibility

Authority: #575 (R owner). Parent R2 #596 exact HEAD `0ab360375a797141e8bc0f2a9c04188a2db9e650`; immutable R1 #593 exact `7c9a013f10e55172f6415deb9002ce7d4417f504`. This is a **single independent R3 Draft**; it does not alter the protected main, Golden #588, S3 #598, L1 #594, V1 #595, or A/B/C.

## Why this milestone

The three lanes remain **unmerged**. S3 retained source-qualified observation Memory through the actual S49 owner and copied L1's existing `experience_bridge.py` with exact Git blob identity. V1 independently tests original-report constraints on its own branch, not the native WSL2 receipts. R2 has a raw evidence handoff envelope, but **no S3 physical original producer has wired a real R1 envelope**. Do not claim otherwise.

R3 checks the *actual* unmerged source branches together in ephemeral CI. It catches source/lock/Profile drift without merging sibling code or installing a separate model/World runtime. It is not another scheduler, action owner, environment, lease, or provenance authority.

## Frozen sibling read-only matrix

| Lane | Exact pinned HEAD | Offline check |
| --- | --- | --- |
| R2 | `0ab360375a797141e8bc0f2a9c04188a2db9e650` | R1/R2 offline source API + test suite |
| S3 #598 | `6f493b7a559dd72ea365998b9eadbd35fd7eb9b4` | original S1 dry-run, focused S3/Experience tests |
| L1 #594 | `40db58d548ea31c4a70acabcc71b0954c7b6ce42` | original bounded Experience bridge tests |
| V1 #595 | `fc76b89638487eadda752e61e9bd7913e67088e5` | original V1 report-only/no-original audit and independent tests |

Five checkouts are separate directories in CI: one R3 verifier plus four frozen R2/S3/L1/V1 sources (not copies of a shared venv). The source checker requires exact Git HEAD, no tracked or untracked drift, and verifies **actual worktree file bytes** by recomputing Git blob hashes for `experiments/standard_env/profile.v1.json`, `adapters/mineflayer/package.json`, `package-lock.json`; the S3/L1 `src/relay_self/experience_bridge.py` blob must also be equal. All these byte identities were independently queried from the specified GitHub HEADs before pinning them in `lane_compat.py`.

Run default pure plan without any host/git/files:

```bash
python -m experiments.standard_env.lane_compat
```

Opt-in local **source-only** inspection (preexisting clean physical checkouts required):

```bash
python -m experiments.standard_env.lane_compat --verify \
  --r-root /absolute/checkout/r3 --s-root /absolute/checkout/s3 \
  --l-root /absolute/checkout/l1 --v-root /absolute/checkout/v1
```

The accepted result `RSEE_R3_PINNED_SOURCE_IDENTITY_MATCH_ONLY` means exactly that: matching **source files** under these specific frozen heads. It does not verify actual physical npm resolution, WSL2 Python interpreter, a live model/GPU/World, backend STOP ACK, resource release, genuine Action outcome or scientific result.

The CI `sibling-readonly` job runs only the preexisting source branches' documented offline/fixture commands in distinct sibling paths. All package installs in CI use ephemeral hosted runners, not the operator's shared environment. In an actual WSL2 source-only audit, reuse the original shared Python and npm root without copying dependencies/model or starting a process. A new/rebased sibling HEAD must be re-audited; never silently replace an exact SHA.

## Boundaries and next integration

S remains responsible for native Action/S16 source and the real `S3ReadOnlyExperience` producer. L's source-qualified Memory hints are not Action authorization. V owns independent scientific comparisons and retains G3 NO-GO. R2 validates a consumer-supplied R1 evidence envelope **only when actual immutable original receipts and independent source expectations exist**. R3 never constructs pseudo-native receipts or retroactively upgrades historical #588 / #597 / #598 claims.

R3 CI is offline compatibility, not an experiment or Golden approval. No Java, Minecraft, Mineflayer actual session, llama-server, GPU inference, LLM POST, World Action, new receipt write, old receipt alteration or package provisioning in the user's RSEE home. Physical per-lane admission remains `NOT_RUN` until an independently authorized operator completes a genuine read-only host audit; real testing requires separate explicit physical authorization.
