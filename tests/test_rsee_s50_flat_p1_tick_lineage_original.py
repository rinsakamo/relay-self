"""R-independent FLAT native World tick/P1 candidate originals and negatives."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.standard_env import s50_flat_p1_tick_lineage_original_audit as r


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp_path: Path):
    root=tmp_path/"s-original"
    root.mkdir()
    arms={}
    for arm in r.ARMS:
        dest=root/arm
        dest.mkdir()
        world="bba420a8-7943-465f-997e-e857e7587b93"
        walk=0 if arm in ("WALK_ZERO","BOTH_ZERO") else 1
        expected=(
            (1,22,0.5,0.7,0.2),
            (2,23,0.7,1.0,0.3),
        )
        lines=[]
        total=0.0
        total_billed=0.0
        for n,t,x0,x1,blocks in expected:
            total+=blocks
            billed=blocks*0.01*walk
            total_billed+=billed
            lines.append(
                "Native M02_DEV_MOTION "
                f"id={n} reason=WALK blocks={blocks} billed={billed} "
                f"cumulative_blocks={total} cumulative_billed={total_billed} "
                f"from_x={x0} from_z=0.5 to_x={x1} to_z=0.5 "
                f"world_full_time={t} world={world} marker_id=dev"
            )
        console=("\n".join(lines)+"\n").encode()
        report={
            "arm":arm,"status":"PASS","mode":"FLAT_DEV_ONLY",
            "cleanup_complete":True,
            "initial_server_marker":{
                "world":world,"seed":"63101","full_time":"20",
            },
            "terminal_server_marker":{
                "world":world,"seed":"63101","full_time":"25",
                "motion_blocks":str(total),
            },
        }
        report_raw=json.dumps(report).encode()
        manifest={"report.json":sha(report_raw),"paper_server.log":sha(console)}
        (dest/"report.json").write_bytes(report_raw)
        (dest/"paper_server.log").write_bytes(console)
        (dest/"sha256.json").write_text(json.dumps(manifest))
        timeline=[]
        for tick in range(21,26):
            if tick in (22,23):
                blocks=0.2 if tick==22 else 0.3
                timeline.append({
                    "world_full_time":tick,
                    "activity":"MOVE_EVENT_OBSERVED_NOT_FULL_TICK_ADMITTED",
                    "event_count":1,"native_horizontal_blocks":blocks,
                    "P1_hypothetical_gain_not_admitted":blocks*0.04,
                    "P1_frame_issued":False,
                })
            else:
                timeline.append({
                    "world_full_time":tick,
                    "activity":"UNKNOWN_NOT_WAIT","event_count":0,
                    "native_horizontal_blocks":None,
                    "P1_hypothetical_gain_not_admitted":None,
                    "P1_frame_issued":False,
                })
        transitions=[]
        f=0.0
        for tick,blocks in ((22,0.2),(23,0.3)):
            before=f
            f+=blocks*0.04
            transitions.append({
                "world_tick":tick,
                "real_movement_candidate_blocks":blocks,
                "hypothetical_fatigue_before":before,
                "hypothetical_fatigue_after":f,
                "hypothetical_recovered":0.0,
            })
        arms[arm]={
            "source":{
                "arm":arm,"classification":
                "S_FLAT_P1_MOTION_SOURCE_CANDIDATE_DEV_ONLY",
                "world":world,"original_report_sha256":manifest["report.json"],
                "original_console_sha256":manifest["paper_server.log"],
                "start_full_time":20,"terminal_full_time":25,
                "native_motion_events":2,
                "native_observed_horizontal_blocks":0.5,
            },
            "tick_lineage":{
                "classification":"S_FLAT_P1_WORLD_TICK_LINEAGE_CANDIDATE_DEV_ONLY",
                "world":world,"arm":arm,"start_full_time":20,
                "terminal_full_time":25,
                "ticks":timeline,"move_observed_ticks":2,
                "unclassified_ticks":3,
                "SourceBoundTick_MOVE_issued":0,
                "SourceBoundTick_WAIT_issued":0,
                "P1_wait_recovery":0.0,"P1_state_advanced":False,
            },
            "P1_preview":{
                "classification":
                "S_P1_FLAT_CROSS_BRANCH_MOTION_ONLY_PREVIEW_NOT_ADMITTED",
                "arm":arm,"world":world,"P1_owner_profile_sha256":"0"*64,
                "native_move_tick_candidates":2,"unknown_tick_count":3,
                "windows":[{
                    "first_world_tick":22,"last_world_tick":23,
                    "candidate_ticks_replayed":2,
                    "transitions":transitions,
                    "conflict":None,
                    "lineage_reset_at_unknown_gap":True,
                    "authoritative_body_state_updated":False,
                    "hypothetical_window_end_fatigue":f,
                }],
                "P1_World_SourceBoundTick_issued":0,
                "P1_authoritative_state_advanced":False,
                "P1_wait_recovery":0.0,
                "cap_conflicts":0,"M02_energy_ledger_writes":0,
            },
        }
    receipt={
        "classification":r.EXPECTED_DERIVED_CLASS,
        "S_physical_original_run":r.ORIGINAL_RUN,
        "S_physical_original_head":r.ORIGINAL_HEAD,
        "S_artifact_zip_sha256":r.ORIGINAL_DIGEST,
        "P1_owner_commit":r.P1_OWNER_HEAD,
        "P1_actual_body_state_advanced":False,
        "P1_WAIT_recovery":0.0,
        "source_activity_full_tick_qualified":False,
        "science_trials":0,"R_independent_review":"PENDING",
        "arms":arms,
    }
    deriv=tmp_path/"derived.json"
    deriv.write_text(json.dumps(receipt))
    return root, deriv, receipt


def test_independent_native_source_and_unknown_ticks(tmp_path):
    root,derived,receipt=fixture(tmp_path)
    result=r.audit(root,derived)
    assert result["audit_status"]=="PASS"
    assert len(result["arms"])==4
    assert all(x["move_observed_ticks"]==2
               and x["unknown_ticks"]==3
               and x["real_source_bound_wait_ticks"]==0
               for x in result["arms"])
    assert not result["P1_actual_fatigue_state_updated"]
    assert result["P1_recovered"]==0.0


@pytest.mark.parametrize("mutate", [
    lambda x: x.update(S_physical_original_run=38994504184),
    lambda x: x.update(P1_owner_commit="bad"),
    lambda x: x.update(source_activity_full_tick_qualified=True),
    lambda x: x.update(P1_WAIT_recovery=0.1),
    lambda x: x["arms"]["SHAM_ON"]["tick_lineage"]["ticks"][0].update(activity="WAIT"),
    lambda x: x["arms"]["SHAM_ON"]["tick_lineage"]["ticks"][1].update(
        native_horizontal_blocks=0.0),
    lambda x: x["arms"]["SHAM_ON"]["tick_lineage"]["ticks"][1].update(
        P1_frame_issued=True),
    lambda x: x["arms"]["SHAM_ON"]["tick_lineage"].update(
        P1_state_advanced=True),
    lambda x: x["arms"]["SHAM_ON"]["P1_preview"].update(
        P1_wait_recovery=0.1),
    lambda x: x["arms"]["SHAM_ON"]["P1_preview"]["windows"][0][
        "transitions"][0].update(hypothetical_fatigue_before=0.1),
    lambda x: x["arms"]["SHAM_ON"]["P1_preview"]["windows"][0].update(
        first_world_tick=21),
    lambda x: x["arms"]["SHAM_ON"]["source"].update(
        original_report_sha256="0"*64),
    lambda x: x["arms"].pop("BOTH_ZERO"),
])
def test_forged_admission_free_recovery_or_tampered_source_fails(tmp_path,mutate):
    root,derived,receipt=fixture(tmp_path)
    forged=copy.deepcopy(receipt)
    mutate(forged)
    derived.write_text(json.dumps(forged))
    with pytest.raises((ValueError,KeyError,TypeError)):
        r.audit(root,derived)


def test_modified_native_paper_original_or_symlink_rejected(tmp_path):
    root,derived,_=fixture(tmp_path)
    original=root/"SHAM_ON"/"paper_server.log"
    original.write_bytes(original.read_bytes()+b"extra\n")
    with pytest.raises(ValueError,match="digest"):
        r.audit(root,derived)
    original.unlink()
    original.symlink_to(root/"BASAL_ZERO"/"paper_server.log")
    with pytest.raises(ValueError):
        r.audit(root,derived)
