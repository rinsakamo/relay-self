# R1 native read-side witness correction (new child scope)

Original R1 [run #42051052687](https://github.com/rinsakamo/relay-self/actions/runs/42051052687) failed at the first native probe after an **actual original Paper initial zombie spawn**. It did not reach death/600 tick/second zombie. Original immutable artifact #13427326461 (zip sha256 `63ff6af41e25100e825c6223cd2db37385407f1c968a38d7bcb0e96710577a94`) was read only by #42051530649. Both Node and Java exited0. No previous World is re-run.

The hypothesis is a native registry visibility gap immediately after the Paper initial spawn; this is not established by the first artifact. This child changes only bounded **read-only native observation**: maximum 10 fresh correlated probe requests (600ms apart), retains every unqualified probe's names/counts/source, rejects truncated/multiple/absent zombie, and never asserts a sighting from server-only truth. No new Action issuer, physical API, Self-owned timer or WorldBody physics change. Unique later World requires green preflight, a new trigger, and one run only. Any failure is terminal for that attempt.

Target: #742 / #717. DEV_ONLY / WORLD_NOT_RUN_NEW_CHILD / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
