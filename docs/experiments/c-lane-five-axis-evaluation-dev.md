# C Lane five-axis evaluation: partial DEV experiment

This draft adds a read-only experimental executor for a qualified settled Stage27h
review frame. It creates five finite `CognitiveTask`s and serial bounded requests
on the existing resident lane. Each receipt retains its task, options, ticket,
provider result and HTTP hashes; the aggregate preserves the chosen option and
its evidence references. The lane and source frame are checked again around
inference. The caller must supply the original accepted CURRENT settled probe.

The choices describe the Target observation, settled WAL, L0 terminal and
uncertainty. A positive recorded displacement offers a movement observation, not
Skill or Goal success. Every axis offers UNKNOWN. The executor neither issues a
physical Action nor adopts a Skill, Intent or Memory.

Axis status distinguishes selected UNKNOWN from an invalid or absent model
selection (UNRESOLVED). An aggregate with any UNRESOLVED axis is not complete;
the other axes and their evidence remain in the aggregate. CANCELLED and STALE
are represented but a fenced execution currently raises HOLD rather than
returning partial receipts.

**Incomplete; not an acceptance or qualification pass.** This experiment does
not recover already-settled rows from an unresolved WAL, demonstrate all requested
adversarial cases, or establish mixed UNKNOWN/UNRESOLVED behavior through
synthetic HTTP. The alternatives are still limited interpretations, not the full
requested range of distinct assessments. Independent CURRENT expiry and partial
receipt retention on interruption need further review. It is not connected to
the original motor hook. No real World or
real Gemma trial is claimed. The synthetic tests exercise the existing resident
lane and HTTP test server; they are not real-model evidence.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
