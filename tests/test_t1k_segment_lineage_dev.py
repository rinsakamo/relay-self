"""T1k two independent provisional M0/P1 epochs; no hidden STOP gap fill."""
from adapters.mineflayer.t1j_resume_accounting_dev import rebase_tick_accounting_dev
from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevPermit
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from test_t1f_t2_dev import frame


def grant(n, after, previous):
    return ResumeDevPermit(
        resume_id=f"T1J-R{n}", stop_id=f"STOP{n}", session_id="test-session",
        next_action_id=f"t1j-T1J-R{n}-move",
        world=after.data["snapshot"]["world"],
        player=after.data["snapshot"]["player"],
        old_stop_ack_last_server_tick=previous.data["snapshot"]["tick"],
        before_source_seq=previous.seq + 1,
        after_source_seq=after.seq,
        native_probe_seq=previous.seq + 2,
        after_world_tick=after.data["snapshot"]["world_tick"],
        unobserved_world_ticks=(after.data["snapshot"]["world_tick"]
                                - previous.data["snapshot"]["world_tick"] - 1),
    )


def test_two_resume_segments_keep_both_stopped_ledgers_and_credits_unchanged():
    original = TickAccounting("test-session")
    original.observe(frame(1))
    original.observe(frame(2))
    original.energy._credits.add("t2-native-meal")  # synthetic prior verified ID
    old_rows = list(original.rows)
    old_energy = original.energy.body
    old_fatigue = original.fatigue
    original.failed = True
    original.t1j_resumed_stop_id = "STOP1"

    first_baseline = frame(10)
    first_grant = grant(1, first_baseline, original.previous)
    first = rebase_tick_accounting_dev(
        original, baseline=first_baseline, permit=first_grant)
    first.observe(frame(11))
    first_rows = list(first.rows)
    first_energy = first.energy.body
    first_fatigue = first.fatigue
    first.failed = True
    first.t1j_resumed_stop_id = "STOP2"

    second_baseline = frame(20)
    second_grant = grant(2, second_baseline, first.previous)
    second = rebase_tick_accounting_dev(
        first, baseline=second_baseline, permit=second_grant)
    second.observe(frame(21))

    assert original.failed and original.rows == old_rows
    assert original.energy.body == old_energy and original.fatigue == old_fatigue
    assert first.failed and first.rows == first_rows
    assert first.energy.body == first_energy and first.fatigue == first_fatigue
    assert second is not first and first is not original
    assert second.energy._credits == {"t2-native-meal"}
    assert second.energy.credit_count == 1
    assert second.rows[0]["world_tick"] == 221
    assert len(second.rows) == 1
    assert first.segment_origin_dev["unobserved_world_ticks"] == 7
    assert second.segment_origin_dev["unobserved_world_ticks"] == 8
    assert not second.segment_origin_dev["p1_wait_qualified"]
    assert second.segment_origin_dev["stop_gap_debit_and_credit"] == 0
