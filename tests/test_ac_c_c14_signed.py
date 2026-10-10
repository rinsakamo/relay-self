"""C14 source-certified negative evidence, missingness and paid verification."""
from dataclasses import replace

import pytest

from experiments.ac_c_c14_signed import (
    ARMS,
    E0,
    MANIFEST_SHA,
    Case,
    FirstReceipt,
    Memory,
    VerifyReceipt,
    World,
    cases,
    decide,
    digest,
    first_viable,
    frozen,
    report,
    trajectory,
    verify_viable,
)


def example(
    session: str, *, z: int=0, blocked: bool=False,
    sensor: bool=True, verify_sensor: bool=True,
    cues: tuple[int,int,int]=(1,0,1),
    health: int=8, deadline: int=7,
    hunger: int=12, threat: bool=False,
) -> Case:
    return Case(
        session,"sensor_drift",0,0,cues,z,blocked,sensor,verify_sensor,
        health,deadline,hunger,threat,
    )


def first(world: World, guess: int=0):
    e=world.e0()
    r=world.consume_first(e,world.issue_first(e,guess))
    return e,r


def test_manifest_is_prequalified_and_seeds_disjoint():
    m=frozen()
    assert digest(m)==MANIFEST_SHA
    assert m["seeds"]["heldout"]==[601,607,613,617,619]
    assert m["seeds"]["calibration"]==[587,593,599]
    assert set(m["seeds"]["heldout"]).isdisjoint(m["seeds"]["calibration"])
    assert m["world"]["normal_moved"]=="not obstructed irrespective of z"


def test_e0_does_not_expose_truth_epoch_or_future_goal():
    c=example("same",z=0,blocked=True,sensor=False)
    d=replace(c,z=1,obstructed=False,first_sensor_visible=True)
    assert World(c).e0()==World(d).e0()
    assert isinstance(World(c).e0(),E0)
    for attr in (
        "epoch","z","hidden_z","obstructed","first_sensor_visible",
        "verify_sensor_visible","correct","goal","goal_status","goal_reached",
    ):
        assert not hasattr(World(c).e0(),attr)


def test_paired_exogenous_sessions_are_opaque_and_reproducible():
    assert cases(601)==cases(601)
    assert cases(601)!=cases(607)
    assert len(cases(601))==5*120
    assert "sensor_drift" not in cases(601)[263].session
    assert "601" not in cases(601)[263].session


def test_blocked_motion_is_nonidentifiable_in_both_latent_states():
    receipts=[]
    for hidden_z in (0,1):
        w=World(example("same",z=hidden_z,blocked=True))
        e,r=first(w,0)
        assert r.goal_status=="UNKNOWN" and not r.moved
        receipts.append(r)
        s=Memory()
        assert w.retain(e,r,None,s,enabled=True,positive_only=False,allow_verify=True)=="UNIDENTIFIED"
        assert s.signature()==(((),()),())
    assert receipts[0]==receipts[1]


def test_moved_without_observed_goal_never_suffices():
    w=World(example("unknown",z=1,blocked=False,sensor=False))
    e,r=first(w,0)
    assert r.moved and r.goal_status=="UNKNOWN"
    s=Memory()
    assert w.retain(e,r,None,s,enabled=True,positive_only=False,allow_verify=True)=="UNIDENTIFIED"
    assert s.signature()==(((),()),())
    assert w.evaluator()["physical_moved_but_wrong"]


def test_reached_proves_executed_z_without_oracle_label():
    w=World(example("positive",z=1,blocked=False,sensor=True))
    e,r=first(w,1)
    assert r.goal_status=="REACHED" and r.moved
    assert not hasattr(r,"z") and not hasattr(r,"hidden_z")
    s=Memory()
    assert w.retain(e,r,None,s,enabled=True,positive_only=False,allow_verify=True)=="POSITIVE"
    assert list(s.group_z[0])==[1]
    assert len(s.cue_counts)==1
    assert w.evaluator()["selected_correct"]


