"""Export *source-attested* first-World L1 route and load it in World 2.

The World 1 original report and a separate wall-only control are audited
before extracting the successful route. The raw report is kept and its
SHA256 cross-checked at recall; no model inference is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.s49_goal_l1_detour_review_dev import review
from relay_self.goal_experience_dev import L1RouteEpisodeDev
from relay_self.goal_navigation import GoalControlRejected


def _safe_read(path:Path)->bytes:
    if (
        not isinstance(path,Path) or path.is_symlink()
        or not path.is_file() or path.stat().st_size>4_000_000
    ):
        raise GoalControlRejected("missing or unsafe original episode file")
    return path.read_bytes()


def export_episode_dev(root:Path, output:Path)->dict:
    """First certify the control/DETOUR World pair, then encode route offsets."""
    if (
        not isinstance(root,Path) or not root.is_dir() or root.is_symlink()
        or not isinstance(output,Path) or output.exists() or output.is_symlink()
        or output.parent!=root
    ):
        raise GoalControlRejected("memory export needs fresh bounded path")
    audit=review(root)
    report_path=root/"DETOUR"/"goal_report.json"
    original=_safe_read(report_path)
    report=json.loads(original)
    route=report["detour"]
    initial=report["initial_native_xz"]
    stages=route["stages"]
    goal=report["goal_l2"]
    if (
        route["original_wall_action_id"]!=report["native_actions"][-1]["action_id"]
        or route["original_wall_S16_after_seq"]
           !=report["wall_handoff"]["native_after_seq"]
        or route["l1_detour_plan"]["source_s16_seq"]
           !=route["original_wall_S16_after_seq"]
        or goal["session_id"]!=report["session_id"]
        or route["original_l2_goal_id"]!=goal["goal_id"]
        or len(stages)!=3
        or any(s["result"]!="REACHED" for s in stages)
        or any(a["S16_status"]!="executed" or a["terminal"]!="outcome"
               for s in stages for a in s["actions"])
    ):
        raise GoalControlRejected("memory source does not prove three stage route")
    episode=L1RouteEpisodeDev(
        source_session_id=report["session_id"],
        source_goal_id=goal["goal_id"],
        source_blocked_action_id=route["original_wall_action_id"],
        source_blocked_after_seq=route["original_wall_S16_after_seq"],
        original_goal_offset_x=float(goal["target_x"]-initial["x"]),
        original_goal_offset_z=float(goal["target_z"]-initial["z"]),
        source_reason=route["l1_detour_plan"]["reason"],
        stages=tuple(
            (s["stage_id"],float(s["target_x"]-initial["x"]),
             float(s["target_z"]-initial["z"]))
            for s in stages
        ),
        source_native_actions=sum(len(s["actions"]) for s in stages),
        source_final_error_m=float(route["final_parent_goal_error_m"]),
        source_final_tolerance_m=float(stages[-1]["tolerance_m"]),
    )
    envelope={
        "format":"RELAYSELF_L1_EPISODIC_DETOUR_DEV_V1",
        "source_report_sha256":hashlib.sha256(original).hexdigest(),
        "source_validation":"TWO_REAL_WORLDS_S16_AUDITED",
        "source_run_classification":audit["classification"],
        "learned_general_policy":False,
        "native_block_sensor":False,
        "episode":asdict(episode),
    }
    output.write_text(
        json.dumps(envelope,indent=2,sort_keys=True)+"\n",encoding="utf8",
    )
    return envelope


def load_episode_dev(memory_path:Path, source_report:Path)->tuple[L1RouteEpisodeDev,dict]:
    if (
        not isinstance(memory_path,Path) or memory_path.is_symlink()
        or not memory_path.is_file() or memory_path.stat().st_size>100_000
    ):
        raise GoalControlRejected("missing local memory artifact")
    envelope=json.loads(memory_path.read_text(encoding="utf8"))
    if (
        not isinstance(envelope,dict)
        or set(envelope)!={
            "format","source_report_sha256","source_validation",
            "source_run_classification","learned_general_policy",
            "native_block_sensor","episode",
        }
        or envelope["format"]!="RELAYSELF_L1_EPISODIC_DETOUR_DEV_V1"
        or envelope["source_validation"]!="TWO_REAL_WORLDS_S16_AUDITED"
        or envelope["source_run_classification"]
           !="S49_L1_NATIVE_DETOUR_ORIGINAL_L2_GOAL_DEV"
        or envelope["learned_general_policy"] is not False
        or envelope["native_block_sensor"] is not False
        or hashlib.sha256(_safe_read(source_report)).hexdigest()
           !=envelope["source_report_sha256"]
    ):
        raise GoalControlRejected("memory provenance/RAW report digest mismatch")
    raw=envelope.get("episode")
    if (
        not isinstance(raw,dict)
        or set(raw)!=set(L1RouteEpisodeDev.__dataclass_fields__)
        or not isinstance(raw["stages"],list)
        or len(raw["stages"])!=3
        or not all(isinstance(s,list) and len(s)==3 for s in raw["stages"])
    ):
        raise GoalControlRejected("untyped L1 memory schema")
    restored=dict(raw)
    restored["stages"]=tuple(tuple(s) for s in raw["stages"])
    episode=L1RouteEpisodeDev(**restored)
    source=json.loads(_safe_read(source_report))
    if (
        source.get("session_id")!=episode.source_session_id
        or source.get("detour",{}).get("original_wall_action_id")
           !=episode.source_blocked_action_id
        or source.get("detour",{}).get("reached_final_goal") is not True
        or source.get("node_exit")!=0
        or source.get("server_exit")!=0
        or source.get("status")!="PASS"
    ):
        raise GoalControlRejected("memorized World origin no longer matches raw report")
    origin=source["initial_native_xz"]
    stages=source["detour"]["stages"]
    if (
        len(stages)!=3 or not math.isclose(
            math.hypot(
                source["detour"]["final_parent_goal_x"]
                    -source["goal_l2"]["target_x"],
                source["detour"]["final_parent_goal_z"]
                    -source["goal_l2"]["target_z"],
            ),episode.source_final_error_m,abs_tol=1e-8,
        )
        or any(
            not math.isclose(
                stage["target_x"]-origin["x"],episode.stages[i][1],
                abs_tol=1e-8,
            ) or not math.isclose(
                stage["target_z"]-origin["z"],episode.stages[i][2],
                abs_tol=1e-8,
            ) or stage["result"]!="REACHED"
            for i,stage in enumerate(stages)
        )
    ):
        raise GoalControlRejected("episode route changed from native stage sources")
    return episode,envelope


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    envelope=export_episode_dev(a.root,a.output)
    print("S49_L1_NATIVE_EPISODE_EXPORTED_DEV",
          json.dumps({
              "memory":str(a.output),
              "source_session":envelope["episode"]["source_session_id"],
              "sha256":envelope["source_report_sha256"],
              "stages":envelope["episode"]["stages"],
          },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
