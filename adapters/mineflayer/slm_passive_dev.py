"""Explicit S49 DEV owner wiring; diagnostics are drained after Action loop.

One B0 model ledger is owned here because ordinary S49 has none. It is not
Minecraft physiological accounting. No B0 step/food credit, training labels,
learning retention, policy override, native reader or Action issuer is added.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from experiments.metabolism_s49_live_probe_bridge import S49PassiveSourceLease
from experiments.metabolism_slm_dev_host_tap import bounded_s_l_m_audit_row
from relay_self.contextual_shadow import ShadowContext, ShadowSpecification
from relay_self.habit_shadow import GoalSourceAdmission
from relay_self.learning_epoch import advance_learning_epoch
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.runtime_coordination import coordinate_decision_epoch


class S49SLMDevOwner:
    """Bound once by S49 to its real host and existing Executor supervisor."""

    def __init__(
        self, *, self_id: str = "s49-slm-dev",
        retention_enabled: bool = False,
    ):
        if type(retention_enabled) is not bool:
            raise ValueError("L8 shadow retention flag must be explicit bool")
        self.self_id = self_id
        self.retention_enabled = retention_enabled
        self.host = self.supervisor = self.ledger = None
        self.pending = []
        self.current = None
        self.errors = 0
        self.drained = False

    def bind(self, host, supervisor):
        if self.host is not None or host.events or supervisor.open_actions:
            raise ValueError("fresh sole S49 owner required")
        self.host, self.supervisor = host, supervisor
        self.ledger = B0EnergyLedger(host.session_id)
        host.slm_dev_owner = self

    async def observe(self, probe):
        # Bounded source-only capture. No B0/cognition/serialization before L0.
        if self.host is None or len(self.pending) >= 3 or self.drained:
            self.current = None
            self.errors += 1
            return
        lease = S49PassiveSourceLease(enabled=True, max_probes=1)
        await lease.observe(probe)
        self.current = (probe, lease)

    def coordinate_original_choice(self, native, retained, original_choice):
        # The original selector runs exactly once here; no fabricated S42 result.
        epoch = coordinate_decision_epoch(
            self.supervisor, at_ns=self.supervisor.last_at_ns or 0,
            provenance=native.observation.provenance,
            decision_step=lambda: native, relay_engine=original_choice,
        )
        try:
            source = self.current
            self.current = None
            if source is None or source[0] is not native.observation or len(self.pending) >= 3:
                raise ValueError("missing original source lease")
            self.pending.append((source[1], native, retained, epoch))
        except Exception:
            self.errors += 1
        return epoch.cognition_result

    def finish(self, actions):
        if self.drained:
            raise ValueError("diagnostics already drained")
        self.drained = True
        rows = []
        pending, self.pending = self.pending, []
        for lease, native, retained, epoch in pending:
            probe = native.observation
            try:
                # Explicit sole B0 owner decision on the saved original probe.
                decision = self.ledger.decide(probe)
                digest = hashlib.sha256(json.dumps(
                    asdict(probe), sort_keys=True, separators=(",", ":"),
                ).encode()).hexdigest()
                cognition = PersistentCognition(IdentitySpecification(
                    self.self_id, ("observe original S49 epochs",),
                    Provenance("slm-dev", "empty-memory-no-training"),
                ))
                learning = advance_learning_epoch(
                    cognition, current_self_id=self.self_id,
                    current=ShadowContext(
                        probe.session_id, probe.seq, digest, ("native_probe",), probe.provenance,
                    ),
                    admitted_current_probe_sha256=frozenset({digest}),
                    specification=ShadowSpecification(
                        ("native_probe", "near_zombie"), ("MOVE_AWAY", "WAIT"),
                    ),
                    no_memory_action_ref=epoch.cognition_result.selection.value,
                    previous_goal_labels=(), new_episodes=(), new_goal_labels=(),
                    source_admission=GoalSourceAdmission(frozenset(), frozenset()),
                    integration_provenance=Provenance("slm-dev", "no-goal-training"),
                    retention_enabled=self.retention_enabled,
                )
                result = lease.observe_after_original_s_epoch(
                    original_s_epoch=epoch, native=native, ledger=self.ledger,
                    original_b0_decision=decision, retained=retained,
                    self_id=self.self_id, epoch_id=f"s49-probe-{probe.seq}",
                    learning=learning, retention_enabled=self.retention_enabled,
                )
                row = bounded_s_l_m_audit_row(result)
                row["self_id"] = self.self_id
                row["epoch_id"] = f"s49-probe-{probe.seq}"
                row["selfbody_projection"] = "compose_b0_cognition_views via original M tap"
                row["s42_cognition_completed"] = epoch.cognition_requested
                row["b0_owner_tick"] = decision.body_tick
                row["probe_object_sha256"] = digest
                row["digest_scope"] = "DECODED_OBJECT_NOT_RAW_NATIVE_BYTES"
                row["action_outcomes"] = [
                    dict(a) for a in actions if a["probe_seq"] == probe.seq
                ]
                rows.append(row)
            except Exception:
                self.errors += 1
                rows.append({"status": "OBSERVER_ERROR", "probe_seq": probe.seq})
        return {"classification": "DEV_ONLY", "rows": rows, "observer_errors": self.errors,
                "l8_retention_enabled": self.retention_enabled, "model_calls": 0,
                "b0_scope": "MODEL_ONLY_NOT_MINECRAFT_BODY_ACCOUNTING"}
