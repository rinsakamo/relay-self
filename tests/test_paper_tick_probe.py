"""T1 Paper observer-only logs; synthetic rows cannot authorize TPS or L0."""
import pytest

from adapters.mineflayer.m02_paper_dev.paper_tick_probe import (
    PaperTickProbeRejected,
    read_passive_paper_ticks,
)


def log(*, count=4, tps=20):
    return "\n".join(
        "[Paper INFO]: PAPER_DEV_TIME_SAMPLE "
        f"index={i + 1} server_tick={100 + i} world_full_time={500 + i} "
        f"wall_nanos={10_000_000_000 + i * (1_000_000_000 // tps)} "
        "world=abc player=bot-uuid "
        "source=PAPER_SCHEDULER_CALLBACK_ONLY l0_checked=false action_bound=false"
        for i in range(count)
    )


def read(source):
    return read_passive_paper_ticks(source, expected_world="abc", expected_player="bot-uuid")


def test_consecutive_paper_samples_calculate_measured_tps_not_requested_tps():
    for tps in (2, 20, 200):
        result = read(log(tps=tps))
        assert result.paper_ticks == (100, 101, 102, 103)
        assert result.effective_tps == pytest.approx(tps)
        assert result.source_class == "PAPER_SCHEDULER_CALLBACK_ONLY"
        assert not result.l0_checked and not result.action_bound and not result.qualified
        assert not hasattr(result, "l0_checked_ticks")


@pytest.mark.parametrize("old,new", [
    ("index=3", "index=2"),
    ("server_tick=102", "server_tick=104"),
    ("server_tick=102", "server_tick=101"),
    ("world_full_time=502", "world_full_time=504"),
    ("wall_nanos=10100000000", "wall_nanos=10050000000"),
    ("world=abc", "world=wrong"),
    ("player=bot-uuid", "player=wrong"),
    ("l0_checked=false", "l0_checked=true"),
    ("action_bound=false", "action_bound=true"),
    ("source=PAPER_SCHEDULER_CALLBACK_ONLY", "source=FAKE"),
])
def test_changed_out_of_scope_or_fabricated_coverage_rejected(old, new):
    assert old in log()
    with pytest.raises(PaperTickProbeRejected):
        read(log().replace(old, new, 1))


def test_missing_duplicate_and_partial_trace_rejected():
    original = log().splitlines()
    for source in ("\n".join(original[1:]),
                   "\n".join(original[:2] + original[3:]),
                   "\n".join(original[:2] + [original[1]] + original[2:]),
                   original[0], ""):
        with pytest.raises(PaperTickProbeRejected):
            read(source)


def test_extra_or_duplicate_sample_fields_rejected():
    for source in (log().replace("l0_checked=false", "l0_checked=false bonus=true", 1),
                   log().replace("world=abc", "world=abc world=abc", 1),
                   log().replace("index=1", "index=1.0", 1),
                   log().replace("index=1", "index=-1", 1)):
        with pytest.raises(PaperTickProbeRejected):
            read(source)


def test_misleading_timestamp_or_foreign_log_cannot_grant_passive_samples():
    with pytest.raises(PaperTickProbeRejected):
        read(log().replace("wall_nanos=10050000000", "wall_nanos=10000000000", 1))
    with pytest.raises(PaperTickProbeRejected):
        read_passive_paper_ticks(log(), expected_world="wrong", expected_player="bot-uuid")


def test_bounds_and_extra_irrelevant_paper_logs():
    assert len(read("header\n" + log() + "\nother unrelated log").samples) == 4
    with pytest.raises(PaperTickProbeRejected):
        read(log(count=257))
    with pytest.raises(PaperTickProbeRejected):
        read_passive_paper_ticks(log(), expected_world="abc", expected_player="bot-uuid", max_rows=1)
