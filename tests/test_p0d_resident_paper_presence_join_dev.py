"""#860 Stage22: independent Paper presence read-only auditor, fail-closed."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.resident_paper_presence_join_dev import (
    ResidentPaperJoinError,
    ResidentPaperVerdict,
    join_resident_paper_presence,
    parse_owned_paper_resident_trace,
    require_pre_inference_resident_presence,
)
from relay_self.world_resident_lifecycle_dev import (
    LogoutFenceEvidence,
    NativeLoginEvidence,
    WorldLifetime,
)

WORLD = "6502559a-84b7-4eb0-9040-bcbcc2d00874"
BOOT = "f3c136e9-cfd5-4c3b-a905-6060e7efda84"
A = "7d16bb8d-2a9a-4037-a3b6-9fddcb7ce01a"
B = "6d16bb8d-2a9a-4037-a3b6-9fddcb7ce01b"
PAPER = "paper-owned-stage22-boot"


def _line(kind, tick, actor, name, x=0, *,
          boot=BOOT, world=WORLD, y=64, z=0):
    return (
        f"[Server thread/INFO]: P0D_RESIDENT event={kind}"
        f" boot={boot} tick={tick} world={world}"
        f" actor={actor} name={name} x={x} y={y} z={z}"
        " source=PAPER_MAIN_THREAD"
    )


def _events(*, after_move=True, b_quit=False, wrong_rejoin=False,
            b_only_heartbeat=False, changed_world=False):
    data = [
        f"[Server thread/INFO]: P0D_RESIDENT_READY boot={BOOT}"
        " source=PAPER_MAIN_THREAD version=1",
        _line("JOIN", 10, A, "RelayA"),
        _line("JOIN", 11, B, "RelayB", 0),
        _line("PRESENT", 50, B, "RelayB", 0),
        _line("QUIT", 100, A, "RelayA"),
        _line(
            "PRESENT" if b_only_heartbeat else "MOVE",
            108, B, "RelayB", 0 if b_only_heartbeat else 0.8,
        ),
        _line("PRESENT", 145, B, "RelayB",
              0 if b_only_heartbeat else 0.8),
    ]
    if b_quit:
        data.append(_line("QUIT", 150, B, "RelayB", 0.8))
    data.append(_line(
        "JOIN", 160, B if wrong_rejoin else A, "RelayA", 0,
        world="5802559a-84b7-4eb0-9040-bcbcc2d00874"
        if changed_world else WORLD,
    ))
    return ("\n".join(data) + "\n").encode()


def _proofs():
    world = WorldLifetime(WORLD, "stage22-branch", PAPER, 0, 10)
    logout = LogoutFenceEvidence(
        "A", 0, "native-old-A",
        "original-issuer-validated", "cognition-file:/tmp/a",
        True, True, True, True, True, True,
    )
    login = NativeLoginEvidence(
        "A", 2, WORLD, "stage22-branch", PAPER, 0,
        "native-new-A", 161, "new-probe-source",
        True, True, True, True, True,
    )
    return world, logout, login


def _trace(contents=None):
    return parse_owned_paper_resident_trace(
        owned_paper_session_id=PAPER, expected_world_uuid=WORLD,
        owned_paper_log=_events() if contents is None else contents,
        log_ref="owned-paper-process-stdout-sha256-original",
    )


def _join(data=None, *, logout=None, login=None, b_before="native-B"):
    world, original_logout, original_login = _proofs()
    return join_resident_paper_presence(
        trace=_trace(data), world=world,
        a_name="RelayA", b_name="RelayB",
        a_logout=original_logout if logout is None else logout,
        a_relogin=original_login if login is None else login,
        original_b_native="native-B",
        surviving_b_native=b_before,
    )


def test_paper_player_move_after_a_quit_with_independent_a_rejoin():
    decision = _join()
    assert decision.status is ResidentPaperVerdict.MOVEMENT_CORRELATED
    assert decision.a_actor_uuid == A
    assert decision.b_actor_uuid == B
    assert decision.a_quit_tick == 100
    assert decision.b_later_tick == 145
    assert decision.a_rejoin_tick == 160
    assert decision.b_movement_m >= 0.8
    assert decision.prior_native_a == "native-old-A"
    assert decision.new_native_a == "native-new-A"
    assert decision.continuous_native_b == "native-B"
    assert not decision.native_action_caused_b_move
    assert not decision.physical_wal_action_attested
    assert not decision.actual_paper_source_authenticated_by_parser


def test_b_heartbeat_is_world_continuity_not_a_physical_move():
    decision = _join(_events(b_only_heartbeat=True))
    assert decision.status is ResidentPaperVerdict.PRESENCE_CORRELATED
    assert decision.b_movement_m == 0
    assert not decision.native_action_caused_b_move


@pytest.mark.parametrize(
    "data,match",
    [
        (_events(b_quit=True), "continuously"),
        (_events(wrong_rejoin=True), "collision"),
        (_events(changed_world=True), "stream"),
        (_events().replace(b"source=PAPER_MAIN_THREAD", b"source=NATIVE_STREAM"),
         "schema"),
        (_events().replace(b"tick=108", b"tick=90"), "inconsistent"),
        (_events().replace(b"x=0.8", b"x=nan"), "nonfinite"),
        (_events().replace(b"event=MOVE", b"event=JUMP"), "schema"),
        (_events().replace(b"world=" + WORLD.encode(),
                           b"world=5802559a-84b7-4eb0-9040-bcbcc2d00874"),
         "stream"),
    ],
)
def test_corrupt_or_foreign_paper_stream_never_proves_b_continuity(data, match):
    with pytest.raises(ResidentPaperJoinError, match=match):
        _join(data)


def test_no_b_after_a_quit_never_succeeds():
    rows = _events().decode().splitlines()
    rows = [row for row in rows if not (
        ("name=RelayB" in row and ("tick=108" in row or "tick=145" in row))
    )]
    with pytest.raises(ResidentPaperJoinError, match="after A quit"):
        _join(("\n".join(rows) + "\n").encode())


@pytest.mark.parametrize("change", [
    {"native_terminated": False},
    {"no_physical_inflight": False},
    {"physical_wal_clear": False},
    {"stale_gpu_fenced": False},
    {"peer_transport_drained": False},
    {"world_epoch": 1000},
])
def test_a_logout_requires_actual_original_owner_retirement(change):
    _, logout, _ = _proofs()
    with pytest.raises(ResidentPaperJoinError, match="source mismatch"):
        _join(logout=replace(logout, **change))


@pytest.mark.parametrize("change", [
    {"paper_session_id": "paper-owned-foreign"},
    {"native_session_id": "native-old-A"},
    {"new_native_source_verified": False},
    {"old_native_invalidated": False},
    {"world_epoch": 1},
    {"action_issue_authorized": True},
])
def test_a_relogin_must_be_new_source_scoped_process(change):
    _, _, login = _proofs()
    with pytest.raises(ResidentPaperJoinError, match="source mismatch"):
        _join(login=replace(login, **change))


def test_b_cannot_relog_during_a_logout_and_claim_continuous_session():
    with pytest.raises(ResidentPaperJoinError, match="source mismatch"):
        _join(b_before="native-restarted-B")


def test_paper_log_requires_exact_owned_session_not_global_latest():
    with pytest.raises(ResidentPaperJoinError, match="owned Paper"):
        parse_owned_paper_resident_trace(
            owned_paper_session_id="foreign-server",
            expected_world_uuid=WORLD, owned_paper_log=_events(),
            log_ref="untrusted-latest-log",
        )


def test_paper_main_thread_tick_and_native_world_time_are_not_compared():
    world, logout, login = _proofs()
    # Paper ticks 10..160 since this process boot; native day-clock can
    # legitimately be 24,161 in the same real World (time-of-day values).
    decision = join_resident_paper_presence(
        trace=_trace(), world=replace(world, world_tick=24161),
        a_name="RelayA", b_name="RelayB",
        a_logout=logout,
        a_relogin=replace(login, observed_world_tick=24161),
        original_b_native="native-B", surviving_b_native="native-B",
    )
    assert decision.status is ResidentPaperVerdict.MOVEMENT_CORRELATED


def _stage24g_before_model_lines():
    # Remove the final A rejoin: Gemma has not been invoked yet.
    return _events().decode().splitlines()[:-1]


def test_stage24g_paper_live_witness_before_gemma():
    source = ("\n".join(_stage24g_before_model_lines()) + "\n").encode()
    trace = _trace(source)
    require_pre_inference_resident_presence(
        trace, a_name="RelayA", b_name="RelayB",
    )


@pytest.mark.parametrize("fault", [
    "no-resident-boot",
    "old-p0b-only",
    "missing-b-after-a-quit",
    "duplicate-a-epoch",
])
def test_stage24g_pre_inference_never_substitutes_old_paper_telemetry(fault):
    lines = _stage24g_before_model_lines()
    if fault == "no-resident-boot":
        lines = lines[1:]
    if fault == "old-p0b-only":
        lines = [
            "[Server thread/INFO]: P0D_TICK_READY boot=" + BOOT,
            "[Server thread/INFO]: P0B_PLAYER tick=11 world=" + WORLD
            + " actor=" + B + " name=RelayB",
        ]
    if fault == "missing-b-after-a-quit":
        lines = lines[:-2]
    if fault == "duplicate-a-epoch":
        lines.append(_line("JOIN", 160, A, "RelayA"))
    raw = ("\n".join(lines) + "\n").encode()
    with pytest.raises(ResidentPaperJoinError):
        trace = _trace(raw)
        require_pre_inference_resident_presence(
            trace, a_name="RelayA", b_name="RelayB",
        )
