"""Independent R original-source qualification for ONE new Paper V7 tick-meter BASE_ON.

No physical process, no source mutation. Only a genuine new S QUALIFICATION
producer, correct original bytes, independent same-host process witness and
new grant may pass. Never admits DEV, historical one-shot, other profiles,
V SCIENCE, sub-tick path, or production.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.standard_env import s50_tick_chord_original_audit as chord
from experiments.standard_env import v7_m02_direct_basal_readback as basal
from experiments.standard_env import v7_m02_world_nbt_audit as world

PASS = "R_M02_V7_NEW_BASE_ON_TICK_CHORD_ENGINEERING_QUALIFIED_ONLY"
FAIL = "R_M02_V7_NEW_BASE_ON_QUALIFICATION_FAILED_OR_UNDETERMINED"
GRANT = "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE"
CONFIRM = "M02-V7-TICK-CHORD-BASE-ON-ONE-SHOT"
PINS = {
    "paper-1.21.8.jar": "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e",
    "relay-metabolism-paper-dev.jar": "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f",
    "config.yml": "939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16",
    "server.properties": "11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae",
}
FILES = (
    "paper_server.log", "original_native.jsonl", "owner_commands.jsonl",
    "qualification_producer.json", "initial_world_level.dat",
    "source_plugin.jar", "source_config.yml", "source_server.properties",
    "s50_action_original.jsonl",
)


class NotQualified(ValueError):
    pass


def need(condition: bool, why: str) -> None:
    if not condition:
        raise NotQualified(why)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe(root: Path) -> None:
    need(root.is_absolute() and root.is_dir() and not root.is_symlink()
         and all(not parent.is_symlink() for parent in root.parents),
         "unsafe original root")


def original(root: Path, name: str) -> bytes:
    path = root / name
    need(path.is_file() and not path.is_symlink(),
         "missing/aliased original: " + name)
    data = path.read_bytes()
    # The independently pinned Paper 1.21.8 JAR itself is 52,811,717 bytes.
    # Native text originals remain much smaller; accept the JAR only by digest.
    maximum = 64 * 1024 * 1024 if name == "paper-1.21.8.jar" else 20 * 1024 * 1024
    need(0 < len(data) < maximum, "empty/oversize original: " + name)
    return data


def obj(data: bytes, name: str) -> dict[str, Any]:
    try:
        x = json.loads(data)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise NotQualified("invalid JSON original " + name) from exc
    need(type(x) is dict, "not a source JSON object: " + name)
    return x


def review(root: Path, assets: Path, witness: Path,
           expected_workflow_run_id: str) -> dict[str, Any]:
    safe(root)
    safe(assets)
    need(re.fullmatch("[1-9][0-9]{6,20}", expected_workflow_run_id or "")
         is not None, "no exact current GitHub qualifier run identity")
    need(witness.is_absolute() and witness.is_file()
         and not witness.is_symlink(), "missing separate same-host witness")
    for name in PINS:
        need(sha(original(assets, name)) == PINS[name],
             "candidate admission asset identity mismatch: " + name)
    manifest = original(root, "SHA256SUMS").decode("ascii")
    index: dict[str, str] = {}
    for line in manifest.splitlines():
        m = re.fullmatch("([0-9a-f]{64})  ([a-zA-Z0-9_.-]+)", line)
        need(m is not None and m.group(2) not in index,
             "invalid/duplicate original hash index")
        index[m.group(2)] = m.group(1)
    need(set(index) == set(FILES), "missing/extra original qualification file")
    raw={name: original(root,name) for name in FILES}
    need(all(sha(raw[name]) == index[name] for name in FILES),
         "source originals changed/forged against index")
    need(sha(raw["source_plugin.jar"]) == PINS["relay-metabolism-paper-dev.jar"]
         and sha(raw["source_config.yml"]) == PINS["config.yml"]
         and sha(raw["source_server.properties"]) == PINS["server.properties"],
         "original new Paper JAR or config differs from source asset")
    q=obj(raw["qualification_producer.json"], "qualification_producer")
    need(q.get("classification") ==
         "S_M02_V7_TICK_CHORD_QUAL_SOURCE_CLOSED_R_REVIEW_REQUIRED"
         and q.get("owner") == "S" and q.get("mode") == "QUALIFICATION"
         and q.get("grant_id") == GRANT and q.get("authorization_consumed") is True
         and q.get("retry_count") == 0
         and q.get("java_launch_count") == 1
         and q.get("node_session_count") == 1
         and q.get("new_world") == "NEW_ISOLATED_PAPER"
         and q.get("seed") == "61021"
         and q.get("source_asset_hashes") == PINS
         and q.get("qual_engineering") is False
         and q.get("science_success") is False
         and q.get("v_trials") == 0
         and q.get("production_go") is False
         and q.get("virtual_m0_ledger_used") is False,
         "fresh one-shot S source is not qualified for independent review")
    need(q.get("java_exit") == 0 and q.get("node_exit") == 0
         and q.get("port_released") is True
         and q.get("owned_java_pid_absent") is True
         and q.get("owned_node_pid_absent") is True
         and q.get("owned_world_cleaned") is True,
         "S STOP or cleanup is not closed")
    session=q.get("source_session_id")
    need(type(session) is str and len(session) >= 12
         and re.fullmatch("[0-9a-f]{32}",q.get("run_id","")) is not None,
         "missing new qualification session identity")
    native = [obj(row, "native event") for row in
              raw["original_native.jsonl"].splitlines()]
    commands = [obj(row, "owner command") for row in
                raw["owner_commands.jsonl"].splitlines()]
    need(len(native) >= 10
         and all(x.get("session_id") == session and x.get("seq") == i
                 for i,x in enumerate(native))
         and native[-2].get("type") == "shutdown_ack"
         and native[-1].get("type") == "connection_end"
         and len([x for x in commands if x.get("type") == "shutdown"]) == 1
         and q.get("native_stop_ack_seq") == native[-2]["seq"]
         and q.get("native_connection_end_seq") == native[-1]["seq"],
         "native session chronology/STOP mismatch")
    movement=q.get("movement")
    need(type(movement) is dict and movement.get("action_state") == "outcome"
         and movement.get("source_session") == session,
         "no genuine issued S50 Action and outcome")
    action=movement.get("action_id")
    marker=action+"-"+session if type(action) is str else ""
    need(movement.get("v7_phase_marker_id") == marker,
         "Action/session phase marker not authenticated")
    journal=[obj(row,"Action journal") for row in
             raw["s50_action_original.jsonl"].splitlines()]
    need(len(journal)==2
         and [r.get("state") for r in journal]==["issued","outcome"]
         and all(r.get("action_id")==action
                 and r.get("session_id")==session for r in journal)
         and journal[1].get("events",[])[:-1] == journal[0].get("events")
         and journal[1].get("events",[])[-1].get("state") == "outcome",
         "formal Action journal mismatch")
    for key,aid,effect in (
        ("look_seq",action+"-look","look"),
        ("forward_seq",action,"set_control"),
        ("clear_seq",action+"-clear","clear_controls"),
    ):
        seq=movement.get(key)
        need(type(seq) is int and 0 <= seq < len(native)
             and native[seq].get("type")=="effect_result"
             and native[seq].get("action_id")==aid
             and native[seq].get("effect")==effect
             and native[seq].get("result")=="applied"
             and len([x for x in native if x.get("action_id")==aid
                      and x.get("type")=="effect_result"])==1,
             "native issued control ACK missing/repeated")
        need(len([x for x in commands if x.get("action_id")==aid])==1,
             "unauthorized/duplicate command")
    # S50 MOVE has exactly three motor effects, but this qualification
    # intentionally includes the subsequent S51 real EAT (equip + consume).
    # The earlier DEV-only S50 audit rightfully admits only three effects;
    # this broader QUAL audit must audit *both* sources, not discard S51.
    eat=q.get("eating")
    need(type(eat) is dict and type(eat.get("action_id")) is str,
         "missing S51 action owner")
    eat_id=eat["action_id"]
    expected_effects = [
        (action+"-look", "look"),
        (action, "set_control"),
        (action+"-clear", "clear_controls"),
        (eat_id+"-equip", "equip_item"),
        (eat_id+"-consume", "consume_held"),
    ]
    actual_effects = [(x.get("action_id"),x.get("effect")) for x in commands
                      if x.get("type")=="effect"]
    need(actual_effects == expected_effects,
         "unexpected S50/S51 effect sequence or extra native motor authority")
    for aid,effect in expected_effects[-2:]:
        found=[x for x in native if x.get("type")=="effect_result"
               and x.get("action_id")==aid]
        need(len(found)==1 and found[0].get("effect")==effect
             and found[0].get("result")=="applied",
             "missing/duplicate native S51 equip/consume ACK")
    physical=chord.review_paper_source(raw["paper_server.log"], "BASE_ON",
                                       marker)
    b=basal.review_original_server_log(raw["paper_server.log"],"BASE_ON")
    w=world.review_level_dat(raw["initial_world_level.dat"], expected_seed=61021)
    need(physical["bounded_quiet_window_observed"] is True
         and physical["event_native_double_billing"] is False
         and physical["source_tick_chord_blocks_lower_bound"] > .5
         and abs(physical["source_walk_exhaustion_per_chord_block"]-.01) < 1e-9
         and b["first200_source_player_callbacks"]==200
         and abs(b["direct_source_requested_basal_cumulative_first200"]-.2)<1e-8
         and w["world_seed_from_nbt"]==61021,
         "actual native tick-chord/BASAL/World source invalid")
    ev=q.get("eating")
    need(type(ev) is dict and ev.get("action_state")=="outcome"
         and type(ev.get("native_outcome")) is dict
         and ev["native_outcome"].get("session_id")==session
         and ev["native_outcome"].get("consumed_item")=="cooked_beef"
         and ev["native_outcome"].get("food_after",0)>
         ev["native_outcome"].get("food_before",999),
         "S51 true native EAT not source closed")
    host=obj(original(witness.parent,witness.name),"independent host witness")
    need(host.get("github_run_id")==expected_workflow_run_id
         and host.get("github_run_attempt")==1
         and host.get("java_pid")==q.get("java_pid")
         and host.get("node_pid")==q.get("node_pid")
         and host.get("java_absent") is True
         and host.get("node_absent") is True
         and host.get("loopback_port_released") is True,
         "no independent same-host PID/port closure witness")
    need(all(sha(original(root,k))==index[k] for k in FILES)
         and original(root,"SHA256SUMS").decode("ascii")==manifest,
         "qualification original bytes changed during independent R review")
    return {
        "classification": PASS,
        "scope":"PAPER_1_21_8_NEW_S50_TICK_CHORD_BASE_ON_ONLY",
        "source_new_plugin_sha256":PINS["relay-metabolism-paper-dev.jar"],
        "new_base_config_sha256":PINS["config.yml"],
        "original_sha256":index,
        "source_run_id":q["run_id"],
        "source_session_id":session,
        "github_run_id":expected_workflow_run_id,
        "java_launches":1,"node_sessions":1,"grant_consumed":True,
        "source_basal_first200":b["direct_source_requested_basal_cumulative_first200"],
        "source_tick_chord_lower_bound_blocks":
            physical["source_tick_chord_blocks_lower_bound"],
        "source_walk_setter_input":
            physical["walk_native_exhaustion_setter_input"],
        "actual_tick_writer_rows":physical["native_tick_rows"],
        "source_stop_ack_seq":native[-2]["seq"],
        "independent_host_pid_port_witness":True,
        "candidate_engineering_qualified":True,
        "continuous_subtick_path_qualified":False,
        "all_other_profiles_qualified":False,
        "ecological_survival_qualified":False,
        "science_trials":0,"science_go":False,"production_go":False,
    }


def main() -> int:
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--workflow-run-id", required=True)
    args=parser.parse_args()
    try:
        result=review(args.original_root,args.asset_root,args.witness,
                      args.workflow_run_id)
        status=0
    except (NotQualified, chord.InvalidSource, basal.SourceRejected,
            world.InvalidWorld, ValueError, TypeError, OSError, KeyError,
            AttributeError) as exc:
        result={
            "classification":FAIL,
            "reason":f"{type(exc).__name__}: {exc}",
            "candidate_engineering_qualified":False,
            "science_go":False,"production_go":False,
            "requires_new_grant_if_java_was_started":True,
        }
        status=2
    print(json.dumps(result,sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
