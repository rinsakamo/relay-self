# RelaySelf activity summary

This directory contains the first read-only operator observability surface for
the RelaySelf 1.0 Minecraft MVP.

It is presentation code, not a cognition owner or trace authority.

## Inputs

The reducer reads existing source objects directly:

- decoded Mineflayer messages;
- one existing `IntentCommitment` history;
- existing `SkillExecution` snapshots;
- existing `ActionLifecycle` snapshots;
- optional before/after `PersistentCognition` snapshots.

It does not create a generic event bus or a second lifecycle.

## Movement reduction

Consecutive Mineflayer `move` observations are compacted into bounded movement
spans.

Each span preserves:

- session id;
- first/last sequence;
- source observation count;
- first/last position;
- accumulated path distance;
- displacement;
- first/last source provenance.

A non-movement Mineflayer event closes the current span. Ordinary move spam is
therefore not rendered line by line.

## Separate owner clocks

The summary does not fabricate one universal timeline across unrelated owner
clocks.

Mineflayer source ordering remains session/sequence based. Intent, Skill, and
Action histories remain in their existing owner-local event order.

## Missing evidence

An unsupplied source surface is rendered as `not supplied`.

That is deliberately different from saying that no event occurred.

Likewise, the reducer does not infer threat, danger, fear, success, or other
appraisal labels from target-local Mineflayer facts.

## Persistent Cognition

Durable cognition reporting is a before/after comparison only.

The current slice reports newly retained `Memory` values and preserves both
their source and integration provenance. Existing memories may not be rewritten
or removed by this projection.

## Authority boundary

The generated Markdown is a read-only human view.

It is not:

- Observation or Evidence;
- Belief;
- Memory;
- Current Intent;
- Skill or Action state;
- Action authorization;
- fresh World truth;
- a write path into Persistent Cognition.

If later work wants to retain experience from the underlying evidence, that
must use the governed cognition path rather than the rendered summary text.
