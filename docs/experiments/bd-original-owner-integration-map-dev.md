# B+D original-owner integration map (DEV preparation)

This is a compatibility map, not an integration or evidence of a World run.
The B baseline is `a552e7b5592053e125071be5ea8903ddeb1aadbb`; the D
reference is `0eb3dc88b5cfa6326b3666642c95077c178a35c6`. Their histories
diverge, so a branch merge or wholesale replacement of B files is unsafe.

| Responsibility | Authoritative B seam | D material to adapt |
| --- | --- | --- |
| Per-Self state and mutation | `CheckpointedCognitiveOwner`, gated by `ResidentCognitiveWorkOwner` | Question, Goal and attempt transitions under the original resident lock and epoch |
| GPU and bounded L1 | `ResidentLlamaInferenceLane` and `stage28c2c_fresh_recovered_l1_dev` | Source-qualified exploration candidates, preserving actual numbered selection including DEFER |
| Durable cognition | Original `cognition.json`, read back against the owner | `exploration_continuity_dev` and guarded updates in `exploration_checkpoint_bridge_dev` |
| Checkpoint | B cohort freeze, typed World/Self generation and original WAL | OPEN Question references and inert attempt records in the same generation |
| Restore | B staged recovery, fresh Paper/native admission and new observation | Restore historical records only; never reuse an old L1 result or dispatch an old reservation |

## Format compatibility

B persistent cognition writes schema 2 and reads schemas 1 and 2. D reads
those versions but additionally uses schema 3 for its registry and opt-in
schema 4 for exploration continuity. B typed SelfOwnerCut writes and reads
schema 1, whose registry contains only revision and patterns. D5's typed cut
uses schema 2 only when accepted Presets exist, with a strict Self-bound
registry codec. D's `PatternRegistry` also has accepted Presets and depends
on its skill invocation types; B's type does not. The codec therefore cannot
be copied alone. Preserve B schema 1 serialization and existing checkpoint
readback, explicitly reject foreign Self bindings, and test cross-file
registry and OPEN Question consistency before generation commit. Do not
silently drop Presets or change the provenance of B's existing evidence.

## Real-run regression boundaries

The D11 real attempts each stopped before L1 POST. The latest D reference
addresses three distinct failures: function-local `hashlib` imports shadowing
the module binding; calling the Paper post-QUIT gate before A actually QUIT;
and failing to persist and read back both initial owner cognition files before
source admission. Integrated regression tests must exercise B's actual runner
order and canonical files, including duplicate and stale source rejection.
Passing those tests does not turn those prior HOLDs into successful runs.

## Remaining gates

No exploration integration is established by this document. Implementation
still needs explicitly registered exploration Schema, source-bound Present and
Goal generation, resident-locked durable Question/attempt transitions,
schema-compatible typed cut and restore, and adversarial epoch/identity/WAL
coverage. Only after offline checks and exact-HEAD CI may a separate exclusive
one-shot World and locally owned Gemma DEV run provide new evidence. No
physical action, actual L2 inference, C learning, QUAL or SCIENCE is granted
by this preparation.
