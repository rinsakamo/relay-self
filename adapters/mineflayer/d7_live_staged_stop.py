"""D7-E: current-World DEV stationary readback, never an Action issuer.

Verifies physical stillness AFTER genuine operator-staged pickup by combining
the original S49 S15 clear ACK from the same-client S50 stream, and contiguous
Paper main-thread actual body x/z/velocity/inputs. It cannot attest the exact
Paper-effective tick of the original clear packet. Qualification/SCIENCE
remain separate. Only the live original S49 owner may consume this evidence.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

CONTROL_KEYS = ("forward", "back", "left", "right", "jump", "sprint", "sneak")
PAPER = "PAPER_SERVER_MAIN_THREAD_V1"
CLIENT = "S50_DEV_NATIVE_READBACK_V1"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
STAGED = re.compile(
    rf"RSELF_LOOT_STAGED world=(?P<world>{UUID}) owner=(?P<player>{UUID}) "
    rf"entity=(?P<item>{UUID}) item=rotten_flesh count=1 "
    r"tick=(?P<tick>\d+) source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP "
    r"mode=BACK_2_2M"
)
NATURAL_SPAWN = re.compile(
    rf"RSELF_NATURAL_DROP_SPAWN world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) item=(?P<item>{UUID}) "
    r"tick=(?P<tick>\d+) rotten_count=(?P<count>[12]) "
    r"source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH"
)
NATURAL_PICKUP = re.compile(
    rf"RSELF_NATURAL_DROP_PICKUP world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) item=(?P<item>{UUID}) "
    rf"player=(?P<player>{UUID}) tick=(?P<tick>\d+) "
    r"rotten_count=(?P<count>[12]) source=ACTUAL_PAPER_ITEM_PICKUP"
)
NATURAL_DEATH = re.compile(
    rf"RSELF_NATURAL_DROP_DEATH world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) tick=(?P<tick>\d+) "
    rf"rotten_count=(?P<count>[12]) killer=(?P<killer>{UUID}) "
    r"source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true"
)
PICKED = re.compile(
    rf"RSELF_LOOT_PICKED world=(?P<world>{UUID}) owner=(?P<player>{UUID}) "
    rf"entity=(?P<item>{UUID}) item=rotten_flesh count=1 "
    r"tick=(?P<tick>\d+) source=ACTUAL_PAPER_PICKUP_EVENT"
)


class D7LiveStopRejected(ValueError):
    """Original physical body is not eligible for DEV post-MOVE food."""


@dataclass(frozen=True, slots=True)
class D7LiveStopSource:
    session_id: str
    action_id: str
    original_clear_seq: int
    paper_world_uuid: str
    paper_player_uuid: str
    paper_item_uuid: str
    paper_pickup_tick: int
    paper_last_tick: int
    paper_quiet_tail_ticks: int
    client_postclear_physics_ticks: int
    classification: str = "D7_E_DEV_LIVE_STAGED_BODY_STEADY_SOURCE"
    server_effective_original_clear_tick: str = "NOT_CAUSALLY_ATTESTED"
    original_attack_effect_seq: int | None = None


def _kv(line: str, marker: str) -> dict[str, str]:
    if marker not in line:
        raise D7LiveStopRejected("Paper source marker missing")
    d = {}
    for token in line.split(marker, 1)[1].split():
        if "=" not in token:
            raise D7LiveStopRejected("Paper token missing equals")
        k, v = token.split("=", 1)
        if not k or not v or k in d:
            raise D7LiveStopRejected("Paper duplicate/blank token")
        d[k] = v
    return d


def _int(row: dict, key: str) -> int:
    val = row.get(key)
    try:
        n = int(val)
    except (ValueError, TypeError) as exc:
        raise D7LiveStopRejected(f"invalid Paper {key}") from exc
    if n < 0 or str(n) != val:
        raise D7LiveStopRejected(f"noncanonical Paper {key}")
    return n


def _float(row: dict, key: str) -> float:
    try:
        n = float(row[key])
    except (KeyError, ValueError, TypeError) as exc:
        raise D7LiveStopRejected(f"invalid Paper {key}") from exc
    if not math.isfinite(n):
        raise D7LiveStopRejected(f"nonfinite Paper {key}")
    return n


def _paper_off(row: dict) -> bool:
    if any(row.get(k) not in ("true", "false") for k in CONTROL_KEYS):
        raise D7LiveStopRejected("incomplete Paper seven held controls")
    return all(row[k] == "false" for k in CONTROL_KEYS)


def _client_off(row: dict) -> bool:
    d = row.get("controls")
    if not isinstance(d, dict) or set(d) != set(CONTROL_KEYS):
        raise D7LiveStopRejected("incomplete S50 direct client controls")
    if any(type(v) is not bool for v in d.values()):
        raise D7LiveStopRejected("nonboolean S50 held input")
    return not any(d.values())


def read_d7_live_staged_stop(
    paper_log: str, client_jsonl: str, *,
    session_id: str, action_id: str, clear_seq: int,
    original_stage_line: str, original_pickup_line: str,
    source_kind: str = "staged",
    original_death_line: str | None = None,
) -> D7LiveStopSource:
    """Fail closed on missing/cross-session/source/clock/last-tick evidence.

    This readout **cannot** manufacture a STOP Action, a non-motion grant,
    a server packet ACK, or a natural-drop claim. It belongs to current
    original live S49 owner only, before one S51 EAT issuance.
    """
    if (
        not isinstance(session_id, str) or not session_id
        or not isinstance(action_id, str) or not action_id
        or type(clear_seq) is not int or clear_seq < 0
        or not isinstance(paper_log, str) or not isinstance(client_jsonl, str)
        or not isinstance(original_stage_line, str)
        or not isinstance(original_pickup_line, str)
        or source_kind not in ("staged", "natural", "natural_multi", "natural_multi_passive")
    ):
        raise D7LiveStopRejected("source-scoped current S49 action required")
    lines = paper_log.splitlines()
    if (
        sum("RSELF_D7_PAPER_READY " in s for s in lines) != 1
        or any("RSELF_D7_PAPER_TRUNCATED " in s for s in lines)
        or any("RSELF_D7_PAPER_STOP " in s for s in lines)
    ):
        raise D7LiveStopRejected("Paper observer is not active/nontruncated")
    if source_kind == "staged":
        stages = [m for s in lines if (m := STAGED.search(s))]
        picks = [m for s in lines if (m := PICKED.search(s))]
        if len(stages) != 1 or len(picks) != 1:
            raise D7LiveStopRejected("exact one real staged+picked Paper UUID required")
        st, pk = stages[0].groupdict(), picks[0].groupdict()
        if (
            STAGED.search(original_stage_line) is None
            or PICKED.search(original_pickup_line) is None
            or STAGED.search(original_stage_line).groupdict() != st
            or PICKED.search(original_pickup_line).groupdict() != pk
            or any(st[k] != pk[k] for k in ("world", "player", "item"))
            or int(st["tick"]) >= int(pk["tick"])
        ):
            raise D7LiveStopRejected("original staged Paper pickup UUID provenance mismatch")
        classification = "D7_E_DEV_LIVE_STAGED_BODY_STEADY_SOURCE"
    else:
        spawns = [m for s in lines if (m := NATURAL_SPAWN.search(s))]
        picks = [m for s in lines if (m := NATURAL_PICKUP.search(s))]
        deaths = [m for s in lines if (m := NATURAL_DEATH.search(s))]
        required = 2 if source_kind in ("natural_multi", "natural_multi_passive") else 1
        if (
            len(spawns) != required or len(picks) != required
            or len(deaths) != required
            or not isinstance(original_death_line, str)
            or NATURAL_SPAWN.search(original_stage_line) is None
            or NATURAL_PICKUP.search(original_pickup_line) is None
            or NATURAL_DEATH.search(original_death_line) is None
        ):
            raise D7LiveStopRejected("true natural Paper spawn/pickup/death missing")
        # The exact *current* generation must be explicitly selected from
        # original Paper lines, not the first zombie from historical log.
        st, pk, death = (
            NATURAL_SPAWN.search(original_stage_line).groupdict(),
            NATURAL_PICKUP.search(original_pickup_line).groupdict(),
            NATURAL_DEATH.search(original_death_line).groupdict(),
        )
        if (
            sum(m.groupdict() == st for m in spawns) != 1
            or sum(m.groupdict() == pk for m in picks) != 1
            or sum(m.groupdict() == death for m in deaths) != 1
        ):
            raise D7LiveStopRejected("chosen Paper generation absent/duplicated")
        if source_kind in ("natural_multi", "natural_multi_passive"):
            earlier_death, earlier_spawn, earlier_pickup = (
                deaths[0].groupdict(), spawns[0].groupdict(), picks[0].groupdict(),
            )
            if (
                death != deaths[-1].groupdict()
                or st != spawns[-1].groupdict()
                or pk != picks[-1].groupdict()
                or any(
                    earlier_death[key] != earlier_spawn[key]
                    for key in ("world", "zombie", "count")
                )
                or any(
                    earlier_spawn[key] != earlier_pickup[key]
                    for key in ("world", "zombie", "item", "count")
                )
                or earlier_death["killer"] != earlier_pickup["player"]
                or earlier_death["world"] != death["world"]
                or earlier_death["zombie"] == death["zombie"]
                or earlier_spawn["item"] == st["item"]
                or not (
                    int(earlier_death["tick"]) <= int(earlier_spawn["tick"])
                    < int(earlier_pickup["tick"]) < int(death["tick"])
                )
            ):
                raise D7LiveStopRejected("prior Paper generation source not closed")

        if (
            st != NATURAL_SPAWN.search(original_stage_line).groupdict()
            or pk != NATURAL_PICKUP.search(original_pickup_line).groupdict()
            or sum(
                NATURAL_DEATH.search(s) is not None
                and NATURAL_DEATH.search(s).groupdict() == death
                for s in lines
            ) != 1
            or any(st[k] != pk[k] for k in ("world", "zombie", "item"))
            or any(death[k] != st[k] for k in ("world", "zombie", "count"))
            or pk["count"] != st["count"]
            or pk["player"] != death["killer"]
            or not int(death["tick"]) <= int(st["tick"]) < int(pk["tick"])
            or "RSELF_LOOT_STAGED " in paper_log
        ):
            raise D7LiveStopRejected("Paper natural zombie killer/item lineage invalid")
        st["player"] = pk["player"]
        classification = (
            "D8_DEV_LIVE_SECOND_NATURAL_PASSIVE_PICKUP_STEADY_SOURCE"
            if source_kind == "natural_multi_passive"
            else (
                "D8_DEV_LIVE_SECOND_NATURAL_BODY_STEADY_SOURCE"
                if source_kind == "natural_multi"
                else "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
            )
        )
    pickup_tick = int(pk["tick"])
    stream = [_kv(s, "RSELF_D7_PAPER_TICK ")
              for s in lines if "RSELF_D7_PAPER_TICK " in s]
    if not 8 <= len(stream) <= 8192:
        raise D7LiveStopRejected("insufficient/current Paper source")
    last_tick = None
    tail = 0
    previous_xz = None
    for idx, row in enumerate(stream, 1):
        tick = _int(row, "tick")
        if (
            row.get("source") != PAPER
            or row.get("world") != st["world"]
            or row.get("player") != st["player"]
            or _int(row, "ordinal") != idx
            or (last_tick is not None and tick != last_tick + 1)
            or row.get("ground") not in ("true", "false")
        ):
            raise D7LiveStopRejected("Paper current tick/identity drift")
        last_tick = tick
        off = _paper_off(row)
        x = _float(row, "x")
        z = _float(row, "z")
        _float(row, "y")
        vx, vz = _float(row, "vx"), _float(row, "vz")
        _float(row, "vy")
        stationary = (
            tick > pickup_tick and off and row["ground"] == "true"
            and previous_xz is not None
            and math.hypot(x-previous_xz[0], z-previous_xz[1]) <= 0.01
            and math.hypot(vx, vz) <= 0.01
        )
        tail = tail + 1 if stationary else 0
        previous_xz = (x, z)
    if last_tick is None or last_tick < pickup_tick + 8 or tail < 8:
        raise D7LiveStopRejected("latest Paper after real pickup not stationary 8 ticks")

    records = []
    for line in client_jsonl.splitlines():
        try:
            o = json.loads(line)
        except (ValueError, TypeError) as exc:
            raise D7LiveStopRejected("S50 source truncated/malformed") from exc
        if not isinstance(o, dict):
            raise D7LiveStopRejected("S50 record must be object")
        records.append(o)
    if not 12 <= len(records) <= 9000:
        raise D7LiveStopRejected("S50 original client source incomplete")
    if records[0].get("kind") != "SESSION_START":
        raise D7LiveStopRejected("S50 same-client SESSION_START missing")
    clear_index = None
    ticks_after = 0
    last_client_tick = -1
    for index, row in enumerate(records, 1):
        if (
            row.get("source") != CLIENT
            or row.get("session_id") != session_id
            or row.get("ordinal") != index
            or type(row.get("client_physics_tick")) is not int
            or row["client_physics_tick"] < last_client_tick
        ):
            raise D7LiveStopRejected("S50 session/monotonic client source mismatch")
        last_client_tick = row["client_physics_tick"]
        kind = row.get("kind")
        if kind == "SHUTDOWN_ACK":
            raise D7LiveStopRejected("S50 session closed before owner STOP")
        anchor_id = (
            action_id if source_kind == "natural_multi_passive"
            else action_id + "-s15-clear"
        )
        if kind == "EFFECT_ACK" and (
            row.get("native_action_id") == anchor_id
            and row.get("native_seq") == clear_seq
        ):
            if clear_index is not None or not _client_off(row):
                raise D7LiveStopRejected("duplicate/held original S15 clear")
            clear_index = index
        if clear_index is not None and index >= clear_index:
            if kind not in ("EFFECT_ACK", "PHYSICS_TICK", "PROBE", "SESSION_START"):
                raise D7LiveStopRejected("unexpected client source after clear")
            if not _client_off(row):
                raise D7LiveStopRejected("post-clear native motor input reactivated")
            if kind == "PHYSICS_TICK" and index > clear_index:
                ticks_after += 1
    if clear_index is None or ticks_after < 8:
        raise D7LiveStopRejected("same S49 clear not confirmed by 8 client ticks")
    return D7LiveStopSource(
        session_id=session_id, action_id=action_id,
        original_clear_seq=(
            -1 if source_kind == "natural_multi_passive" else clear_seq
        ),
        original_attack_effect_seq=(
            clear_seq if source_kind == "natural_multi_passive" else None
        ),
        server_effective_original_clear_tick=(
            "NOT_APPLICABLE_NO_MOVE"
            if source_kind == "natural_multi_passive"
            else "NOT_CAUSALLY_ATTESTED"
        ),
        paper_world_uuid=st["world"], paper_player_uuid=st["player"],
        paper_item_uuid=st["item"], paper_pickup_tick=pickup_tick,
        paper_last_tick=last_tick, paper_quiet_tail_ticks=tail,
        client_postclear_physics_ticks=ticks_after,
        classification=classification,
    )