def test_negative_source_proof_identifies_opposite_binary_choice_only():
    w=World(example("negative",z=1,blocked=False,sensor=True))
    e,r=first(w,0)
    assert r.moved and r.goal_status=="NOT_REACHED"
    signed=Memory()
    assert w.retain(
        e,r,None,signed,enabled=True,positive_only=False,allow_verify=False
    )=="NEGATIVE"
    assert list(signed.group_z[0])==[1]
    assert not w.evaluator()["selected_correct"]
    # A POS_ONLY learner on the same exogenous World must abstain on the negative.
    other=World(example("positive_only",z=1,blocked=False,sensor=True))
    e2,r2=first(other,0)
    pos=Memory()
    assert other.retain(
        e2,r2,None,pos,enabled=True,positive_only=True,allow_verify=False
    )=="UNIDENTIFIED"
    assert pos.signature()==(((),()),())


def test_verify_requires_paid_admission_and_consumed_first():
    w=World(example("inspect",z=1,blocked=False,sensor=False))
    e=w.e0()
    issued=w.issue_first(e,0)
    with pytest.raises(ValueError,match="NOT_ADMITTED"):
        w.issue_verify(e,issued)
    r=w.consume_first(e,issued)
    assert verify_viable(e)
    obs=w.issue_verify(e,r)
    assert obs.verified_goal_status=="VERIFIED_NOT_REACHED"
    with pytest.raises(ValueError,match="NOT_ADMITTED"):
        w.issue_verify(e,r)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_verify(e,r,replace(obs))
    assert w.consume_verify(e,r,obs) is obs
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_verify(e,r,obs)
    s=Memory()
    assert w.retain(
        e,r,obs,s,enabled=True,positive_only=False,allow_verify=True
    )=="NEGATIVE"
    assert list(s.group_z[0])==[1]


def test_verify_unknown_is_nonidentifying_and_never_exact():
    w=World(example("unresolved",z=1,sensor=False,verify_sensor=False))
    e,r=first(w,0)
    v=w.consume_verify(e,r,w.issue_verify(e,r))
    assert v.verified_goal_status=="VERIFIED_UNKNOWN"
    s=Memory()
    assert w.retain(
        e,r,v,s,enabled=True,positive_only=False,allow_verify=True
    )=="UNIDENTIFIED"
    assert s.signature()==(((),()),())


def test_verification_is_not_allowed_after_goal_status_known_or_blocked():
    w=World(example("known",z=0,sensor=True))
    e,r=first(w,0)
    with pytest.raises(ValueError,match="NOT_ADMITTED"):
        w.issue_verify(e,r)
    other=World(example("blocked",blocked=True,sensor=False))
    e2,r2=first(other,0)
    with pytest.raises(ValueError,match="NOT_ADMITTED"):
        other.issue_verify(e2,r2)


def test_hard_health_hunger_deadline_bounds():
    good=World(example("g")).e0()
    assert first_viable(good) and verify_viable(good)
    assert not first_viable(replace(good,health=2))
    assert not verify_viable(replace(good,deadline=2))
    assert not verify_viable(replace(good,hunger=2))
    assert not verify_viable(replace(good,threat=True,health=3))
    late=World(example("late",sensor=False,deadline=2))
    e,r=first(late)
    with pytest.raises(ValueError,match="NOT_ADMITTED"):
        late.issue_verify(e,r)


def test_first_receipt_forgery_revision_mode_replay_are_denied():
    w=World(example("id"))
    e=w.e0()
    issued=w.issue_first(e,0)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_first(e,replace(issued))
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_first(replace(e,session="foreign"),issued)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_first(replace(e,revision=1),issued)
    with pytest.raises(ValueError,match="DUPLICATE"):
        w.issue_first(e,0)
    w.consume_first(e,issued)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_first(e,issued)


