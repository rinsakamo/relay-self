"""D8 actual B original resident A/B cognitive continuity during new native JOIN.

Strictly READ-ONLY. Requires source-bound D7 candidate plus the original
B recovered Owner objects, actual accepted native probe, live Paper/native
body link and original clear WAL. No inference, L2 replay or physical lease.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.exploration_continuity_dev import open_question_refs
from relay_self.exploration_d7_real_world_preflight_dev import D7SourceCandidate
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.stage28_cognitive_recovery_gate_dev import Stage28NativePaperBodyLink
from relay_self.stage28c2_recovered_resident_owner_dev import Stage28c2aOfflineOwners
from relay_self.world_resident_lifecycle_dev import NativeLoginEvidence, WorldLifetime


class D8OriginalOwnerHold(RuntimeError):
    """D source identity/Question/attempt was lost on real A/B native JOIN."""


@dataclass(frozen=True, slots=True)
class D8OriginalSelfReadback:
    self_id: str
    native_session_id: str
    paper_session_id: str
    current_native_probe_ref: str
    question_refs: tuple[str, ...]
    prior_l2_attempt_refs: tuple[str, ...]
    cognition_sha256: str
    old_l2_replay_authorized: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class D8OriginalOwnerReadback:
    generation_id: str
    paper_session_id: str
    original_self_roster: tuple[str, ...]
    owners: tuple[D8OriginalSelfReadback, ...]
    old_l2_replay_authorized: bool = False
    fresh_l1_run: bool = False
    physical_action_issue_authorized: bool = False


def inspect_d8_original_online_owner(
    recovered: Stage28c2aOfflineOwners,
    candidate: D7SourceCandidate,
    *,
    world: WorldLifetime,
    logins: dict[str, NativeLoginEvidence],
    links: tuple[Stage28NativePaperBodyLink, ...],
) -> D8OriginalOwnerReadback:
    """Requires ORIGINAL B Owner with real new native WorldBody actually adopted."""
    if (
        not isinstance(recovered, Stage28c2aOfflineOwners)
        or not isinstance(candidate, D7SourceCandidate)
        or not isinstance(world, WorldLifetime)
        or type(logins) is not dict
        or type(links) is not tuple
        or set(logins) != {"A", "B"}
        or {x.self_id for x in links
            if isinstance(x, Stage28NativePaperBodyLink)} != {"A", "B"}
        or len(links) != 2
        or any(not isinstance(x, NativeLoginEvidence) for x in logins.values())
        or recovered.plan.generation_id != candidate.generation_id
        or recovered.plan.source_world_id != candidate.world_id
        or recovered.plan.fork_branch_id != candidate.fork_branch_id
        or world.world_id != candidate.world_id
        or world.branch_id != candidate.fork_branch_id
        or not world.paper_session_id.startswith("paper-owned-")
        or tuple(sorted(recovered.owners)) != ("A", "B")
        or tuple(x.self_id for x in candidate.selves) != ("A", "B")
        or not recovered.physical.observation_only
        or recovered.physical.active_action_ids
    ):
        raise D8OriginalOwnerHold("current original A/B Body/World source not qualified")
    by_link = {link.self_id: link for link in links}
    snapshots = []
    try:
        with recovered.cognitive_work.lock:
            for sid, source in zip(("A", "B"), candidate.selves, strict=True):
                owner = recovered.owners[sid]
                login = logins[sid]
                link = by_link[sid]
                epoch, native, w_epoch = recovered.cognitive_work.current_scope(sid)
                obs = owner.current_worldbody_observation
                file = owner.files.cognition_file
                if (
                    owner.cohort is not recovered.cognitive_work
                    or owner.self_id != sid
                    or not isinstance(obs, MineflayerObservation)
                    or obs.kind != "probe"
                    or obs.session_id != native
                    or obs.request_id != login.observation_ref
                    or not obs.request_id
                    or owner.fresh_native_observation_required
                    or owner.native_session_id != native
                    or login.native_session_id != native
                    or login.world_id != world.world_id
                    or login.branch_id != world.branch_id
                    or login.paper_session_id != world.paper_session_id
                    or login.world_epoch != w_epoch
                    or world.epoch != w_epoch
                    or type(epoch) is not int or epoch < 1
                    or link.native_session_id != native
                    or link.paper_session_id != world.paper_session_id
                    or link.native_probe_ref != obs.request_id
                    or link.native_world_time_tick != login.observed_world_tick
                    or obs.snapshot.time is None
                    or owner.last_observed_tick != (
                        obs.snapshot.time.day * 24000
                        + obs.snapshot.time.time_of_day
                    )
                    or file.is_symlink()
                    or file != owner.files.self_root / "cognition.json"
                    or not file.is_file()
                ):
                    raise D8OriginalOwnerHold("original A/B native probe or epoch differs")
                cognition = load_persistent_cognition(file)
                if (
                    cognition != owner.retained
                    or cognition.identity.self_id != sid
                    or (cognition.pattern_registry is not None
                        and cognition.pattern_registry != owner.pattern_registry)
                ):
                    raise D8OriginalOwnerHold("canonical original cognition differs")
                question_refs = open_question_refs(
                    cognition, expected_self_id=sid,
                )
                state = cognition.exploration_continuity
                attempts = (
                    () if state is None
                    else tuple(a.attempt_ref for a in state.attempts)
                )
                if (
                    question_refs != source.question_refs
                    or attempts != source.attempt_refs
                    or not set(question_refs).issubset(owner.pending_questions)
                ):
                    raise D8OriginalOwnerHold(
                        "D OPEN Question / L2 history changed on native JOIN"
                    )
                PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=sid,
                ).require_clear()
                snapshots.append(D8OriginalSelfReadback(
                    sid, native, world.paper_session_id,
                    obs.request_id, question_refs, attempts,
                    hashlib.sha256(file.read_bytes()).hexdigest(),
                ))
    except D8OriginalOwnerHold:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        raise D8OriginalOwnerHold(
            "original resident cognition/WAL/body source unreadable"
        ) from exc
    return D8OriginalOwnerReadback(
        candidate.generation_id, world.paper_session_id,
        ("A", "B"), tuple(snapshots),
    )
