"""DEV L1 choice from governed Memory exposed as SelfWorld REMEMBERED.

SelfWorld is a read-only epoch view; only PersistentCognition retains records.
Neither memory nor this chooser issues Actions or asserts current block perception.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from enum import Enum

from relay_self.goal_experience_dev import (
    L1RouteEpisodeDev,
    select_route_from_episode_dev,
)
from relay_self.goal_navigation import GoalControlRejected, L2GoalProposal
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import SelfWorldView, WorldOrigin


class L1RecallStatusDev(str, Enum):
    SELECTED = "SELECTED"
    DEFER = "DEFER"


@dataclass(frozen=True, slots=True)
class L1RouteRecallDev:
    status: L1RecallStatusDev
    reason: str
    matching_successes: int
    matching_failures: int
    selected_memory_id: str | None
    source_ids: tuple[str, ...]
    plan: object | None


def make_route_memory_dev(
    *,memory_id:str,kind:str,source_session_id:str,
    source_sha256:str,fixture_scope:str,goal_offset_x:float,
    goal_offset_z:float,episode:L1RouteEpisodeDev|None,
) -> Memory:
    if (
        type(memory_id) is not str or not memory_id
        or kind not in ("SUCCESS_ROUTE","FAILED_BLOCKED")
        or type(source_session_id) is not str or not source_session_id
        or type(source_sha256) is not str or len(source_sha256)!=64
        or any(c not in "0123456789abcdef" for c in source_sha256)
        or type(fixture_scope) is not str or not fixture_scope
        or any(type(x) is not float or not math.isfinite(x)
               for x in (goal_offset_x,goal_offset_z))
        or (kind=="SUCCESS_ROUTE")!=(isinstance(episode,L1RouteEpisodeDev))
        or (episode is not None and (
            episode.source_session_id!=source_session_id
            or not math.isclose(episode.original_goal_offset_x,goal_offset_x,abs_tol=1e-8)
            or not math.isclose(episode.original_goal_offset_z,goal_offset_z,abs_tol=1e-8)
        ))
    ):
        raise GoalControlRejected("memory requires bounded externally source-audited episode")
    data={
        "kind":kind,"fixture_scope":fixture_scope,
        "source_session_id":source_session_id,
        "source_sha256":source_sha256,
        "goal_offset_x":goal_offset_x,"goal_offset_z":goal_offset_z,
        "episode":asdict(episode) if episode is not None else None,
    }
    return Memory(
        memory_id=memory_id,
        content=json.dumps(data,sort_keys=True,separators=(",",":")),
        source_provenance=Provenance("s49-native-world-report-sha256",source_sha256),
        integration_provenance=Provenance(
            "s49-dev-memory-integration",f"retain:{memory_id}",
        ),
    )


def _read(memory:Memory) -> tuple[dict,L1RouteEpisodeDev|None]:
    try:
        value=json.loads(memory.content)
        if not isinstance(value,dict) or set(value)!={
            "kind","fixture_scope","source_session_id","source_sha256",
            "goal_offset_x","goal_offset_z","episode",
        } or memory.source_provenance!=Provenance(
            "s49-native-world-report-sha256",value["source_sha256"],
        ) or memory.integration_provenance!=Provenance(
            "s49-dev-memory-integration",f"retain:{memory.memory_id}",
        ):
            raise ValueError("source lineage")
        raw=value["episode"]
        episode=None
        if raw is not None:
            if not isinstance(raw,dict) or set(raw)!=set(
                L1RouteEpisodeDev.__dataclass_fields__
            ) or not isinstance(raw["stages"],list):
                raise ValueError("episode schema")
            fields=dict(raw)
            fields["stages"]=tuple(tuple(s) for s in raw["stages"])
            episode=L1RouteEpisodeDev(**fields)
        _ = make_route_memory_dev(
            memory_id=memory.memory_id,kind=value["kind"],
            source_session_id=value["source_session_id"],
            source_sha256=value["source_sha256"],
            fixture_scope=value["fixture_scope"],
            goal_offset_x=value["goal_offset_x"],
            goal_offset_z=value["goal_offset_z"],episode=episode,
        )
        return value,episode
    except (ValueError,KeyError,TypeError) as exc:
        raise GoalControlRejected("untrusted remembered route content") from exc


def select_selfworld_route_dev(
    view:SelfWorldView, cognition:PersistentCognition,
    goal:L2GoalProposal, *,start_x:float,start_z:float,
    fixture_scope:str,blocked_action_id:str,blocked_s16_seq:int,
    blocked_reason:str,blocked_terminal:str,
    blocked_consequence:str,provenance:Provenance,
) -> L1RouteRecallDev:
    """Select only one unambiguous source-attested route template.

    Every Memory is read through SelfWorld REMEMBERED. Current World/Goal
    geometry and the new native blocked motor remain independently required.
    """
    if (
        not isinstance(view,SelfWorldView)
        or not isinstance(cognition,PersistentCognition)
        or view.self_id!=cognition.identity.self_id
        or view.session_id!=goal.session_id
        or view.memories!=cognition.memories
        or len(view.memories)>8
        or not isinstance(fixture_scope,str) or not fixture_scope
        or not isinstance(provenance,Provenance)
        or provenance.source=="mineflayer"
        or type(start_x) is not float or type(start_z) is not float
        or not math.isfinite(start_x) or not math.isfinite(start_z)
        or not view.epoch_id
    ):
        raise GoalControlRejected("read-only SelfWorld identity/epoch boundary missing")
    eligible=[]
    failures=0
    ids=[]
    seen_sessions=set()
    for memory in view.memories:
        reading=view.remembered(memory.memory_id)
        if (
            reading.origin is not WorldOrigin.REMEMBERED
            or reading.value!=memory
            or reading.source_provenance!=(
                memory.source_provenance,memory.integration_provenance,
            )
        ):
            raise GoalControlRejected("unbound SelfWorld REMEMBERED source")
        item,episode=_read(memory)
        if item["source_session_id"] in seen_sessions:
            raise GoalControlRejected("duplicate World source masquerades as independent")
        seen_sessions.add(item["source_session_id"])
        if item["source_session_id"]==goal.session_id:
            continue
        if (item["fixture_scope"]!=fixture_scope or
            not math.isclose(item["goal_offset_x"],goal.target_x-start_x,abs_tol=1e-8)
            or not math.isclose(item["goal_offset_z"],goal.target_z-start_z,abs_tol=1e-8)):
            continue
        ids.append(memory.memory_id)
        if item["kind"]=="FAILED_BLOCKED":
            failures+=1
            continue
        assert episode is not None
        try:
            plan=select_route_from_episode_dev(
                episode,goal,start_x=start_x,start_z=start_z,
                blocked_action_id=blocked_action_id,
                blocked_s16_seq=blocked_s16_seq,
                blocked_reason=blocked_reason,
                blocked_terminal=blocked_terminal,
                blocked_consequence=blocked_consequence,
                provenance=provenance,
            )
        except GoalControlRejected:
            continue
        signature=tuple(
            (stage_id,round(dx,5),round(dz,5))
            for stage_id,dx,dz in episode.stages
        )
        eligible.append((memory.memory_id,episode,plan,signature))
    if not eligible:
        return L1RouteRecallDev(
            L1RecallStatusDev.DEFER,"NO_ELIGIBLE_REMEMBERED_ROUTE",
            0,failures,None,tuple(ids),None,
        )
    signatures={s for _,_,_,s in eligible}
    if len(signatures)!=1:
        return L1RouteRecallDev(
            L1RecallStatusDev.DEFER,"CONFLICTING_RECALLED_ROUTES",
            len(eligible),failures,None,tuple(ids),None,
        )
    # Deterministic preference only among equivalent geometries. Never
    # assign confidence to an unobserved wall or unknown route.
    selected=min(
        eligible,
        key=lambda x:(x[1].source_native_actions,x[1].source_final_error_m,x[0]),
    )
    return L1RouteRecallDev(
        L1RecallStatusDev.SELECTED,"MATCHED_REMEMBERED_PATTERN",
        len(eligible),failures,selected[0],tuple(ids),selected[2],
    )