def test_verify_parent_action_binding_and_retention_single_use():
    w=World(example("ids",z=1,sensor=False))
    e,r=first(w,0)
    v=w.issue_verify(e,r)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_verify(e,r,replace(v,action_bit=1))
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_verify(e,replace(r),v)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.retain(e,r,v,Memory(),enabled=True,positive_only=False,allow_verify=True)
    w.consume_verify(e,r,v)
    s=Memory()
    assert w.retain(
        e,r,v,s,enabled=True,positive_only=False,allow_verify=False
    )=="UNIDENTIFIED"
    with pytest.raises(ValueError,match="REPLAYED"):
        w.retain(e,r,v,s,enabled=True,positive_only=False,allow_verify=True)


def test_first_and_verify_absent_experience_cannot_be_forged():
    w=World(example("untrusted"))
    e=w.e0()
    phantom=FirstReceipt(e.session,digest({"fake":1}),0,True,"REACHED",1)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.retain(e,phantom,None,Memory(),enabled=True,positive_only=False,allow_verify=True)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_first(e,phantom)
    vr=VerifyReceipt(e.session,"forged",0,"VERIFIED_NOT_REACHED",2)
    with pytest.raises(ValueError,match="REPLAYED"):
        w.consume_verify(e,phantom,vr)


def test_warmup_admissible_equal_for_every_policy():
    rr={a:trajectory(601,a) for a in ARMS}
    head=rr[ARMS[0]]
    baseline=[
        (r["session"],r["mode"],r["zguess"],r["label_kind"])
        for r in head["trace"] if r["epoch"]=="warmup"
    ]
    for arm,report_row in rr.items():
        assert report_row["warmup_sig"]==head["warmup_sig"]
        assert [
            (r["session"],r["mode"],r["zguess"],r["label_kind"])
            for r in report_row["trace"] if r["epoch"]=="warmup"
        ]==baseline,arm


def test_frozen_controls_equivalent_and_majority_outputs_ignore_retention():
    f,n=trajectory(601,"FROZEN_GROUP"),trajectory(601,"NO_FEEDBACK_GROUP")
    assert f["phases"]==n["phases"]
    assert [x["zguess"] for x in f["trace"]]==[
        x["zguess"] for x in n["trace"]
    ]
    fm,sm=trajectory(601,"FROZEN_MAJORITY"),trajectory(601,"SIGNED_MAJORITY")
    assert [x["zguess"] for x in fm["trace"]]==[
        x["zguess"] for x in sm["trace"]
    ]


def test_source_no_retention_verification_matches_signed_gate_actions():
    # Verification alone has no immediate physical outcome or free labels.
    a=trajectory(601,"SIGNED_GATE")
    b=trajectory(601,"SIGNED_VERIFY_NO_RETENTION")
    assert [x["zguess"] for x in a["trace"]]==[
        x["zguess"] for x in b["trace"]
    ]


def test_select_does_not_use_evaluator_or_future_world_receipt():
    e=World(example("selection")).e0()
    for arm in ARMS:
        if arm=="EVALUATOR_ORACLE":
            with pytest.raises(ValueError,match="ORACLE"):
                decide(e,Memory(),arm,warmup=False)
        else:
            mode,z=decide(e,Memory(),arm,warmup=False)
            assert mode in ("GROUP","MAJORITY") and z in (0,1)


def test_deterministic_report_all_arm_denominators_and_result_hash():
    r=report()
    assert r==report()
    assert r["result_sha256"]==digest({
        k:v for k,v in r.items() if k!="result_sha256"
    })
    assert set(r["paired"])=={"601","607","613","617","619"}
    for arm in ARMS:
        h=r["summary"]["heldout"][arm]
        assert h["correct"]+h["wrong"]+h["abstain"]==2400
        assert h["positive_cert"]+h["negative_cert"]<=h["correct"]+h["wrong"]
        assert h["verified_resolved"]<=h["verified"]
        assert h["first_positive"]+h["first_negative"]+h["first_unknown"]==h["correct"]+h["wrong"]


def test_emit_machine_result_in_exact_head_ci():
    import json
    import warnings

    r=report()
    warnings.warn("C14_RESULT_JSON "+json.dumps({
        "manifest_sha256":r["manifest_sha256"],
        "result_sha256":r["result_sha256"],
        "heldout":r["summary"]["heldout"],
        "paired":r["paired"],
    },sort_keys=True),UserWarning)
