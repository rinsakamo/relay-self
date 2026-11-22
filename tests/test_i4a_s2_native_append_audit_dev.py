"""Original S1->S2 Native append auditor (synthetic, CPU-only)."""
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from relay_self.i_lane_i4a_s1_source_capture_dev import freeze_original_s1_wal
from relay_self.i_lane_i4a_s2_first_native_move_dev import (
    issue_s2_first_original_place_move_synthetic_dev,
)
from relay_self.i_lane_i4a_s2_native_append_audit_dev import (
    I4AS2NativeAppendHold,
    audit_i4a_s2_native_append,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s1_native_source_audit_dev import _stream, _write_raw
from test_i4a_s2_first_move_proposal_dev import _first_s2, _propose
from test_i4a_s2_first_native_move_dev import _prepare_native
from test_i4a_s2_first_physical_reservation_dev import _prepare


def test_original_s2_native_append_readback_refuses_forged_source(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        owner = loop.owner
        old = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).records
        directory = tmp_path / "s1-frozen"
        directory.mkdir()
        captured = freeze_original_s1_wal(
            owner, physical=f.physical, lane=lane,
            anchor=boundary.anchor, evidence_dir=directory,
        )
        original = tmp_path / "s1-native.jsonl"
        before_sha = _write_raw(original, _stream(old))
        candidate = _propose(f, lane, witness, boundary, observed)
        native, args = _prepare(f, lane, candidate, witness)
        _prepare_native(f, candidate, native)
        await issue_s2_first_original_place_move_synthetic_dev(
            native, candidate, **args,
        )
        rows = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).records
        full = tmp_path / "s2-native.jsonl"
        entries = _stream(rows)
        after_sha = _write_raw(full, entries)
        kwargs = {
            "s2_wal": owner.files.physical_wal_file,
            "before_stdout": original, "after_stdout": full,
            "before_sha256": before_sha, "after_sha256": after_sha,
            "action_id": candidate.action_id,
            "skill_id": boundary.new_skill_id, "intent_id": boundary.new_intent_id,
        }
        receipt = audit_i4a_s2_native_append(captured, **kwargs)
        # Independent subprocess must reconstruct the receipt from disk and
        # cannot access the live original Owner/Physical/Resident model.
        manifest = tmp_path / "capture.json"
        manifest.write_text(json.dumps(asdict(captured)), encoding="utf-8")
        root = Path(__file__).resolve().parents[1]
        script = root / "experiments" / "i_lane_i4a_s2_independent_native_audit_dev.py"
        argv = [
            sys.executable, str(script), "--capture", str(manifest),
            "--s2-wal", str(kwargs["s2_wal"]),
            "--before-stdout", str(original), "--after-stdout", str(full),
            "--before-sha256", before_sha, "--after-sha256", after_sha,
            "--action-id", candidate.action_id,
            "--skill-id", boundary.new_skill_id,
            "--intent-id", boundary.new_intent_id,
        ]
        env = {**os.environ, "PYTHONPATH": str(root / "src") + os.pathsep + str(root)}
        verified = subprocess.run(
            argv, cwd=root, env=env, capture_output=True, text=True,
            timeout=15, check=False,
        )
        assert verified.returncode == 0, verified.stderr
        separate = json.loads(verified.stdout)
        assert separate["classification"].endswith("CPU_OFFLINE_ONLY")
        assert not separate["physical_authorized"]
        assert not separate["paper_attested"]
        fake = json.loads(manifest.read_bytes())
        fake["restart_authenticated"] = True
        manifest.write_text(json.dumps(fake), encoding="utf-8")
        denied = subprocess.run(
            argv, cwd=root, env=env, capture_output=True, text=True,
            timeout=15, check=False,
        )
        assert denied.returncode == 2
        assert "I4A_S1_S2_NATIVE_CONTENT_HOLD" in denied.stderr
        assert receipt.s2_status == "NATIVE_PLACE_MOVE_SETTLED"
        assert receipt.s2_effect_count == 3
        assert receipt.native_probe_count == 4
        assert not receipt.world_attested
        assert not receipt.paper_attested
        assert not receipt.physical_authorized
        assert not receipt.restart_authenticated
        assert native.sent_commands
        for index, mutate, match in (
            (rows[-1]["effect_seqs"][0], "action_id", "child ACK"),
            (rows[-1]["after_seq"], "session_id", "stream invalid"),
        ):
            forged = json.loads(json.dumps(entries))
            forged[index][mutate] = "foreign-original"
            tampered_sha = _write_raw(full, forged)
            with pytest.raises(I4AS2NativeAppendHold, match=match):
                audit_i4a_s2_native_append(
                    captured, **{**kwargs, "after_sha256": tampered_sha},
                )
        forged = json.loads(json.dumps(entries))
        forged[0]["config"]["username"] = "new-session"
        tampered_sha = _write_raw(full, forged)
        with pytest.raises(I4AS2NativeAppendHold, match="append-only"):
            audit_i4a_s2_native_append(
                captured, **{**kwargs, "after_sha256": tampered_sha},
            )
        forged = json.loads(json.dumps(entries))
        forged[rows[-1]["after_seq"]]["snapshot"]["position"]["x"] += 0.5
        tampered_sha = _write_raw(full, forged)
        with pytest.raises(I4AS2NativeAppendHold, match="position/tick"):
            audit_i4a_s2_native_append(
                captured, **{**kwargs, "after_sha256": tampered_sha},
            )
    _fixture(tmp_path, scenario)
