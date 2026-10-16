"""R purely offline PREWORLD source/profile contract for a new M0.2 qualifier.

No java, network, filesystem mutation, science/DEV upgrades or grant use.
Caller-provided data must NEVER substitute for independently fetched source.
"""
from __future__ import annotations

import re
from typing import Any

CLASS = "R_M02_V7_NEW_PLUGIN_PREWORLD_SHAPE_ONLY_NOT_ADMITTED"
OLD_SPENT_GRANT = "USER_M02_PAPER_QUALIFICATION_20261015_THIRD_ONCE"
NEW_SPENT_GRANT = "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE"
SPENT_GRANTS = frozenset({OLD_SPENT_GRANT, NEW_SPENT_GRANT})
PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
BASE_CONFIG_SHA = "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e"
OLD_PLUGIN_SHA = "0ed8a00a7ebf577bdbea361e2c6facf7ed4b24001c017d362823da5cb60398e5"
ARM = "BASE_ON"


class PreworldRejected(ValueError):
    pass


def check(ok: bool, message: str) -> None:
    if not ok:
        raise PreworldRejected(message)


def full_digest(value: Any) -> bool:
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def review_candidate(x: dict[str, Any]) -> dict[str, Any]:
    """Validate a non-authoritative proposal; do NOT authorize any physical run.

    Hash shapes and self-reported CI success are never source attestation.
    """
    check(type(x) is dict and set(x) == {
        "s_exact_head", "r_exact_head", "plugin_sha256", "paper_sha256",
        "config_sha256", "arm", "grant_id", "qualification_run_id",
        "source_evidence_root", "source_ci_run_id",
        "independent_r_receipt", "previous_grants_reused",
        "new_java_starts", "new_node_sessions", "scientific_trials",
    }, "incomplete preworld proposal fields")
    for key in ("s_exact_head", "r_exact_head"):
        check(type(x[key]) is str
              and re.fullmatch("[0-9a-f]{40}", x[key]) is not None,
              "unknown source head shape")
    for key in ("plugin_sha256", "paper_sha256", "config_sha256"):
        check(full_digest(x[key]), "unidentified candidate binary/config digest")
    check(x["plugin_sha256"] != OLD_PLUGIN_SHA,
          "historical qualified plugin substituted for new plugin")
    check(x["paper_sha256"] == PAPER_SHA
          and x["config_sha256"] == BASE_CONFIG_SHA
          and x["arm"] == ARM,
          "unregistered Paper binary/arm/config")
    check(type(x["grant_id"]) is str
          and len(x["grant_id"]) <= 128
          and x["grant_id"] not in SPENT_GRANTS
          and "20261015" not in x["grant_id"],
          "consumed/undefined grant")
    check(type(x["qualification_run_id"]) is str
          and re.fullmatch("[A-Za-z0-9_-]{8,100}", x["qualification_run_id"]),
          "missing separate one-shot run identity")
    check(type(x["source_evidence_root"]) is str
          and x["source_evidence_root"].startswith("/")
          and ".." not in x["source_evidence_root"].split("/")
          and len(x["source_evidence_root"]) <= 512,
          "unsafe or absent unique candidate evidence root")
    check(type(x["source_ci_run_id"]) is int and x["source_ci_run_id"] > 0,
          "missing new source-head CI candidate")
    check(x["independent_r_receipt"] is None,
          "preworld must not supply retroactive R verdict")
    check(x["previous_grants_reused"] is False
          and x["new_java_starts"] == 0
          and x["new_node_sessions"] == 0
          and x["scientific_trials"] == 0,
          "physical start, science or grant already claimed by preworld")
    return {
        "classification": CLASS,
        "candidate_s_head": x["s_exact_head"],
        "candidate_r_head": x["r_exact_head"],
        "candidate_plugin_sha256": x["plugin_sha256"],
        "candidate_arm": ARM,
        "independent_ci_source_authentication": "NOT_PERFORMED_BY_THIS_MODULE",
        "new_binary_source_original_authentication": "NOT_PERFORMED_BY_THIS_MODULE",
        "old_grant_reused": False,
        "qualification_run_executed": False,
        "one_shot_authorization_consumed": False,
        "physical_launch_permission_issued_by_this_module": False,
        "new_jar_engineering_qualified": False,
        "science_go": False,
        "production_go": False,
    }
