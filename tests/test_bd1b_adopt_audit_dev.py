"""Generate faithful CPU synthetic ADOPT originals and audit in another process."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from relay_self.bd1b_adopt_audit_dev import audit_adopt_bundle
from relay_self.relay_engine import ProviderDecision
from test_bd1b_adopt_commit_dev import commit
from test_bd1b_issuer_readback_dev import read, setup, submit

_FILES = (
    "cognition.before.json", "cognition.after.json",
    "physical.before.wal", "physical.after.wal",
)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _write_json(path, value):
    path.write_text(
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _fixture_bundle(tmp_path, monkeypatch):
    case, turns, lane = setup(tmp_path / "self", monkeypatch, ProviderDecision.resolved("1"))
    try:
        turn = turns[0]
        owner = turn.owner
        ticket = submit(lane, turn)
        job = lane._jobs[(turn.self_id, turn.work_ref)]
        readback = read(case, lane, turn, ticket)
        assert job.question_adoption_state == "unused"
        before_pending = sorted(owner.pending_questions)
        before_cognition = owner.files.cognition_file.read_bytes()
        before_wal = owner.files.physical_wal_file.read_bytes()
        before_job = job.question_adoption_state

        assert commit(case, lane, turn, ticket) == "ADOPT"
        assert job.question_adoption_state == "committed"
        assert job.question_adoption_binding is not None
        after_cognition = owner.files.cognition_file.read_bytes()
        after_wal = owner.files.physical_wal_file.read_bytes()
        final_binding = job.question_adoption_binding
        assert final_binding[0] is ticket

        bundle = tmp_path / "audit-bundle"
        bundle.mkdir()
        originals = {
            "cognition.before.json": before_cognition,
            "cognition.after.json": after_cognition,
            "physical.before.wal": before_wal,
            "physical.after.wal": after_wal,
        }
        for name, raw in originals.items():
            (bundle / name).write_bytes(raw)

        request = asdict(turn.request)
        probe = turn.original_probe
        boot = case[2]
        freeze = {
            "self_id": turn.self_id,
            "self_scope": list(turn.owner_scope),
            "paper_session": boot.paper_session_id,
            "paper_boot": boot.paper_boot_id,
            "world_uuid": boot.source_world_id,
            "fork": boot.fork_branch_id,
            "probe_session": probe.session_id,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "probe_provenance": probe.provenance.reference,
            "registry_revision": owner.pattern_registry.revision,
            "request_id": turn.request.request_id,
            "choices": [[c.choice_id, c.description] for c in turn.request.choices],
            "presets": [],
            "context": [
                [c.key, c.value_json, c.provenance.reference]
                for c in turn.request.context
            ],
        }
        manifest = {
            "version": 1,
            "kind": "CPU_SYNTHETIC",
            "ticket": asdict(ticket),
            "request": request,
            "request_sha256": job.request_sha256,
            "source": asdict(turn.source),
            "candidate_input": freeze,
            "candidate_set_sha256": turn.candidate_set_sha256,
            "readback": asdict(readback),
            "provider_decision": asdict(job.future.result()),
            "job_binding": {
                "ticket": asdict(final_binding[0]),
                "work_ref": final_binding[1],
                "request_sha256": final_binding[2],
                "candidate_set_sha256": final_binding[3],
                "owner_scope": list(final_binding[4]),
            },
            "job_state_before": before_job,
            "job_state_after": job.question_adoption_state,
            "inquiry_ref": turn.inquiry.question_ref,
            "pending_before": before_pending,
            "pending_after": sorted(owner.pending_questions),
            "file_sha256": {name: _sha(raw) for name, raw in originals.items()},
        }
        _write_json(bundle / "manifest.json", manifest)
        return bundle
    finally:
        lane._pool.shutdown(wait=True)


def _subprocess_audit(bundle):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "relay_self.bd1b_adopt_audit_dev", str(bundle)],
        cwd=root, env=env, text=True, capture_output=True, check=False,
    )


def test_actual_cpu_adoption_bundle_passes_separate_process(tmp_path, monkeypatch):
    (tmp_path / "self").mkdir()
    bundle = _fixture_bundle(tmp_path, monkeypatch)
    result = audit_adopt_bundle(bundle)
    assert result["classification"] == "CPU_SYNTHETIC_ADOPT_BUNDLE_CONSISTENT"
    before_audit = {p.name: p.read_bytes() for p in bundle.iterdir()}
    proc = _subprocess_audit(bundle)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["inquiry_ref"] == result["inquiry_ref"]
    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == before_audit
    # An opt-in CI archive preserves actual copied originals for later review.
    # Re-audit the archive in a fresh process before the artifact is uploaded.
    retained = os.environ.get("BD1B_AUDIT_ARCHIVE")
    if retained:
        archive = Path(retained)
        assert not archive.exists()
        shutil.copytree(bundle, archive)
        recheck = _subprocess_audit(archive)
        assert recheck.returncode == 0, recheck.stderr
        assert json.loads(recheck.stdout) == result
        print("BD1B_AUDIT_ORIGINAL " + json.dumps({
            "archive": str(archive),
            "manifest_sha256": _sha((archive / "manifest.json").read_bytes()),
            "file_sha256": {name: _sha((archive / name).read_bytes()) for name in _FILES},
            **result,
        }, sort_keys=True))


@pytest.mark.parametrize("variant", [
    "missing", "truncated", "request", "ticket", "source", "candidate",
    "submitted_digest", "binding", "consumption", "readback",
    "pending", "wal", "question", "origin", "provider", "registry",
    "duplicate_json", "symlink_manifest", "symlink_evidence", "registry_install",
])
def test_auditor_rejects_changed_originals(tmp_path, monkeypatch, variant):
    (tmp_path / "self").mkdir()
    bundle = _fixture_bundle(tmp_path, monkeypatch)
    altered = tmp_path / "altered"
    shutil.copytree(bundle, altered)
    manifest_file = altered / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if variant == "missing":
        (altered / "physical.after.wal").unlink()
    elif variant == "symlink_manifest":
        manifest_file.unlink()
        manifest_file.symlink_to(bundle / "manifest.json")
    elif variant == "symlink_evidence":
        after_wal = altered / "physical.after.wal"
        after_wal.unlink()
        after_wal.symlink_to(altered / "physical.before.wal")
    elif variant == "truncated":
        (altered / "cognition.after.json").write_text('{"invalid"', encoding="utf-8")
    elif variant == "wal":
        with (altered / "physical.after.wal").open("ab") as f:
            f.write(b"evil")
    elif variant == "duplicate_json":
        raw = manifest_file.read_text(encoding="utf-8").rstrip()
        manifest_file.write_text(
            raw[:-1] + ', "version": 1}', encoding="utf-8",
        )
    elif variant in ("question", "origin", "registry_install"):
        path = altered / "cognition.after.json"
        post = json.loads(path.read_text(encoding="utf-8"))
        q = post["exploration_continuity"]["questions"][-1]
        if variant == "question":
            q["question_ref"] = "foreign-inquiry"
        elif variant == "origin":
            q["origin"]["reference"] = '{"choice_id":"2"}'
        else:
            post["pattern_registry"] = {"revision": 999}
        raw = (json.dumps(post, sort_keys=True, ensure_ascii=False) + "\n").encode()
        path.write_bytes(raw)
        manifest["file_sha256"]["cognition.after.json"] = _sha(raw)
        _write_json(manifest_file, manifest)
    else:
        if variant == "request":
            manifest["request"]["choices"].reverse()
        elif variant == "ticket":
            manifest["ticket"]["request_id"] = "forged"
        elif variant == "source":
            manifest["source"]["paper_session_id"] = "forged"
        elif variant == "candidate":
            manifest["candidate_set_sha256"] = "0" * 64
        elif variant == "submitted_digest":
            manifest["request_sha256"] = "0" * 64
        elif variant == "binding":
            manifest["job_binding"]["work_ref"] = "forged"
        elif variant == "consumption":
            manifest["job_state_after"] = "unused"
        elif variant == "readback":
            manifest["readback"]["selection"] = "DECLINE"
        elif variant == "provider":
            manifest["provider_decision"]["choice_id"] = "2"
        elif variant == "registry":
            manifest["candidate_input"]["registry_revision"] = 77
        elif variant == "pending":
            manifest["pending_after"] = []
        _write_json(manifest_file, manifest)
    proc = _subprocess_audit(altered)
    assert proc.returncode != 0, (variant, proc.stdout, proc.stderr)
    assert "HOLD:" in proc.stderr
