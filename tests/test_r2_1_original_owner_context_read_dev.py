"""R2-1: Owner-owned *read-only* Context entrypoint, no L1/product switch."""
from dataclasses import replace

import pytest

from relay_self.persistent_cognition import Memory, save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.r1_owner_context_shadow_dev import (
    R1ShadowStatus,
    compare_original_owner_r1_shadow,
    r1_shadow_is_live,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_r1_owner_context_shadow_dev import _args, _snapshot


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r2_1_original_resident_reads_context_without_new_owner_or_writes(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    resident = bridge.cognitive_work
    before_files, before_owners = _files(bridge), _snapshot(bridge)
    before_turns = dict(resident._coverage_adoption_turns)
    report = resident.read_context_shadow_cpu(**_args(case, sid))
    direct = compare_original_owner_r1_shadow(**_args(case, sid))
    assert report == direct and report.status is R1ShadowStatus.MATCH
    assert report.context is not None
    assert report.context.current.scope.self_id == sid
    assert report.context.current.coverage is EpistemicStatus.UNKNOWN
    assert report.context.recent.entries == ()
    assert report.context.retrieved.references == ()
    assert r1_shadow_is_live(
        report, bridge=bridge, boot=boot, world=world, links=links,
    )
    assert bridge.owners[sid] is resident.owners[sid]
    assert report.l1_input_switched is False
    assert report.physical_authorized is False
    assert report.memory_adopted is False
    assert _files(bridge) == before_files
    assert _snapshot(bridge) == before_owners
    assert dict(resident._coverage_adoption_turns) == before_turns


def test_r2_1_original_persisted_memory_is_read_by_digest_only(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    owner = bridge.owners["A"]
    owner.retain_memory(Memory(
        "r2-1-held-history",
        "prior observation does not certify this World's state",
        Provenance("prior-world", "previous-observation"),
        Provenance("original-owner", "retained"),
    ))
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    before_files, before_owners = _files(bridge), _snapshot(bridge)
    report = bridge.cognitive_work.read_context_shadow_cpu(
        **_args(case), memory_ids=("r2-1-held-history",),
    )
    assert report.status is R1ShadowStatus.MATCH
    item, = report.context.retrieved.references
    assert item.memory_id == "r2-1-held-history"
    assert item.status is EpistemicStatus.REMEMBERED
    assert item.applicability == "UNKNOWN"
    assert not hasattr(item, "content")
    assert _files(bridge) == before_files
    assert _snapshot(bridge) == before_owners
    owner.retained = replace(owner.retained, memories=())
    assert not r1_shadow_is_live(
        report, bridge=bridge, boot=case[2], world=case[3], links=case[4],
    )


@pytest.mark.parametrize("failure", (
    "foreign-owner", "foreign-resident", "foreign-self", "paper-session",
    "owner-epoch", "old-boot", "unknown-memory", "invalid-selector",
    "corrupt-original-disk",
))
def test_r2_1_read_boundary_fails_closed_for_unqualified_source(
    tmp_path, monkeypatch, failure,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    resident = bridge.cognitive_work
    args = _args(case)
    if failure == "foreign-owner":
        bridge.owners["A"] = bridge.owners["B"]
    elif failure == "foreign-resident":
        from types import SimpleNamespace

        args["bridge"] = SimpleNamespace(cognitive_work=object(),
                                         owners=bridge.owners)
    elif failure == "foreign-self":
        args["self_id"] = "Z"
    elif failure == "paper-session":
        bridge.paper._session_id = "foreign-paper-session"
    elif failure == "owner-epoch":
        resident._states["A"].epoch += 1
    elif failure == "old-boot":
        args["boot"] = replace(boot, paper_boot_id="foreign-boot")
    elif failure == "unknown-memory":
        args["memory_ids"] = ("not-originally-retained",)
    elif failure == "invalid-selector":
        args["recent_limit"] = 0
    elif failure == "corrupt-original-disk":
        bridge.owners["A"].files.cognition_file.write_text('{"corrupt":true}')

    before = _files(bridge)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.read_context_shadow_cpu(**args)
    assert _files(bridge) == before


def test_r2_1_cached_context_revokes_after_paper_advances(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    report = bridge.cognitive_work.read_context_shadow_cpu(**_args(case))
    assert report.status is R1ShadowStatus.MATCH
    bridge.paper._session_id = "new-paper-session"
    assert not r1_shadow_is_live(
        report, bridge=bridge, boot=case[2], world=case[3], links=case[4],
    )
    with pytest.raises(ResidentCognitiveWorkError):
        bridge.cognitive_work.read_context_shadow_cpu(**_args(case))


def test_r2_1_live_source_drift_during_read_fails_closed(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    resident = bridge.cognitive_work
    original = resident.read_present_cpu
    calls = 0

    def mutate_external_paper(**kw):
        nonlocal calls
        result = original(**kw)
        calls += 1
        if calls == 2:
            bridge.paper._session_id = "changed-during-read"
        return result

    monkeypatch.setattr(resident, "read_present_cpu", mutate_external_paper)
    with pytest.raises(ResidentCognitiveWorkError):
        resident.read_context_shadow_cpu(**_args(case))
