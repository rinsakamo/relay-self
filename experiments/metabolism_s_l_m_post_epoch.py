"""S/L/M post-epoch passive tap: explicit opt-in after original owner decisions.

Caller owns native probe, S epoch coordination, B0 decision and any L8
experience. This module is a read-only adapter, not a runtime loop,
a separate action issuer, another sensor owner or a goal policy.
"""
from __future__ import annotations

from dataclasses import dataclass

from experiments.metabolism_b0_cognition import read_b0_resource_context
from experiments.metabolism_l8_resource_shadow import (
    SL8MResourceContrast,
    contrast_l8_with_m_resource,
)
from experiments.metabolism_s_epoch_resource import (
    PostSEpochResourceObservation,
    observe_completed_s_resource_epoch,
)


class SLMPostEpochRejected(ValueError):
    """The owner did not supply one coherent post-decision source boundary."""


@dataclass(frozen=True, slots=True)
class SLMPostEpochReadout:
    """Result of a passive one-probe read; never a new decision or Action."""

    session_id: str
    probe_seq: int
    request_id: str
    self_id: str
    epoch_id: str
    b0_owner_tick: int
    b0_original_l0_kind: str
    m: PostSEpochResourceObservation
    l8_m: SL8MResourceContrast | None
    source_scope: str = "S_L_M_POST_EPOCH_OWNER_PROVIDED_DEV_UNQUALIFIED"
    source_attested: bool = False
    action_authority: bool = False
    action_issues: int = 0
    new_native_reads: int = 0
    new_cognition_calls: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    food_credits: int = 0


def read_s_l_m_after_owner_epoch(
    *,
    probe: object,
    native: object,
    ledger: object,
    original_b0_decision: object,
    original_s_epoch: object,
    retained: object,
    self_id: str,
    epoch_id: str,
    learning: object | None = None,
    retention_enabled: bool | None = None,
    noise_bound: float | None = None,
) -> SLMPostEpochReadout:
    """Read existing owner objects *without* driving any of their lifecycles.

    S must already have obtained its native probe, B0 owner decision and
    original S coordinator result. If L8 is enabled, the caller supplies
    a previously computed source/goal-admitted next-epoch learning snapshot.
    Neither S49 execution nor B0 feeding is called here.

    B0's owner config and calibration are read from that exact ledger rather
    than caller-supplied copies. This does not independently attest Minecraft
    bytes, B0 calibration or any real S49 locomotion cost.
    """
    # Import product adapters lazily: independent M branch intentionally does
    # not own or copy source files from the S #634 product branch.
    from adapters.mineflayer.b0_energy_bridge import B0Decision, B0EnergyLedger
    from adapters.mineflayer.python_protocol import MineflayerObservation
    from adapters.mineflayer.s34_native_world_cognition_ci import NativeThreat
    from adapters.mineflayer.self_body_m0_projection import compose_b0_cognition_views

    if (
        not isinstance(probe, MineflayerObservation)
        or not isinstance(native, NativeThreat)
        or native.observation is not probe
        or not isinstance(ledger, B0EnergyLedger)
        or not isinstance(original_b0_decision, B0Decision)
        or ledger.session_id != probe.session_id
        or type(self_id) is not str or not self_id
        or type(epoch_id) is not str or not epoch_id
        or (learning is None) != (retention_enabled is None)
        or (retention_enabled is not None and type(retention_enabled) is not bool)
        or not hasattr(ledger, "config")
        or not hasattr(ledger, "sensor")
    ):
        raise SLMPostEpochRejected(
            "same original native/B0 source and explicit L8 opt-in required"
        )

    before = (
        ledger.body, ledger.credit_count,
        ledger._last_decision_seq, ledger._last_eat_seq,
    )
    try:
        views = compose_b0_cognition_views(
            probe, ledger, original_b0_decision,
            self_id=self_id, epoch_id=epoch_id,
        )
        resource = read_b0_resource_context(
            views, owner_decision=original_b0_decision,
            config=ledger.config, sensor=ledger.sensor, noise_bound=noise_bound,
        )
        s_m = observe_completed_s_resource_epoch(
            original_s_epoch, native=native, retained=retained, body=resource,
        )
        joined = None
        if learning is not None:
            from relay_self.l1_epoch_observer import observe_s_epoch_l1

            l8 = observe_s_epoch_l1(
                original_s_epoch, native=native, retained=retained,
                learning=learning, retention_enabled=retention_enabled,
            )
            joined = contrast_l8_with_m_resource(
                l8, s_m, native=native, retained=retained,
                learning=learning, retention_enabled=retention_enabled,
            )
        if before != (
            ledger.body, ledger.credit_count,
            ledger._last_decision_seq, ledger._last_eat_seq,
        ):
            raise SLMPostEpochRejected("original B0 owner mutated during passive tap")
    except (ValueError, TypeError, AttributeError) as exc:
        raise SLMPostEpochRejected(
            "original S/B0/L8 post-epoch join or source admission rejected"
        ) from exc

    return SLMPostEpochReadout(
        session_id=probe.session_id,
        probe_seq=probe.seq,
        request_id=probe.request_id,
        self_id=self_id, epoch_id=epoch_id,
        b0_owner_tick=original_b0_decision.body_tick,
        b0_original_l0_kind=original_b0_decision.kind,
        m=s_m,
        l8_m=joined,
    )
