"""S31-A static and deterministic gates; no Minecraft server on pytest."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_source_native_world as s27
from adapters.mineflayer.s31a_real_server_ci import (
    MINECRAFT_VERSION,
    MINEFLAYER_VERSION,
    S31ABlocked,
    S31AQualificationError,
    _assert_official_url,
    _verified_target,
    _write_config,
)

ROOT = Path(__file__).resolve().parents[1]


def test_s31a_requires_exact_pinned_actual_version():
    assert MINECRAFT_VERSION == "1.21.8"
    assert MINEFLAYER_VERSION == "4.39.0"


@pytest.mark.parametrize("url", [
    "http://piston-meta.mojang.com/version.json",
    "https://evil.example/minecraft-server.jar",
    "https://piston-data.mojang.com.evil.example/server.jar",
    "https://bad@piston-data.mojang.com/server.jar",
    "https://piston-data.mojang.com:444/server.jar",
    "file:///tmp/fake.jar",
])
def test_download_rejects_nonofficial_server_url(url):
    with pytest.raises(S31ABlocked):
        _assert_official_url(url)


def test_download_accepts_only_explicit_official_https_hosts():
    _assert_official_url(
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    )
    _assert_official_url(
        "https://piston-data.mojang.com/v1/objects/valid/server.jar"
    )


def test_disposable_server_must_bind_loopback_and_disable_external_control(tmp_path):
    _write_config(tmp_path)
    props = dict(
        line.split("=", 1)
        for line in (tmp_path / "server.properties").read_text().splitlines()
    )
    assert props["server-ip"] == "127.0.0.1"
    assert props["server-port"] == "25565"
    assert props["online-mode"] == "false"
    assert props["enable-rcon"] == "false"
    assert props["level-type"] == "minecraft:flat"
    assert props["max-players"] == "2"
    assert (tmp_path / "eula.txt").read_text() == "eula=true\n"


def test_world_registry_fact_geometry_accepts_only_one_known_zombie():
    _data, _failed, _inputs, args = s27._fixture(distance_m=1.8)
    target = _verified_target(args["observation"])
    assert target is not None
    assert target["entity_id"] == s27.ENTITY_ID
    assert target["name"] == "zombie"
    assert target["distance_m"] == 1.8
    assert target["coverage_truncated"] is False
    assert target["request_id"] is None  # raw S27 test fixture, not live S31-A


def test_absent_target_is_unknown_not_safety_evidence():
    _, _, _, args = s27._fixture()
    observation = args["observation"]
    snap = replace(
        observation.snapshot, nearby_entities=(),
        nearby_entities_coverage=replace(
            observation.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    )
    assert _verified_target(replace(observation, snapshot=snap)) is None


def test_reported_entity_distance_mismatch_does_not_qualify():
    _, _, _, args = s27._fixture()
    observation = args["observation"]
    entity = observation.snapshot.nearby_entities[0]
    changed = replace(
        observation, snapshot=replace(
            observation.snapshot,
            nearby_entities=(replace(entity, distance=1.0),),
        ),
    )
    with pytest.raises(S31AQualificationError):
        _verified_target(changed)


def test_static_receipt_requires_live_ci_evidence():
    data = json.loads(
        (ROOT / "docs/postmain-s31a-plan-receipt.json").read_text()
    )
    assert data["base_head"] == "5aff6711a33ed91800fb8bdf473ba8aebea25ce6"
    assert data["status"] == "PENDING_CI"
    assert data["qualification_requires"] == "S31A_REPORT.status == PASS"
    assert data["live_minecraft"] == "NOT_YET_VERIFIED"
    assert data["automatic_action_authorization"] is False
