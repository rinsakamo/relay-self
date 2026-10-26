"""DEV timing reducer must exclude pre-Action hazards and retain missed ticks."""
import json

from adapters.mineflayer.t1e_native_dev import measure


def test_active_interval_latency_excludes_startup_unknown_and_uses_node_clock(tmp_path):
    frames = [
        {"type": "paper_l0_shadow", "seq": 2, "paper_server_tick": "10",
         "assessment": "UNKNOWN", "node_monotonic_ns": "1"},
        {"type": "effect_result", "effect": "set_control", "seq": 10,
         "result": "applied", "node_monotonic_ns": "100000000"},
        {"type": "paper_l0_shadow", "seq": 11, "paper_server_tick": "11",
         "assessment": "LOW_HEALTH", "node_monotonic_ns": "102000000"},
        {"type": "effect_result", "effect": "clear_controls", "seq": 13,
         "result": "applied", "node_monotonic_ns": "104000000"},
        {"type": "paper_l0_shadow", "seq": 14, "paper_server_tick": "12",
         "assessment": "LOW_HEALTH", "node_monotonic_ns": "105000000"},
    ]
    (tmp_path / "node_timing.jsonl").write_text("\n".join(map(json.dumps, frames)))
    (tmp_path / "paper.log").write_text(
        "PAPER_DEV_TIME_SAMPLE server_tick=10 wall_nanos=999000000000\n"
        "PAPER_DEV_TIME_SAMPLE server_tick=11 wall_nanos=999050000000\n"
        "PAPER_DEV_TIME_SAMPLE server_tick=12 wall_nanos=999100000000\n"
        "PAPER_DEV_TIME_SAMPLE server_tick=13 wall_nanos=999150000000\n")
    (tmp_path / "commands.jsonl").write_text(
        '{"effect":"set_control"}\n{"effect":"clear_controls"}\n')
    metrics = measure(tmp_path, {})
    assert metrics["node_shadow_emit_to_clear_applied_ms"] == 2
    assert metrics["active_danger_assessment"] == "LOW_HEALTH"
    assert metrics["active_shadow_ticks"] == 1
    assert metrics["paper_ticks_without_emitted_l0"] == ["13"]
    assert metrics["paper_effective_tps"] == 20
    assert not metrics["fresh_world_tick_attested"]
    assert metrics["clear_control_sends"] == 1
