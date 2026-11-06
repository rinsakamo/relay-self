# Bug-0 D5 R3 — one independent new World after D5-only late cleanup

This document is the exact one-use gate for `.github/workflows/bug0-d5-second-intent-r3-oneworld.yml`. The only change in this trigger commit is this document. Source fix `2c0e65311ab97ad12f90190a40dfa801fbc4cc76` delays operator-only nonzombie cleanup until after native hunger qualification, restores doMobLoot before genuine zombie death, and retains the baseline no-hook D4 path.

Previous R2 real World run #42242338646 failed before first attack because the original native source had multiple nearby entities; immutable original evidence was SHA-verified by read-only run #42243511470. R3 is a *new* World test, never an automatic retry of R2. This workflow must pass its own strict preworld offline checks before starting exactly one new World. No reattempt on failure, no second kill/EAT claim without proof. Same original S49 supervisor only, physical actions bounded, preserve original SHA256 evidence. DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

Trigger: `run-bug0-d5-second-intent-r3-oneworld-once-20261107`
