"""G4.5 native ACK vs sole real Paper/T2 source-order proof bounds."""
import pytest

from adapters.mineflayer.g45_paper_gait_join_dev import join_g45_native_ack_paper_gait_dev


def join(**changes):
    args={
        "session_id":"sess",
        "transition_acks":[{
            "action_id":"goal-a-step-2","parent_s49_issued_action_id":"goal-a-step-2",
            "effect":"g44_gait_transition_dev","applied":True,
            "world_tick_gait_attested":False,"mode_to":"JOG",
            "native_probe_seq":9,"ack_seq":10,
        },{
            "action_id":"goal-a-step-2","parent_s49_issued_action_id":"goal-a-step-2",
            "effect":"g44_gait_transition_dev","applied":True,
            "world_tick_gait_attested":False,"mode_to":"WALK",
            "native_probe_seq":13,"ack_seq":14,
        }],
        "original_clear_acks":[{
            "action_id":"goal-a-step-2","clear_seq":22,"s16_seq":24,
            "s16_terminal":"outcome",
        }],
        "paper_rows":[{
            "session_id":"sess","source_seq":seq,"world_tick":tick,
            "kind":kind,
        } for seq,tick,kind in (
            (11,100,"TRANSITION_OR_UNDETERMINED"),
            (12,101,"STABLE_ORDINARY_FORWARD_CANDIDATE"),
            (15,102,"TRANSITION_OR_UNDETERMINED"),
            (19,103,"STABLE_SNEAK_FORWARD_CANDIDATE"),
        )],
        "t2_rows":[{"source_seq":seq,"world_tick":tick}
                   for seq,tick in ((11,100),(12,101),(15,102),(19,103))],
    }
    args.update(changes)
    return join_g45_native_ack_paper_gait_dev(**args)


def test_g45_source_order_join_without_false_per_tick_claim():
    rows=join()
    assert [v.mode_to for v in rows]==["JOG","WALK"]
    assert [v.stable_matching_world_ticks for v in rows]==[(101,),(103,)]
    assert [v.initial_or_transition_unknown_frames for v in rows]==[1,1]
    assert all(v.paper_stable_candidate_seen for v in rows)
    assert all(not v.packet_to_paper_tick_causality_attested
               and not v.full_tick_gait_attested
               and not v.second_t2_owner_created for v in rows)


def test_g45_missing_stable_frame_is_explicitly_undetermined():
    bad=[{"session_id":"sess","source_seq":11,"world_tick":100,
          "kind":"TRANSITION_OR_UNDETERMINED"}]
    out=join(paper_rows=bad)
    assert out[0].status=="NO_STABLE_FRAME"
    assert out[1].status=="NO_STABLE_FRAME"


@pytest.mark.parametrize("key,bad",[
    ("original_clear_acks",[{"action_id":"goal-a-step-2","clear_seq":14,
                              "s16_seq":24,"s16_terminal":"outcome"}]),
    ("transition_acks",[{"action_id":"goal-a-step-2",
                          "parent_s49_issued_action_id":"other",
                          "effect":"g44_gait_transition_dev","applied":True,
                          "world_tick_gait_attested":False,
                          "mode_to":"JOG","native_probe_seq":9,"ack_seq":10}]),
    ("paper_rows",[{"session_id":"foreign","source_seq":11,
                    "world_tick":100,"kind":"STABLE_ORDINARY_FORWARD_CANDIDATE"}]),
    ("t2_rows",[{"source_seq":11,"world_tick":666}]),
])
def test_g45_rejects_forged_or_unowned_native_paper_sources(key,bad):
    with pytest.raises(ValueError,match="G4.5"):
        join(**{key:bad})
