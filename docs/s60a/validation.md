# S60-A validation history

Frozen prospective manifest committed and posted before implementation:
7cdd55dae77f9b77ff06c6fd3ca129460c44cb9b; SHA256 in manifest.sha256.

First local bootstrap: default `python` unavailable; system python3 had no
pytest/Ruff. Installed pinned pytest 9.1.1/Ruff 0.16.7 in external temporary venv;
no repository dependency or frozen code changed.

First actual focused run: 1 failed, 32 passed. The negative receipt assertion
searched substring ACK, which also matches BACKEND_BUSY/COMPLETION; this is a
fixture assertion defect, not a stop claim. Whole-repository Ruff passed.
The red implementation/test snapshot is retained in Git history. Fix checks
explicit forbidden proof event names without changing acceptance thresholds.

Corrected focused run: 35 passed. Additional checks explicitly reject conversion
of L0 UNKNOWN to a success receipt, verify no task accumulation, and revoke an
active deadline before natural completion. No acceptance thresholds changed.
Whole-repository Ruff, repository contracts, frozen manifest SHA256 and Node 22
protocol checks (33 tests) pass. Full regression and exact-head CI results are
recorded in PR/Issue receipts after their actual completion.
