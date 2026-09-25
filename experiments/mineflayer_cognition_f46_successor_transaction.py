from __future__ import annotations

import argparse
import json
import shlex
import tempfile
import urllib.error
from pathlib import Path

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_f46_successor as probe
import experiments.mineflayer_cognition_llama_cpp_transaction as physical

FORMAT_VERSION = 1
EXPECTED_MODEL_CALLS = probe.EXPECTED_MODEL_CALLS


def planned_request_ledger(model: str) -> list[dict[str, object]]:
    rows = probe.planned_ledger(model)
    if len(rows) != EXPECTED_MODEL_CALLS:
        raise AssertionError("successor physical ledger size drift")
    return rows


def _result_record(
    *,
    item: dict[str, object],
    model: str,
    endpoint: str,
    raw_text: str,
    plan_id: str | None,
    parse_error: str | None,
    transport_error: str | None,
) -> dict[str, object]:
    plan_order = item["planOrder"]
    if not isinstance(plan_order, list):
        raise AssertionError("planOrder must be a list")
    mapping = str(item["mapping"])

    return {
        "blockId": item["blockId"],
        "mapping": mapping,
        "arm": item["arm"],
        "permutation": item["permutation"],
        "planOrder": plan_order,
        "requestHash": item["requestHash"],
        "gradientPresent": item["gradientPresent"],
        "executionIndex": item["executionIndex"],
        "blockCallIndex": item["blockCallIndex"],
        "model": model,
        "endpoint": cognition.endpoint_metadata(endpoint),
        "rawText": raw_text,
        "planId": plan_id,
        "selectedGeometry": probe.selected_geometry(mapping, plan_id),
        "selectedPosition": probe.selected_position(
            plan_order,
            plan_id,
        ),
        "parseError": parse_error,
        "transportError": transport_error,
    }


def execute_successor(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    planned = planned_request_ledger(model)
    records: list[dict[str, object]] = []

    for item in planned:
        request_body = item["request"]
        if not isinstance(request_body, dict):
            raise physical.PhysicalTransactionError(
                "planned request is not an object"
            )

        request_hash = probe._request_hash(request_body)
        if request_hash != item["requestHash"]:
            records.append(
                _result_record(
                    item=item,
                    model=model,
                    endpoint=endpoint,
                    raw_text="",
                    plan_id=None,
                    parse_error="request_hash_mismatch",
                    transport_error=None,
                )
            )
            break

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
            records.append(
                _result_record(
                    item=item,
                    model=model,
                    endpoint=endpoint,
                    raw_text="",
                    plan_id=None,
                    parse_error="transport_or_response_error",
                    transport_error=f"{type(exc).__name__}:{exc}",
                )
            )
            break

        parsed = probe.parse_choice(raw_text)
        records.append(
            _result_record(
                item=item,
                model=model,
                endpoint=endpoint,
                raw_text=raw_text,
                plan_id=parsed.plan_id,
                parse_error=parsed.error,
                transport_error=None,
            )
        )
        if parsed.error is not None:
            break

    return {
        "records": records,
        "summary": probe.summarize_records(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Own one llama.cpp lifetime for the frozen #331 "
            "viability-gradient successor probe."
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
                prefix="relay-self-f46-successor-"
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
        "implementationOwner": 332,
        "designOwner": 331,
        "scientificQuestionOwner": 46,
        "armCount": len(probe.ARMS),
        "mappingCount": len(probe.MAPPINGS),
        "blockCount": probe.EXPECTED_BLOCKS,
        "callsPerBlock": probe.EXPECTED_CALLS_PER_BLOCK,
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
                "current successor condition requires port 1234"
            )
        if not physical._port_is_free(physical.DEFAULT_HOST, args.port):
            raise physical.PhysicalTransactionError(
                "127.0.0.1:1234 is already occupied"
            )
        physical._complete_stage(summary, "port_free")

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"

        physical._begin_stage(summary, "llama_cpp_revision")
        physical._require_llama_cpp_paths(
            llama_cpp_root,
            server_binary,
        )
        revision = physical._collect_llama_revision(llama_cpp_root)
        physical._complete_stage(summary, "llama_cpp_revision")

        physical._begin_stage(summary, "llama_server_version")
        version_identity = physical._collect_server_version(
            server_binary
        )
        physical._complete_stage(summary, "llama_server_version")
        llama_identity = {
            "revision": revision,
            **version_identity,
        }

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
            "implementationOwner": 332,
            "designOwner": 331,
            "scientificQuestionOwner": 46,
            "expectedModelCalls": EXPECTED_MODEL_CALLS,
            "blockCount": probe.EXPECTED_BLOCKS,
            "callsPerBlock": probe.EXPECTED_CALLS_PER_BLOCK,
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
        if not isinstance(attested, dict):
            raise physical.PhysicalTransactionError(
                "runtime attestation object missing"
            )
        model = attested["requestModel"]
        if not isinstance(model, str):
            raise physical.PhysicalTransactionError(
                "attested request model is not a string"
            )

        physical._begin_stage(summary, "request_ledger")
        ledger = planned_request_ledger(model)
        physical._write_json(
            evidence_root / "request-ledger.json",
            ledger,
        )
        physical._complete_stage(summary, "request_ledger")

        physical._begin_stage(summary, "model_generation")
        result = execute_successor(
            endpoint=f"{origin}/v1/chat/completions",
            model=model,
            timeout=args.timeout,
        )
        physical._complete_stage(summary, "model_generation")

        physical._begin_stage(summary, "result_write")
        physical._write_json(
            evidence_root / "f46-successor-result.json",
            result,
        )
        summary["modelCallCount"] = len(result["records"])
        result_summary = result["summary"]
        if not isinstance(result_summary, dict):
            raise physical.PhysicalTransactionError(
                "successor result summary missing"
            )
        classification = result_summary["classification"]
        summary["scientificClassification"] = classification

        if classification == probe.INVALID:
            summary["disposition"] = "TERMINAL_INVALID"
            exit_code = 4
        else:
            summary["disposition"] = "COMPLETED"
            exit_code = 0

        physical._complete_stage(summary, "result_write")
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
            cleanup["exitCode"] = physical._terminate_owned_process(
                process
            )
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
