"""DEV adapter: retain source-audited route episodes in existing Memory owner.

SelfWorld is only a read-only view of this explicit persistent snapshot;
the adapter authenticates RAW source files on every recall and may not issue.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from adapters.mineflayer.s49_l1_experience_export_dev import (
    export_episode_dev,
    load_episode_dev,
)
from relay_self.goal_memory_choice_dev import (
    L1RecallStatusDev,
    make_route_memory_dev,
    select_selfworld_route_dev,
)
from relay_self.goal_navigation import GoalControlRejected, L2GoalProposal
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import SelfWorldView


SCOPE="DEV_STONE_WALL_3WIDE_AT_PLUS_2Z_OPERATOR_CONTEXT"
SELF_ID="s49-dev-episodic-self"


def _read(path:Path)->bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise GoalControlRejected("unsafe original source")
    return path.read_bytes()


def build_selfworld_memory_dev(root:Path)->dict:
    """Two genuine successful source Worlds, one genuine blocked control."""
    if not isinstance(root,Path) or not root.is_dir() or root.is_symlink():
        raise GoalControlRejected("fresh real World root needed")
    audit_a=review(root)  # WALL_STOP + DETOUR
    # REVIEW uses immutable source files; do not relabel a simulated outcome
    # as a second World. DETOUR_B is its own real Java/Node session.
    secondary=root/"SECOND_AUDIT"
    secondary.mkdir(mode=0o700)
    for name,source in (
        ("WALL_STOP",root/"WALL_STOP"/"goal_report.json"),
        ("DETOUR",root/"DETOUR_B"/"goal_report.json"),
    ):
        target=secondary/name
        target.mkdir(mode=0o700)
        shutil.copyfile(source,target/"goal_report.json")
    audit_b=review(secondary)
    if len({
        audit_a["control_session"],audit_a["detour_session"],
        audit_b["detour_session"],
    })!=3 or audit_b["control_session"]!=audit_a["control_session"]:
        raise GoalControlRejected("same World source replayed as independent memory")
    a_path=root/"l1_episode_a.json"
    b_path=secondary/"l1_episode_b.json"
    export_episode_dev(root,a_path)
    export_episode_dev(secondary,b_path)
    episode_a,e_a=load_episode_dev(a_path,root/"DETOUR"/"goal_report.json")
    episode_b,e_b=load_episode_dev(
        b_path,secondary/"DETOUR"/"goal_report.json",
    )
    control_path=root/"WALL_STOP"/"goal_report.json"
    control=json.loads(_read(control_path))
    if (
        control.get("classification")!="DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN"
        or control.get("wall_handoff",{}).get("reason")
           !="MOTOR_CONSEQUENCE_UNDETERMINED"
        or control.get("native_actions",[])[-1].get("s16_terminal")!="unknown"
        or control.get("goal_l2",{}).get("goal_id")!=episode_a.source_goal_id
        or episode_a.source_goal_id!=episode_b.source_goal_id
    ):
        raise GoalControlRejected("failed-source memory is not real wall S16")
    memory=PersistentCognition(
        identity=IdentitySpecification(
            self_id=SELF_ID,
            directives=("Remember source-attributed outcomes only",),
            provenance=Provenance("s49-dev-operator","explicit-self"),
        ),
    )
    memories=(
        make_route_memory_dev(
            memory_id="l1-route-success-a",kind="SUCCESS_ROUTE",
            source_session_id=episode_a.source_session_id,
            source_sha256=e_a["source_report_sha256"],
            fixture_scope=SCOPE,
            goal_offset_x=episode_a.original_goal_offset_x,
            goal_offset_z=episode_a.original_goal_offset_z,
            episode=episode_a,
        ),
        make_route_memory_dev(
            memory_id="l1-route-success-b",kind="SUCCESS_ROUTE",
            source_session_id=episode_b.source_session_id,
            source_sha256=e_b["source_report_sha256"],
            fixture_scope=SCOPE,
            goal_offset_x=episode_b.original_goal_offset_x,
            goal_offset_z=episode_b.original_goal_offset_z,
            episode=episode_b,
        ),
        make_route_memory_dev(
            memory_id="l1-wall-stop-failure",kind="FAILED_BLOCKED",
            source_session_id=control["session_id"],
            source_sha256=hashlib.sha256(_read(control_path)).hexdigest(),
            fixture_scope=SCOPE,
            goal_offset_x=0.0,goal_offset_z=4.0,
            episode=None,
        ),
    )
    for item in memories:
        memory=memory.retain_memory(item)
    path=root/"persistent_self_memory_dev.json"
    save_persistent_cognition(path,memory)
    restored=load_persistent_cognition(path)
    if restored!=memory:
        raise GoalControlRejected("persistent Memory roundtrip lost provenance")
    catalogue={
        "format":"S49_L1_SELF_WORLD_MEMORY_CATALOG_DEV_V1",
        "owner_self_id":SELF_ID,
        "snapshot_sha256":hashlib.sha256(_read(path)).hexdigest(),
        "fixture_scope":SCOPE,
        "source_entries":[
            {"memory_id":"l1-route-success-a",
             "episode_path":"l1_episode_a.json",
             "report_path":"DETOUR/goal_report.json"},
            {"memory_id":"l1-route-success-b",
             "episode_path":"SECOND_AUDIT/l1_episode_b.json",
             "report_path":"DETOUR_B/goal_report.json"},
            {"memory_id":"l1-wall-stop-failure",
             "episode_path":None,
             "report_path":"WALL_STOP/goal_report.json"},
        ],
    }
    cat=root/"selfworld_route_catalog_dev.json"
    cat.write_text(json.dumps(catalogue,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return {
        "snapshot_path":str(path),"catalog_path":str(cat),
        "source_sessions":[
            episode_a.source_session_id,
            episode_b.source_session_id,control["session_id"],
        ],
        "source_count":3,"success_count":2,"failed_blocked_count":1,
        "memory_owner":"PersistentCognition",
        "selfworld_role":"REMEMBERED_READ_ONLY",
    }


def recall_from_selfworld_dev(
    snapshot_path:Path,catalog_path:Path,
    goal:L2GoalProposal,*,start_x:float,start_z:float,
    blocked_action_id:str,blocked_s16_seq:int,
    blocked_reason:str,blocked_terminal:str,
    blocked_consequence:str,
):
    if (
        not isinstance(snapshot_path,Path) or not isinstance(catalog_path,Path)
        or snapshot_path.is_symlink() or catalog_path.is_symlink()
        or snapshot_path.parent!=catalog_path.parent
        or not isinstance(goal,L2GoalProposal)
    ):
        raise GoalControlRejected("SelfWorld requires explicit local saved owner")
    root=snapshot_path.parent
    cat=json.loads(_read(catalog_path))
    owner=load_persistent_cognition(snapshot_path)
    if (
        not isinstance(cat,dict) or set(cat)!={
            "format","owner_self_id","snapshot_sha256",
            "fixture_scope","source_entries",
        }
        or cat["format"]!="S49_L1_SELF_WORLD_MEMORY_CATALOG_DEV_V1"
        or cat["owner_self_id"]!=owner.identity.self_id
        or cat["snapshot_sha256"]!=hashlib.sha256(_read(snapshot_path)).hexdigest()
        or cat["fixture_scope"]!=SCOPE
        or not isinstance(cat["source_entries"],list)
        or len(cat["source_entries"])!=len(owner.memories)==3
        or {e["memory_id"] for e in cat["source_entries"]} !={
            m.memory_id for m in owner.memories
        }
    ):
        raise GoalControlRejected("PersistentCognition source catalog mismatch")
    # Every Memory source digest is compared to its RAW original World file.
    for entry in cat["source_entries"]:
        if (
            not isinstance(entry,dict)
            or set(entry)!={"memory_id","report_path","episode_path"}
            or type(entry["report_path"]) is not str
            or Path(entry["report_path"]).is_absolute()
            or ".." in Path(entry["report_path"]).parts
        ):
            raise GoalControlRejected("unsafe Memory source file reference")
        source=root/entry["report_path"]
        memory=next(m for m in owner.memories if m.memory_id==entry["memory_id"])
        if memory.source_provenance!=Provenance(
            "s49-native-world-report-sha256",hashlib.sha256(_read(source)).hexdigest(),
        ):
            raise GoalControlRejected("governed Memory does not match raw physical source")
        if entry["episode_path"] is not None:
            if (
                type(entry["episode_path"]) is not str
                or Path(entry["episode_path"]).is_absolute()
                or ".." in Path(entry["episode_path"]).parts
            ):
                raise GoalControlRejected("unsafe stored episode reference")
            episode,_=load_episode_dev(root/entry["episode_path"],source)
            if episode.source_session_id not in memory.content:
                raise GoalControlRejected("episode source not in retained Memory")
        else:
            source_report=json.loads(_read(source))
            if (
                source_report.get("classification")!="DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN"
                or source_report.get("stage")!="NEEDS_REPLAN"
                or source_report["native_actions"][-1]["s16_terminal"]!="unknown"
            ):
                raise GoalControlRejected("failure record not original native UNKNOWN")
    view=SelfWorldView(
        self_id=owner.identity.self_id,session_id=goal.session_id,
        epoch_id=f"goal-native-{blocked_s16_seq}",
        observation=None,memories=owner.memories,beliefs=(),
        scenarios=(),forecasts=(),self_body=None,
    )
    selection=select_selfworld_route_dev(
        view,owner,goal,start_x=start_x,start_z=start_z,
        fixture_scope=SCOPE,blocked_action_id=blocked_action_id,
        blocked_s16_seq=blocked_s16_seq,blocked_reason=blocked_reason,
        blocked_terminal=blocked_terminal,
        blocked_consequence=blocked_consequence,
        provenance=Provenance(
            "s49-dev-l1-memory-choice",f"session:{goal.session_id}:seq:{blocked_s16_seq}",
        ),
    )
    return selection
