"""Static browser preview, no network, JS, game effect, model or Memory write."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_timeline
from adapters.mineflayer.self_timeline_html import render_html
from test_self_demo import _native_report
from test_self_timeline import _l2, _memory


def _all_events():
    return self_timeline.timeline(
        _native_report(), live_l2=_l2(), memory=_memory(),
    )


def test_browser_preview_renders_existing_original_world_events():
    html = render_html(_all_events())
    assert html.startswith("<!doctype html>")
    assert "<title>RelaySelf · Cognition timeline</title>" in html
    assert html.count("class='event'") == 10
    assert "Epoch 1" in html
    assert html.count("<div class='lane'>L0</div>") == 3
    assert "WAIT" in html and "MOVE_AWAY" in html
    assert "0.627" in html
    assert "Goal: UNKNOWN" in html
    assert "no new Habit" in html
    assert "EXPIRED_WORLD_ADVANCED" in html
    assert "temporal overlap" in html
    assert "RELAYSELF · OBSERVATIONAL PLAYBACK" in html
    assert "default-src 'none'" in html
    assert "<script" not in html.lower()
    assert "https://" not in html.lower()


def test_untrusted_model_text_is_html_escaped_never_script_markup():
    events = list(_all_events())
    idx = next(i for i, x in enumerate(events) if x["kind"] == "l2_observer")
    events[idx] = {
        **events[idx],
        "text_untrusted": '<img src=x onerror=alert("oops")> & </div>',
    }
    html = render_html(tuple(events))
    assert "&lt;img src=x onerror=alert(&quot;oops&quot;)&gt;" in html
    assert "&amp; &lt;/div&gt;" in html
    assert '<img src=x' not in html
    assert "Model commentary (untrusted)" in html


@pytest.mark.parametrize("mutation", [
    lambda x: tuple(),
    lambda x: ({"kind": "present"}, *x[1:]),
    lambda x: (x[0], *x[1:-1], {"kind": "bad"}),
    lambda x: (x[0], {**x[1], "session": "foreign"}, *x[2:]),
    lambda x: (x[0], {**x[1], "schema": "fake"}, *x[2:]),
])
def test_browser_requires_full_source_bound_product_timeline(mutation):
    with pytest.raises(ValueError):
        render_html(mutation(_all_events()))


def test_cli_writes_one_static_html_page_without_mutating_any_input(
    tmp_path: Path, capsys,
):
    native = tmp_path / "native_report.json"
    native.write_text(json.dumps(_native_report()), encoding="utf-8")
    dst = tmp_path / "viewer.html"
    original = native.read_bytes()
    options = [
        "--native-report", str(native),
        "--format", "html", "--output", str(dst),
    ]
    assert self_timeline.main(options) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "VIEW_WRITTEN"
    assert result["world_actions_issued"] == 0
    assert result["model_requests_issued"] == 0
    assert dst.is_file()
    assert "One Self session" in dst.read_text(encoding="utf-8")
    assert native.read_bytes() == original
    snapshot = dst.read_bytes()
    assert self_timeline.main(options) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "UNDETERMINED"
    assert dst.read_bytes() == snapshot


def test_cli_fails_closed_when_html_output_missing_or_not_html(
    tmp_path: Path, capsys,
):
    report = tmp_path / "native_report.json"
    report.write_text(json.dumps(_native_report()), encoding="utf-8")
    for args in (
        ["--format", "html"],
        ["--format", "html", "--output", str(tmp_path / "viewer.json")],
        ["--format", "jsonl", "--output", str(tmp_path / "viewer.html")],
    ):
        assert self_timeline.main(["--native-report", str(report), *args]) == 2
        assert json.loads(capsys.readouterr().out)["status"] == "UNDETERMINED"
    assert sorted(x.name for x in tmp_path.iterdir()) == ["native_report.json"]


def test_html_output_with_optional_l2_and_memory_keeps_user_source_files(
    tmp_path: Path, capsys,
):
    from relay_self.persistent_cognition import save_persistent_cognition

    native = tmp_path / "native_report.json"
    live = tmp_path / "live_l2.jsonl"
    memory = tmp_path / "observed_memory.json"
    native.write_text(json.dumps(_native_report()), encoding="utf-8")
    live.write_text(json.dumps(_l2()) + "\n", encoding="utf-8")
    save_persistent_cognition(memory, _memory())
    prior = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert self_timeline.main([
        "--native-report", str(native),
        "--live-l2", str(live),
        "--memory", str(memory),
        "--format", "html", "--output", str(tmp_path / "timeline.html"),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "VIEW_WRITTEN"
    for name, content in prior.items():
        assert (tmp_path / name).read_bytes() == content
    output = (tmp_path / "timeline.html").read_text(encoding="utf-8")
    assert "Maybe observe whether the hazard moves" in output
    assert "2 stored movement observations" in output
    assert "Model commentary (untrusted)" in output
