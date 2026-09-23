from __future__ import annotations

import argparse
import copy
import json
import shlex
import tempfile
import urllib.error
from pathlib import Path

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_llama_cpp_transaction as physical
import experiments.mineflayer_cognition_opaque_id_calibration as opaque

FORMAT_VERSION = 1
CALIBRATION_REPEATS = 5
EXPECTED_MODEL_CALLS = len(opaque.OPAQUE_CONDITIONS) * CALIBRATION_REPEATS


def physical_requests(model: str) -> dict[str, dict[str, object]]:
    rendered = opaque.render_opaque_requests(model)
    output: dict[str, dict[str, object]] = {}
    for condition in opaque.OPAQUE_CONDITIONS:
        request_body = copy.deepcopy(rendered[condition]["request"])
        if not isinstance(request_body, dict):
            raise AssertionError("rendered request must be an object")
        request_body["reasoning_effort"] = "none"
        request_body["cache_prompt"] = False
        output[condition] = {
            "request": request_body,
            "requestHash": physical._sha256_bytes(
                physical._canonical_json(request_body).encode("utf-8")
            ),
            "geometryBinding": rendered[condition]["geometryBinding"],
            "planOrder": rendered[condition]["planOrder"],
            "shortestGeometryPlanId": rendered[condition][
                "shortestGeometryPlanId"
            ],
        }
    return output


def planned_request_ledger(model: str) -> list[dict[str, object]]:
    rendered = physical_requests(model)
    rows: list[dict[str, object]] = []
    conditions = tuple(opaque.OPAQUE_CONDITIONS)

    for trial in range(CALIBRATION_REPEATS):
        ordered = (
            conditions
            if trial % 2 == 0
            else tuple(reversed(conditions))
        )
        for order_index, condition in enumerate(ordered):
            bundle = rendered[condition]
            rows.append(
                {
                    "trial": trial,
                    "orderIndex": order_index,
                    "condition": condition,
                    "requestHash": bundle["requestHash"],
                    "request": bundle["request"],
                    "geometryBinding": bundle["geometryBinding"],
                    "planOrder": bundle["planOrder"],
                    "shortestGeometryPlanId": bundle[
                        "shortestGeometryPlanId"
                    ],
                }
            )

    if len(rows) != EXPECTED_MODEL_CALLS:
        raise AssertionError("opaque calibration ledger size drift")
    return rows


