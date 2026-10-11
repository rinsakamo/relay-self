# RSEE R1 — S/L/V shared runtime contract

Authority: RSEE Issue #575; Self product #537. R1 is a separate unmerged Draft based on #588 exact 34820f6bf391c77f325d7c29d3b779a33e3ca835. S #590 and A/B/C are separate writers.

## Reused authority (no competing launcher)

- experiments.standard_env.preflight: canonical profile, local source/host/package/model/JAR checks and original product import probes.
- experiments.standard_env.node_runtime: byte-exact physical shared npm package and lock identity.
- experiments.standard_env.golden_host_gate: existing read-only Git HEAD, tracked-diff and Linux listener observers. R1 does NOT reuse its Golden grant or classification.
- experiments.standard_env.golden_admission: exact #583 stopped World JAR, seed, 26-file snapshot and native sidecar hashes, bytes-only qualification.
- adapters.mineflayer.self_owned_llama and existing S49/process_session: original lease, model/World/Node process and native Action/OUTCOME owners. R1 never starts or stops them.

Canonical root: /home/rinsa/.local/share/relay-self/rsee-1.0-20261011
Python: BASE/venv/bin/python (sys.prefix=BASE/venv)
Node: BASE/npm-mineflayer-4.39.0 (physical, source-lock-matched).
Original model: /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf.
Original llama: /home/rinsa/src/llama.cpp/build/bin/llama-server.
Original Minecraft: BASE/minecraft-1.21.8.jar and BASE/bootstrap-approved-20261011-once/snapshot and its manifest/native observation.
No worktree-local venv/node_modules install, GGUF copy, automatic repair or model substitution.

## Usage for S, L, V

From an independent checkout containing R1, set PYTHONPATH="$PWD/src:$PWD/tests:$PWD" and PYTHONDONTWRITEBYTECODE=1. The following operations are read-only. For each lane, select --lane S / L / V.

Default plan (no Git, host tools, process launch, port probe or file writes):

    "$BASE/venv/bin/python" -m experiments.standard_env.shared_runtime --lane S

Opt-in **local** preflight, using an unused evidence destination that already has a physical parent directory:

    HEAD="$(git rev-parse HEAD)"
    "$BASE/venv/bin/python" -m experiments.standard_env.shared_runtime \
      --lane L --verify-local --expected-head "$HEAD" \
      --new-evidence-dir "$BASE/evidence/r1-l-fresh-id"

API equivalents: plan("V") or preflight("S", expected_head=HEAD, evidence_dir=PATH).

Results:
- RSEE_R1_PLAN_ONLY: canonical paths and expected hashes, live source HEAD/Node/GPU/lease all unknown.
- RSEE_R1_FILES_READY_NOT_AUTHORIZED: offline checks passed only.
- RSEE_R1_PREFLIGHT_BLOCKED: source/host/dependency/artifact/World/port/output identity blocked; read errors array.

The opt-in check verifies exact HEAD, tracked clean state, canonical venv interpreter/sys.prefix, central npm root/manifest/lock, actual Mineflayer/S49 import closure via existing verifier, static product profile, exact binary/GGUF/JAR/World pin, no unsafe NODE_PATH/NODE_OPTIONS override, no occupied model/World listener without resource ownership, safe fresh destination outside Git or inside BASE/evidence only. It creates NO destination. Port observation is not socket reservation. Python/Node version reads are non-generative; no Java server or Mineflayer session is started.

Even PASS cannot transfer Golden grants, authorize Minecraft EULA/Java, llama-server or GPU, LLM POST, Self Action or a trial. Existing --rsee-golden-run-once remains independent and the three Golden approvals are already spent.

## Provenance / evidence envelope

experiments.standard_env.shared_runtime.SCHEMA is RSEE_R1_PROVENANCE_V1.
validate_evidence(record) checks exact fields:

- lane, exact source_head, environment_profile_sha256, source_session, terminal_classification
- world_identity and model_identity (null when truly unobserved)
- original_receipt_refs and action_outcome_refs, lists of {path:absolute existing original, sha256:lowercase 64-hex}
- evidence_sha256_index mapping original raw absolute paths to SHA256
- cleanup_observations, distinctly preserving host cancellation, backend STOP ACK, slot release, GPU quiescence, VRAM release, owned process exits; UNKNOWN when not observed
- physical_execution_authorized=false, science_qualified=false, timeline_is_physical_proof=false

read_only_receipt_index hashes the original existing bytes without copying or writing.
validate_evidence(record, verify_receipts=True) rehashes and rejects changed or absent originals. R1 is a provenance envelope, NOT new receipt authority: do not backfill missing S49 native receipts or promote a RelayUI timeline into physical evidence. A future separately authorized owner may write a derived envelope in a new external evidence directory, never alter originals, #583 World, #588 Golden index, #590 event stream or unrelated lanes.

## Responsibility and cleanup boundaries

- GPU lease llama-cpp:local-gpu: original product lease holder. Lease status UNKNOWN until actually checked.
- llama-server: existing self_owned_llama. Host cancellation != backend STOP ACK != slot release != GPU quiescence != VRAM release != owned PID exit.
- Minecraft server: existing S49 World owner. Independent native stop/save, process exit and port proof are different.
- Node/Mineflayer: existing session owner. Raw bridge ACK is not inferred from clean process exit.
- R lane: zero process or scheduler ownership. Responsible only for read-only selection, environment diagnosis, and provenance indexing.

## Offline verification and limits

Dedicated tests: S/L/V parity, plan without probes, exact HEAD / dirty source / busy listener, missing or mismatched dependencies/World, unsafe/symlinked destination, noncanonical Python/Node, hostile overrides, original receipt drift, and timeline promotion. The R1 CI checks focused tests, Ruff, repository contracts, full inherited Python suite, existing Node adapter checks.

GitHub CI is not the user's WSL2 host: GPU, active lease, exact current native STOP ACK, runtime inference, and subsequent physical World qualification remain UNKNOWN / NOT_RUN. No production GO from R1.
