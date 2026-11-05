# Corrective offline-only replay — 2026-11-05

Original two Paper Worlds are fixed and immutable:
- high REST original run 41947095526 (one ATTACK, one L0 REST,
  java/node exit0; former post-world analysis parser rejected a
  new-format CHOICE REST marker);
- low WAIT original run 41927124487 (one ATTACK, L0 WAIT,
  java/node exit0).

First read-only pairing run 41947580969 successfully downloaded
and SHA256-checked both source artifact sets, then stopped at
ModuleNotFoundError('pytest') from an existing imported S49 test
module. There is no additional physical World execution.

This correction installs only the pinned Python-only import
dependency pytest 9.1.1 inside the replay-only CI before rerunning
the original-P1 source-bound retrospective comparisons. No Paper,
Java server, Mineflayer, original S49 owner, attack, REST Action,
P1 live runtime, M energy, learning or source rewriting is allowed.

The pinned original P1 evaluation logic remains unchanged. Two
independently original World sources remain DISTINCT in session
and World UUID, so this tests conditional decision behavior
under separate, explicit *virtual* fatigue-rate hypotheses.
Source full-tick R certification and real physiological fatigue
remain unattested; QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
