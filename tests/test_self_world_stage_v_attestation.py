"""Stage V cross-process crypto proof: synthetic key, NO external issuer trust.

Signer subprocess can validate request bytes but not physical World truth.
No real S10 authorization is sent to the original physical Action host.
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, replace

import pytest

import test_self_world_stage_s_feedback as s_fixture
from adapters.mineflayer.self_world_stage_v_attestation import (
    StageVAttestationRejected,
    StageVGrantRequest,
    StageVPinnedGrantVerifier,
    fingerprint_for_public_pem,
    request_from_existing_world,
)


def _request(run_id="stage-v-disposable-001"):
    w = s_fixture._synthetic_targeted_witness(0.5, 0.0)
    after = w.consequence.after_observation
    assert after is not None
    probe = replace(
        w.original_probe, seq=after.seq + 3,
        request_id=f"s49-actual:{w.original_probe.session_id}:event-{after.seq + 2}",
    )
    return request_from_existing_world(
        run_id=run_id, closed=w, following_probe=probe,
    )


@pytest.fixture(scope="module")
def signed_original(tmp_path_factory):
    assert shutil.which("openssl"), "Stage V signature boundary requires OpenSSL"
    root = tmp_path_factory.mktemp("stage-v-external-issuer")
    private = root / "issuer-private.pem"
    public = root / "public-pinned.pem"
    proc = subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA",
         "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)],
        capture_output=True, check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    proc = subprocess.run(
        ["openssl", "pkey", "-in", str(private),
         "-pubout", "-out", str(public)],
        capture_output=True, check=False, timeout=15,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    request = _request()
    infile = root / "request.json"
    outfile = root / "issued-signed-grant.json"
    infile.write_text(json.dumps(asdict(request)))
    # Exactly one independent Python issuer process, which itself invokes
    # OpenSSL holding the private key. The consumer uses only public bytes.
    proc = subprocess.run(
        [sys.executable, "-m",
         "adapters.mineflayer.self_world_stage_v_attestation",
         "--request", str(infile),
         "--private-key", str(private),
         "--public-key", str(public),
         "--output", str(outfile)],
        capture_output=True, check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    return request, json.loads(outfile.read_text()), public.read_bytes()


def _verifier(public, *, run="stage-v-disposable-001"):
    return StageVPinnedGrantVerifier(
        pinned_public_pem=public,
        pinned_fingerprint=fingerprint_for_public_pem(public),
        expected_run_id=run,
    )


def test_v_separate_signer_process_matches_pinned_public_and_replay_denial(
    signed_original,
):
    request, envelope, public = signed_original
    verifier = _verifier(public)
    accepted = verifier.verify_once(envelope, expected=request)
    assert accepted is request
    assert accepted.expected_revision == 1
    assert accepted.expected_value == 4
    assert accepted.proposed_value == 3
    assert accepted.direction == "decrease"
    assert accepted.next_probe_seq > accepted.after_seq
    with pytest.raises(StageVAttestationRejected, match="replay"):
        verifier.verify_once(envelope, expected=request)


@pytest.mark.parametrize("bad", (
    "wrong_fingerprint", "wrong_run", "foreign_action",
    "wrong_direction", "wrong_source_sha", "wrong_revision",
    "copied_session", "alter_signed_request", "alter_signature",
    "missing_signature", "extra_envelope_field", "truncated_signature",
    "bad_b64", "unknown_request_key", "replayed_with_another_run",
))
def test_v_signed_envelope_scope_and_sham_rejected(signed_original, bad):
    request, original_envelope, public = signed_original
    envelope = json.loads(json.dumps(original_envelope))
    verifier = _verifier(public)
    expected = request
    if bad == "wrong_fingerprint":
        envelope["key_fingerprint_sha256"] = "0" * 64
    elif bad == "wrong_run":
        envelope["request"]["run_id"] = "stage-v-wrong-run"
    elif bad == "foreign_action":
        envelope["request"]["action_id"] = "s49-native-move-50"
    elif bad == "wrong_direction":
        envelope["request"]["direction"] = "increase"
        envelope["request"]["proposed_value"] = 5
    elif bad == "wrong_source_sha":
        envelope["request"]["evidence_sha256"] = "a" * 64
    elif bad == "wrong_revision":
        envelope["request"]["expected_revision"] = 2
    elif bad == "copied_session":
        envelope["request"]["session_id"] = "another-session"
    elif bad == "alter_signed_request":
        envelope["request"]["next_probe_seq"] += 1
        expected = StageVGrantRequest.from_dict(envelope["request"])
    elif bad == "alter_signature":
        original = base64.b64decode(envelope["signature_b64"])
        envelope["signature_b64"] = base64.b64encode(
            bytes([original[0] ^ 1]) + original[1:],
        ).decode()
    elif bad == "missing_signature":
        del envelope["signature_b64"]
    elif bad == "extra_envelope_field":
        envelope["public_key"] = "attacker-controlled"
    elif bad == "truncated_signature":
        envelope["signature_b64"] = base64.b64encode(
            base64.b64decode(envelope["signature_b64"])[:-1],
        ).decode()
    elif bad == "bad_b64":
        envelope["signature_b64"] = "!not-base64!"
    elif bad == "unknown_request_key":
        envelope["request"]["issuer_tells_truth"] = True
    elif bad == "replayed_with_another_run":
        verifier = _verifier(public, run="stage-v-other-run")
    with pytest.raises(StageVAttestationRejected):
        verifier.verify_once(envelope, expected=expected)


def test_v_valid_signature_not_sufficient_for_source_truth_or_live_grant(
    signed_original,
):
    request, envelope, public = signed_original
    assert _verifier(public).verify_once(envelope, expected=request) == request
    # A locally test-generated signing key can authenticate TEST bytes,
    # but does not prove real original S49 terminal or qualified issuer.
    # No LearningUpdateAuthority or S10 state commit is constructed here.
    assert request.direction == "decrease"
    assert request.run_id == "stage-v-disposable-001"


@pytest.mark.parametrize("change", (
    "no_future_probe", "foreign_future_probe", "stale_future_probe",
    "missing_future_request", "wrong_future_event", "future_event_after_probe",
    "hold_outcome", "foreign_direction",
))
def test_v_original_source_shape_denies_unsupported_grant_request(change):
    w = s_fixture._synthetic_targeted_witness(0.5, 0.0)
    after = w.consequence.after_observation
    assert after is not None
    probe = replace(
        w.original_probe, seq=after.seq + 3,
        request_id=f"s49-actual:{w.original_probe.session_id}:event-{after.seq + 2}",
    )
    if change == "no_future_probe":
        probe = None
    elif change == "foreign_future_probe":
        probe = replace(probe, session_id="foreign")
    elif change == "stale_future_probe":
        probe = replace(probe, seq=after.seq)
    elif change == "missing_future_request":
        probe = replace(probe, request_id=None)
    elif change == "wrong_future_event":
        probe = replace(probe, request_id="forged-event-from-other-owner")
    elif change == "future_event_after_probe":
        probe = replace(
            probe,
            request_id=f"s49-actual:{w.original_probe.session_id}:event-{probe.seq+1}",
        )
    elif change == "hold_outcome":
        w = s_fixture._synthetic_targeted_witness(0.0, 0.2)
    else:
        w = replace(w, interpretation=replace(
            w.interpretation, reason_code="prediction_match",
        ))
    with pytest.raises((StageVAttestationRejected, ValueError)):
        request_from_existing_world(
            run_id="stage-v-disposable-002", closed=w, following_probe=probe,
        )
