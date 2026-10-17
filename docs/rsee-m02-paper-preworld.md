# RSEE M0.2 — separate Paper 1.21.8 preworld profile

**Status: OFFLINE_ASSET_ADMISSION_IMPLEMENTED; NEW_PAPER_WORLD_NOT_RUN.**

Authority: R #575/#610, S #537/#545, M #616/#617, V #619.
This is a NEW Paper profile, not a replacement for protected Mojang Golden
#588 or its completed B0 engineering qualification.

- Contract: `experiments/standard_env/m02_paper_preworld_profile.json`
- Pure offline checker: `experiments/standard_env/m02_paper_preworld.py`
- Synthetic negatives: `tests/test_rsee_m02_paper_preworld.py`

The profile pins the Paper 1.21.8 JAR, plugin JAR, Paper plugin config,
and isolated server.properties byte SHA256, plus S/M source identity, historical
source artifact and archived R readback. It rejects unknown versions, broken
digests, missing/extra assets, symlinks, source changes and promotion flags.

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
# No-I/O default; never a launch authorization:
python -m experiments.standard_env.m02_paper_preworld
# Only when four exact candidate assets have been staged offline:
python -m experiments.standard_env.m02_paper_preworld \
  --asset-root /ABSOLUTE/NEW/ISOLATED/FOUR-FILE-ASSET-ROOT
```

The four files in the isolated directory must be named
`paper-1.21.8.jar`, `relay-metabolism-paper-dev.jar`,
`config.yml`, and `server.properties`. Do not substitute a Mojang
Golden JAR or mutate source to match pins. A successful asset-only check
returns `M02_PAPER_ASSETS_PINNED_PREWORLD_REVIEW_ONLY`, explicitly
`qualified=false` and `new_physical_qualification_authorized=false`.
Without staged bytes the current result remains
`M02_PAPER_PREWORLD_ASSETS_UNCHECKED`.

R's authenticated real DEV archive readback is available at:
https://github.com/rinsakamo/relay-self/actions/runs/38696894732/artifacts/11954211513
(expires 2027-01-13). The original S 7-day artifact expires
2026-10-22. No original file was modified.

**Important physical-source correction:** the published command-stream hash
was missing five characters; the independently fetched 64-character SHA256 is
`d81b0242a8ab7a68faf1ba8d6b845c3f3bc3f27e19598a96716c247d456d2fb0`.
Independent readback of 97 native rows and 9 genuine motion packets
confirmed 1.2828913533098643 blocks and 0.012828913533098642 exhaustion.
This is still an **old DEV** result, not a fresh R engineering qualification.

The next admission must additionally validate a newly owned Paper
world snapshot / seed, actual runtime JDK+Node dependencies, original source
lineage and live STOP/PID/port cleanup. Fresh user authorization is required
before any **new R QUALIFICATION Java start**. The prior B0 grant is consumed;
no science or production claim follows from this document. BASAL/WALK ecology
coefficients remain uncalibrated.
