"""I1 opt-in normal original resident CPU loop (DEV; no model/Action).

The original B owner, PatternRegistry, Paper/Native qualification and receiver
remain the only authorities. A restored Self without exploration must stay
without it: an EMPTY SchemaSnapshot means no exploration Need, not OFF evidence.
"""
from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from adapters.mineflayer.sense_projection import SenseFrame
from relay_self.cognitive_minimal_dev import PatternKind, Predicate
from relay_self.i_lane_i1_cpu_schema_probe_dev import prepare_i1_cpu_schema_probe
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
)


class I1NormalRuntimeHold(RuntimeError):
    """A live original source, Schema or CPU epoch was not qualified."""


@dataclass(frozen=True, slots=True)
class I1OriginalCPUEpoch:
    """One read-only, source-referenced original owner CPU cognitive epoch."""

    self_id: str
    native_session_id: str
    native_seq: int
    sense_revision: str
    native_request_id: str | None
    native_observation_ref: str
    paper_tick: int
    paper_tick_source_ref: str
    paper_log_sha256: str
    paper_actor_uuid: str
    resident_epoch: int
    source_revision_refs: tuple[str, ...]
    schema_revision: int
    goal_ids: tuple[str, ...]
    l1_descriptions: tuple[str, ...]
    inquiry_ref: str | None
    model_invoked: bool = False
    action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class I1OriginalCPUResult:
    epochs: tuple[I1OriginalCPUEpoch, ...]
    per_self_counts: tuple[tuple[str, int], ...]
    continuous_native_updates_observed: bool
    model_invoked: bool = False
    action_issue_authorized: bool = False


def prepare_i1_original_schema_bootstrap(
    resident: ResidentCognitiveWorkOwner,
) -> tuple[SchemaSnapshot, ...]:
    """Check BOTH saved Self registries before any in-memory registration.

    A saved exploration pattern permits a matching config-only activation.
    If absent, install *no* exploration. Never bootstrap a new PatternRegistry
    or write a checkpoint to make old Self seem newly exploratory.
    """
    if (not isinstance(resident, ResidentCognitiveWorkOwner)
            or set(resident.owners) != {"A", "B"}):
        raise I1NormalRuntimeHold("original A/B resident owner required")
    with resident.lock:
        snapshots = []
        for sid in ("A", "B"):
            state = resident._states[sid]
            owner = resident.owners[sid]
            if (state.mode != "OFFLINE" or state.epoch != 0
                    or sid in resident._present_schemas or owner.cohort is not resident):
                raise I1NormalRuntimeHold("Schema registration requires fresh offline owner")
            registry = owner.pattern_registry
            explore = [
                p for p in registry.patterns
                if p.schema_id == "exploration" or p.predicate is Predicate.EXPLORE
            ]
            if explore:
                if (len(explore) != 1 or explore[0].schema_id != "exploration"
                        or explore[0].predicate is not Predicate.EXPLORE
                        or explore[0].kind is not PatternKind.GOAL
                        or explore[0].version != 1):
                    raise I1NormalRuntimeHold("unqualified original exploration registration")
                spec = SchemaModuleSpec(
                    "exploratory", 1, frozenset({SchemaMode.FULL}),
                    ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
                    Provenance("innate-schema", "original-saved-exploration-v1"),
                )
                modules = (SchemaActivation(spec, SchemaMode.FULL),)
            else:
                modules = ()
            snapshots.append(SchemaSnapshot(sid, registry.revision, modules))
        return tuple(snapshots)


def install_i1_original_schema_bootstrap(
    resident: ResidentCognitiveWorkOwner,
) -> tuple[SchemaSnapshot, ...]:
    """Install only config on existing original offline owners; no persisted mutation."""
    with resident.lock:
        snapshots = prepare_i1_original_schema_bootstrap(resident)
        for snapshot in snapshots:
            resident.register_present_schema(snapshot.self_id, snapshot)
        return snapshots


def read_i1_original_cpu_epoch(*, bridge, boot, world, links, self_id: str,
                               require_correlated_i1: bool = False) -> I1OriginalCPUEpoch:
    """One synchronous normal CPU epoch from exact current B+E source evidence."""
    resident = bridge.cognitive_work
    if not isinstance(resident, ResidentCognitiveWorkOwner):
        raise I1NormalRuntimeHold("original resident CPU owner missing")
    with resident.lock:
        current = (bridge.current_i1_correlated_sense(self_id)
                   if require_correlated_i1 else bridge.current_sense(self_id))
        if current is None:
            raise I1NormalRuntimeHold("fresh original native SENSE required")
        if require_correlated_i1 and (
            current.observation.kind != "probe"
            or type(current.observation.request_id) is not str
            or re.fullmatch(r"i1-original-sense-[0-9a-f]{32}",
                            current.observation.request_id) is None
        ):
            raise I1NormalRuntimeHold("I1 source not an exact matched original observe reply")
        probe = prepare_i1_cpu_schema_probe(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i1_require_correlated_sense=require_correlated_i1,
        )
        refs = probe.original.source_revision_refs
        if (len(refs) != 3 or refs[-1] != current.source_revision_ref
                or probe.percept.source != current.provenance
                or probe.percept.sequence != current.observation.seq
                or (bridge.current_i1_correlated_sense(self_id)
                    if require_correlated_i1 else bridge.current_sense(self_id)) is not current
                or probe.schema.options or probe.action_issue_authorized
                or probe.model_invoked):
            raise I1NormalRuntimeHold("unqualified / executable native CPU projection")
        return I1OriginalCPUEpoch(
            self_id=self_id,
            native_session_id=current.observation.session_id,
            native_seq=current.observation.seq,
            sense_revision=current.source_revision_ref,
            native_request_id=current.observation.request_id,
            native_observation_ref=current.provenance.reference,
            paper_tick=world.world_tick,
            paper_tick_source_ref=probe.original.present.source.paper_tick_source_ref,
            paper_log_sha256=probe.original.present.source.paper_log_sha256,
            paper_actor_uuid=probe.original.present.source.paper_actor_uuid,
            resident_epoch=probe.original.present.source.resident_epoch,
            source_revision_refs=refs,
            schema_revision=probe.original.present.schema.revision,
            goal_ids=tuple(goal.goal_id for goal in probe.schema.goals),
            l1_descriptions=tuple(text for _, text in probe.l1_proposal.numbered),
            inquiry_ref=(probe.original.coverage_inquiry.question_ref
                         if probe.original.coverage_inquiry is not None else None),
        )


