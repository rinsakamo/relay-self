"""Adversarial checks for R2-3i runner admission and source capture."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from experiments.p0d_real_resident_presence_dev import run_real_resident_presence
from experiments.r2_3i_independent_audit_dev import read_native, verify_manifest
from experiments.r2_3i_real_original_rejoin_dev import seal_evidence, wait_for_paper_present
from experiments.stage28c2c_real_original_l1_dev import OriginalRawBoundedLlamaProvider
from test_mineflayer_process_session import observation_line
from test_p0d_resident_paper_presence_join_dev import BOOT, PAPER, WORLD, A, B, _line


@pytest.mark.parametrize("competing", ["world_only", "initial_source_dev", "b_selected_move_dev",
                                     "b_autonomous_l1_dev", "typed_owner_cut_dev"])
def test_rejoin_opt_in_refuses_competing_mode_before_asset_io(tmp_path, competing):
    with pytest.raises(RuntimeError, match="without competing"):
        asyncio.run(run_real_resident_presence(
            paper_jar=tmp_path / "missing-paper", paper_sha256="",
            plugin_jar=tmp_path / "missing-plugin", plugin_sha256="",
            scratch_parent=tmp_path, accepted_eula=True, real_world_dev_grant=True,
            exploration_schema_dev=True, original_rejoin_dev=True, **{competing: True},
        ))
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("fault", ["missing", "duplicate", "b_logout", "foreign_epoch", None])
def test_rejoin_wait_requires_original_paper_edges_and_present(tmp_path, fault):
    rows = [
        f"P0D_RESIDENT_READY boot={BOOT} source=PAPER_MAIN_THREAD version=1",
        _line("JOIN", 1, A, "RelayA"), _line("JOIN", 2, B, "RelayB"),
        _line("QUIT", 3, A, "RelayA"), _line("PRESENT", 4, B, "RelayB"),
        _line("JOIN", 5, A, "RelayA"), _line("PRESENT", 6, A, "RelayA"),
        _line("PRESENT", 7, B, "RelayB"),
    ]
    if fault == "duplicate":
        rows.insert(4, rows[3])
    elif fault == "missing":
        del rows[-1]
    elif fault == "b_logout":
        rows.append(_line("QUIT", 8, B, "RelayB"))
    raw = ("\n".join(rows) + "\n").encode()
    bridge = SimpleNamespace(
        lifecycle=SimpleNamespace(world=SimpleNamespace(
            paper_session_id=PAPER, world_id=B if fault == "foreign_epoch" else WORLD,
        )),
        paper=SimpleNamespace(read_owned_log=lambda session: raw),
    )
    if fault:
        with pytest.raises((RuntimeError, ValueError)):
            asyncio.run(wait_for_paper_present(bridge, tmp_path, "rejoin", 0.005))
        assert not tuple(tmp_path.iterdir())
    else:
        asyncio.run(wait_for_paper_present(bridge, tmp_path, "rejoin", 0.005))
        assert (tmp_path / "paper-rejoin.log").read_bytes() == raw


@pytest.mark.parametrize("sequences", [(1, 1), (2, 1), (1, 3), (1, 2)])
def test_native_audit_rejects_duplicate_reverse_and_missing_sequence(tmp_path, sequences):
    probe = json.loads(observation_line())
    start = {
        "type": "adapter_started", "session_id": probe["session_id"], "seq": 0,
        "mineflayer_version": MINEFLAYER_VERSION,
        "config": {"host": "127.0.0.1", "port": 25565, "username": "RelayA", "version": "1.21.8"},
    }
    path = tmp_path / "native.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in (
        start, *(dict(probe, seq=seq, kind="probe", request_id=f"p-{index}")
                 for index, seq in enumerate(sequences)),
    )) + "\n")
    if sequences == (1, 2):
        assert len(read_native(path, "RelayA")[1]) == 2
    else:
        with pytest.raises(ValueError, match="sequence mismatch"):
            read_native(path, "RelayA")


def test_manifest_checks_missing_and_injected_files(tmp_path):
    path = tmp_path / "raw"
    path.write_bytes(b"owned stdout")
    seal_evidence(tmp_path)
    verify_manifest(tmp_path)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="manifest mismatch"):
        verify_manifest(tmp_path)


def test_question_provider_repeated_post_refused_at_transport(tmp_path, monkeypatch):
    sent = []
    def timeout(request, **kwargs):
        sent.append(request)
        raise TimeoutError("synthetic timeout")

    monkeypatch.setattr("urllib.request.urlopen", timeout)
    provider = OriginalRawBoundedLlamaProvider(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma", raw_dir=tmp_path, max_posts=1,
    )
    with pytest.raises(RuntimeError, match="may be in flight"):
        provider._call({"model": "gemma"})
    with pytest.raises(RuntimeError, match="repeated model POST"):
        provider._call({"model": "gemma"})
    assert len(sent) == provider.attempted == 1
    assert provider.completed == 0