def execute_calibration(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    planned = planned_request_ledger(model)
    records: list[dict[str, object]] = []

    for item in planned:
        request_body = item["request"]
        assert isinstance(request_body, dict)

        try:
            raw_text = cognition.call_openai_compatible(
                endpoint=endpoint,
                request_body=request_body,
                api_key=None,
                timeout=timeout,
            )
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise physical.PhysicalTransactionError(
                "opaque calibration model call failed without retry at "
                f"trial {item['trial']} condition {item['condition']}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        parsed = opaque.parse_opaque_choice(raw_text)
        plan_id = parsed.plan_id
        condition = str(item["condition"])
        geometry_binding = item["geometryBinding"]
        assert isinstance(geometry_binding, dict)

        selected_geometry = (
            geometry_binding[plan_id]
            if plan_id in opaque.OPAQUE_PLAN_IDS
            else None
        )

        records.append(
            {
                "trial": item["trial"],
                "orderIndex": item["orderIndex"],
                "condition": condition,
                "model": model,
                "endpoint": cognition.endpoint_metadata(endpoint),
                "requestHash": item["requestHash"],
                "rawText": raw_text,
                "planId": plan_id,
                "selectedGeometry": selected_geometry,
                "tracksShortestGeometry": (
                    selected_geometry == "direct"
                    if selected_geometry is not None
                    else None
                ),
                "parseError": parsed.error,
                "transportError": None,
            }
        )

    return {
        "records": records,
        "summary": opaque.summarize(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Own one llama.cpp lifetime for the #323 "
            "opaque-plan-id calibration."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--llama-cpp-root",
        default=str(Path.home() / "src" / "llama.cpp"),
    )
    parser.add_argument(
        "--artifact-path",
        default=str(
            Path.home()
            / "models"
            / "gguf"
            / "gemma-4-12B-it-Q4_K_M.gguf"
        ),
    )
    parser.add_argument("--port", type=int, default=physical.DEFAULT_PORT)
    parser.add_argument(
        "--timeout",
        type=float,
        default=physical.DEFAULT_REQUEST_TIMEOUT,
    )
    parser.add_argument("--evidence-root")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    evidence_root = (
        Path(args.evidence_root).expanduser().resolve()
        if args.evidence_root
        else Path(
            tempfile.mkdtemp(
                prefix="relay-self-opaque-id-calibration-"
            )
        )
    )
    if args.evidence_root:
        evidence_root.mkdir(parents=True, exist_ok=False)

    summary: dict[str, object] = {
        "formatVersion": FORMAT_VERSION,
        "disposition": None,
        "serverLaunchCount": 0,
        "modelCallCount": 0,
        "plannedModelCallCount": EXPECTED_MODEL_CALLS,
        "retryCount": 0,
        "replayCount": 0,
        "fallbackCount": 0,
        "repositoryMutationCount": 0,
        "evidenceRoot": str(evidence_root),
        "currentStage": "initialization",
        "completedStages": [],
        "calibrationOwner": 323,
        "parentCalibrationOwner": 320,
        "scientificOwner": 46,
        "calibrationRepeats": CALIBRATION_REPEATS,
    }

    process = None
    log_path = evidence_root / "llama-server.log"
    cleanup: dict[str, object] = {
        "ownedProcess": False,
        "terminated": False,
        "exitCode": None,
    }
    exit_code = 2

    try:
        physical._begin_stage(summary, "clean_repo")
        head, tree = physical._require_clean_repo(repo_root)
        summary["relaySelf"] = {"head": head, "tree": tree}
        physical._complete_stage(summary, "clean_repo")

        physical._begin_stage(summary, "port_free")
        if args.port != physical.DEFAULT_PORT:
            raise physical.PhysicalTransactionError(
                "current calibration condition requires port 1234"
            )
        if not physical._port_is_free(physical.DEFAULT_HOST, args.port):
            raise physical.PhysicalTransactionError(
                "127.0.0.1:1234 is already occupied"
            )
        physical._complete_stage(summary, "port_free")

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"

        physical._begin_stage(summary, "llama_cpp_revision")
        physical._require_llama_cpp_paths(llama_cpp_root, server_binary)
        revision = physical._collect_llama_revision(llama_cpp_root)
        physical._complete_stage(summary, "llama_cpp_revision")

        physical._begin_stage(summary, "llama_server_version")
        version_identity = physical._collect_server_version(server_binary)
        physical._complete_stage(summary, "llama_server_version")
        llama_identity = {"revision": revision, **version_identity}

        physical._begin_stage(summary, "gguf_verify")
        artifact_sha256 = physical._verify_artifact(artifact_path)
        physical._complete_stage(summary, "gguf_verify")

        physical._begin_stage(summary, "gpu_identity")
        gpu_identity = physical._collect_gpu_identity()
        physical._complete_stage(summary, "gpu_identity")

        command = physical._server_command(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.port,
            log_path=log_path,
        )
        binding = {
            "relaySelf": {"head": head, "tree": tree},
            "llamaCpp": llama_identity,
            "artifactPath": str(artifact_path),
            "artifactSha256": artifact_sha256,
            "launchCommand": shlex.join(command),
            "gpuIdentity": gpu_identity,
            "context": physical.DEFAULT_CONTEXT,
            "slots": physical.DEFAULT_SLOTS,
            "contextShiftEnabled": False,
            "calibrationOwner": 323,
            "parentCalibrationOwner": 320,
            "scientificOwner": 46,
            "calibrationRepeats": CALIBRATION_REPEATS,
            "expectedModelCalls": EXPECTED_MODEL_CALLS,
        }

        physical._begin_stage(summary, "binding_write")
        physical._write_json(
            evidence_root / "binding.json",
            binding,
        )
        physical._complete_stage(summary, "binding_write")

        physical._begin_stage(summary, "server_launch")
        process = physical._start_server(command)
        cleanup["ownedProcess"] = True
        summary["serverLaunchCount"] = 1
        summary["serverPid"] = process.pid
        physical._complete_stage(summary, "server_launch")

        origin = f"http://{physical.DEFAULT_HOST}:{args.port}"

        physical._begin_stage(summary, "readiness")
        physical._wait_until_ready(process, origin)
        physical._complete_stage(summary, "readiness")

        physical._begin_stage(summary, "runtime_attestation")
        runtime = physical._probe_and_attest(
            origin=origin,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            llama_identity=llama_identity,
        )
        physical._write_json(
            evidence_root / "runtime-attestation.json",
            runtime,
        )
        physical._complete_stage(summary, "runtime_attestation")

        attested = runtime["attested"]
        assert isinstance(attested, dict)
        model = attested["requestModel"]
        assert isinstance(model, str)

        physical._begin_stage(summary, "request_ledger")
        ledger = planned_request_ledger(model)
        physical._write_json(
            evidence_root / "request-ledger.json",
            ledger,
        )
        physical._complete_stage(summary, "request_ledger")

        physical._begin_stage(summary, "model_generation")
        result = execute_calibration(
            endpoint=f"{origin}/v1/chat/completions",
            model=model,
            timeout=args.timeout,
        )
        physical._complete_stage(summary, "model_generation")

        physical._begin_stage(summary, "result_write")
        physical._write_json(
            evidence_root / "opaque-calibration-result.json",
            result,
        )
        summary["modelCallCount"] = len(result["records"])
        summary["resultSummary"] = result["summary"]
        summary["disposition"] = "COMPLETED"
        physical._complete_stage(summary, "result_write")
        exit_code = 0
        return exit_code

    except physical.PhysicalTransactionError as exc:
        summary["disposition"] = "BLOCKED_OR_INVALID"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3
        return exit_code

    except Exception as exc:
        summary["disposition"] = "HARNESS_INVALID"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 2
        return exit_code

    finally:
        if process is not None:
            cleanup["exitCode"] = physical._terminate_owned_process(process)
            cleanup["terminated"] = process.poll() is not None
        if log_path.is_file():
            cleanup["logSha256"] = physical._sha256_file(log_path)
        physical._write_json(
            evidence_root / "cleanup.json",
            cleanup,
        )
        completed = summary.get("completedStages")
        if isinstance(completed, list):
            completed.append("cleanup")
        summary["transactionExitCode"] = exit_code
        summary["cleanup"] = cleanup
        physical._write_json(
            evidence_root / "transaction-summary.json",
            summary,
        )
        print(
            json.dumps(
                summary,
                ensure_ascii=False,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