async def sample_i1_original_cpu_epochs(
    *, bridge, boot, world, links, refresh_paper_source: Callable,
    refresh_native_source: Callable[[], Awaitable[dict[str, SenseFrame]]] | None = None,
    timeout_s: float = 5.0, poll_s: float = 0.05,
    per_self_limit: int = 2,
) -> I1OriginalCPUResult:
    """Run a bounded event-driven *read* after real original A/B login.

    Polls E's last frame only; never takes Native receive ownership. For a
    new revision, caller rereads original Paper before B Present admission.
    A zero-update result is HOLD. One baseline epoch per Self is partial;
    two distinct Native revisions each demonstrate continued CPU consumption.
    """
    if (not isinstance(bridge.cognitive_work, ResidentCognitiveWorkOwner)
            or getattr(bridge, "enable_sense", False) is not True
            or not callable(refresh_paper_source)
            or (refresh_native_source is not None and not callable(refresh_native_source))
            or type(per_self_limit) is not int or per_self_limit != 2
            or type(timeout_s) not in (int, float) or not 0 < timeout_s <= 10
            or type(poll_s) not in (int, float) or not 0 < poll_s <= 1
            or poll_s > timeout_s):
        raise I1NormalRuntimeHold("bounded original CPU observation contract required")
    event_loop = asyncio.get_running_loop()
    deadline = event_loop.time() + timeout_s
    last: dict[str, str | None] = {"A": None, "B": None}
    counts = {"A": 0, "B": 0}
    epochs: list[I1OriginalCPUEpoch] = []
    refresh_rounds = 0
    expected_probes: dict[str, SenseFrame] = {}
    while event_loop.time() < deadline and not all(v == per_self_limit for v in counts.values()):
        # Explicit caller-owned read-only Native probes ensure a stationary
        # Self can be reobserved without fabricating passive movement.
        if (refresh_native_source is not None
                and refresh_rounds < per_self_limit
                and all(n == refresh_rounds for n in counts.values())):
            observed_probes = await refresh_native_source()
            if (type(observed_probes) is not dict
                    or set(observed_probes) != {"A", "B"}
                    or any(type(frame) is not SenseFrame for frame in observed_probes.values())):
                raise I1NormalRuntimeHold("original A/B matched observe receipts missing")
            expected_probes = observed_probes
            refresh_rounds += 1
        changed = [
            sid for sid in ("A", "B")
            if counts[sid] < per_self_limit
            and (frame := (
                bridge.current_i1_correlated_sense(sid)
                if refresh_native_source is not None
                else bridge.current_sense(sid)
            )) is not None
            and frame.source_revision_ref != last[sid]
        ]
        if changed:
            # Original Paper owner issues a fresh independent tick/readback
            # and link receipt. Never carry an old link through Paper log growth.
            fresh_world, fresh_links = refresh_paper_source()
            for sid in changed:
                row = read_i1_original_cpu_epoch(
                    bridge=bridge, boot=boot, world=fresh_world,
                    links=fresh_links, self_id=sid,
                    require_correlated_i1=refresh_native_source is not None,
                )
                if refresh_native_source is not None:
                    expected = expected_probes.get(sid)
                    if (expected is None
                            or bridge.current_i1_correlated_sense(sid) is not expected
                            or row.native_request_id != expected.observation.request_id
                            or row.native_seq != expected.observation.seq
                            or row.native_observation_ref != expected.provenance.reference
                            or row.sense_revision != expected.source_revision_ref):
                        failure = I1NormalRuntimeHold(
                            "read-only Native request correlation lost before CPU adoption"
                        )
                        failure.i1_correlated_cpu_readback = {
                            "self_id": sid,
                            "row_request_id": row.native_request_id,
                            "row_native_seq": row.native_seq,
                            "row_sense_revision": row.sense_revision,
                            "expected_request_id": (
                                expected.observation.request_id if expected is not None else None
                            ),
                            "expected_native_seq": (
                                expected.observation.seq if expected is not None else None
                            ),
                            "expected_sense_revision": (
                                expected.source_revision_ref if expected is not None else None
                            ),
                            "diagnostic_only": True,
                            "independent_audit_pass": False,
                        }
                        raise failure
                if row.sense_revision != last[sid]:
                    epochs.append(row)
                    last[sid] = row.sense_revision
                    counts[sid] += 1
        if not all(v == per_self_limit for v in counts.values()):
            await asyncio.sleep(poll_s)
    if not all(counts.values()):
        raise I1NormalRuntimeHold("one or both original Selves lacked qualified SENSE")
    return I1OriginalCPUResult(
        epochs=tuple(epochs),
        per_self_counts=tuple((sid, counts[sid]) for sid in ("A", "B")),
        continuous_native_updates_observed=all(
            v == per_self_limit for v in counts.values()
        ),
    )
