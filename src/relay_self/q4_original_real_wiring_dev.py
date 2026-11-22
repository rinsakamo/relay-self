"""Q4 diagnostic for safely bringing the Original Owner PLACE into real DEV.

This is a read-only compatibility audit, NOT a World launcher, execution
permit, model result or original external source attestation. The historical
I4a synthetic issuer must NEVER be treated as an active real motor path.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import begin_physical_issue_dev
from experiments.cognitive_physical_place_move_issue_dev import (
    Stage27PlaceMoveReceipt,
    complete_prepared_place_move_dev,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


@dataclass(frozen=True, slots=True)
class Q4OriginalRealWiringAudit:
    """An inventory of unresolved source/issuer interfaces, not a grant."""

    implemented_receipt: bool
    implemented_shared_executor: bool
    missing_original_interfaces: tuple[str, ...]
    synthetic_only_s2_api: bool = True
    real_world_authorized: bool = False


def audit_q4_original_live_wiring_cpu() -> Q4OriginalRealWiringAudit:
    """Identify concrete missing links without constructing an Action.

    The historical Stage27 executor and read-only WAL window have been
    restored to the unified tree. Original I4a's synthesis-only reservation
    still depends on historical physical/transaction methods not present in
    the unified B authority, plus a PLACE-specific WAL reservation contract.
    Never infer that importability or CI permits real motor execution.
    """
    physical = PhysicalIssueAdmission
    missing = tuple(
        name for name in (
            "original_i4a_s2_first_wal_window",
            "require_original_i4a_s2_wal_window",
            "consume_original_i4a_s2_action_once",
        ) if not callable(getattr(physical, name, None))
    )
    wal_parameters = inspect.signature(begin_physical_issue_dev).parameters
    if not {"place_invocation", "place_motion"}.issubset(wal_parameters):
        missing += ("original_place_wal_reservation",)
    # A first-action PLACE reservation does not implement the S1-prefix
    # transaction or Stage27's prior-terminal option.
    if "i4a_s2_boundary" not in wal_parameters:
        missing += ("original_place_s2_wal_reservation",)
    if "allow_prior_original_place_terminals" not in wal_parameters:
        missing += ("original_place_prior_terminal_reservation",)
    if not callable(getattr(physical, "quiescent_wal_history_window", None)):
        missing += ("quiescent_wal_history_window",)
    # These are deliberate no-positive-result fixtures. The original
    # ProcessSession class is named here only to keep explicit the real
    # adapter type; no instance is launched or read.
    _ = MineflayerProcessSession
    return Q4OriginalRealWiringAudit(
        implemented_receipt=inspect.isclass(Stage27PlaceMoveReceipt),
        implemented_shared_executor=inspect.iscoroutinefunction(
            complete_prepared_place_move_dev,
        ),
        missing_original_interfaces=missing,
    )
