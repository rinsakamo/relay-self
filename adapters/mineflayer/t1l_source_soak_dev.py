"""T1l bounded 20TPS-source DEV soak on the original T1e receiver.

No Motor actions, no synthetic ticks, no tick/TPS actuator, no P1 qualified WAIT.
The native Paper subscription is capped at 2400 causal challenges; do not
silently wrap/reset its sequence or extend its source lifetime.
"""
from __future__ import annotations

from adapters.mineflayer.t1f_continuation_dev import next_tick, _latch_source_loss
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from adapters.mineflayer.t1l_source_diagnostic_dev import CHALLENGE_CAP


class SoakDevRejected(ValueError):
    """Source discontinuity, budget exhaustion, native death or unknown frame."""


async def run_source_soak(session, report, *, accounted_ticks: int,
                          maximum_index: int = 2300, checkpoint_every: int = 200):
    if (type(accounted_ticks) is not int or not 100 <= accounted_ticks <= 2000
            or type(maximum_index) is not int
            or not 100 <= maximum_index <= CHALLENGE_CAP
            or checkpoint_every != 200
            or getattr(session, "source_lost", False)
            or getattr(session, "tick_owner", None) is not None):
        raise SoakDevRejected("T1l separate bounded source-only DEV scope required")
    owner = TickAccounting(session.started.session_id)
    session.tick_owner = owner
    report["t1l"] = {
        "classification": "T1L_SOURCE_CONTINUITY_BOUNDED_DEV",
        "target_accounted_ticks": accounted_ticks, "checkpoints": [],
        "new_action_count": 0, "p1_qualified_wait": False,
        "source_independently_authenticated": False,
        "known_challenge_limit": CHALLENGE_CAP,
        "effective_stop_index": maximum_index,
    }
    last_seq = -1
    try:
        # The normal T1e owner already subscribed on the same session.
        # The first Paper sample establishes a baseline, not a charged tick.
        first = await next_tick(session)
        last_seq = first.seq
        index = first.data["snapshot"]["index"]
        if index + accounted_ticks >= maximum_index:
            raise SoakDevRejected("T1l requested soak would reach challenge budget")
        while len(owner.rows) < accounted_ticks:
            frame = await next_tick(session, after_seq=last_seq)
            last_seq = frame.seq
            if frame.data["snapshot"]["index"] >= maximum_index:
                raise SoakDevRejected("T1l bounded protocol challenge budget reached")
            if getattr(session, "source_lost", False) or owner.failed:
                raise SoakDevRejected("T1l owner source lost")
            if len(owner.rows) and len(owner.rows) % checkpoint_every == 0:
                end = owner.rows[-1]
                if (not report["t1l"]["checkpoints"]
                        or report["t1l"]["checkpoints"][-1]["accounted_ticks"]
                        != len(owner.rows)):
                    report["t1l"]["checkpoints"].append({
                        "accounted_ticks": len(owner.rows),
                        "source_seq": end["source_seq"],
                        "world_tick": end["world_tick"],
                        "energy_last_known": owner.energy.body.energy,
                        "fatigue_last_known": owner.fatigue.fatigue,
                        "credit_count": owner.energy.credit_count,
                    })
        if (owner.failed or owner.active_action is not None or owner.pending_meal
                or owner.previous is None or len(owner.rows) != accounted_ticks
                or getattr(session, "source_lost", False)
                or session.process_returncode is not None):
            raise SoakDevRejected("T1l source, ledger or process not live")
        out = report["t1l"]
        out.update({
            "first_accounted_world_tick": owner.rows[0]["world_tick"],
            "last_accounted_world_tick": owner.rows[-1]["world_tick"],
            "first_source_seq": owner.rows[0]["source_seq"],
            "last_source_seq": owner.rows[-1]["source_seq"],
            "accounted_ticks": len(owner.rows),
            "accounted_world_ticks_consecutive": (
                owner.rows[-1]["world_tick"] - owner.rows[0]["world_tick"] + 1
                == len(owner.rows)),
            "m0_credit_count": owner.energy.credit_count,
            "m0_energy_last_known": owner.energy.body.energy,
            "p1_fatigue_last_known": owner.fatigue.fatigue,
            "p1_qualified_wait": False,
            "no_issued_motor_or_eat_actions": True,
        })
        report["status"] = "PASS"
        return out
    except BaseException:
        _latch_source_loss(session)
        report["t1l"]["status"] = "FAIL_CLOSED"
        report["t1l"]["accounted_ticks_before_failure"] = len(owner.rows)
        raise
