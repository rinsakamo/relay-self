# BD1b original issuer one-shot API (DEV)

`relay_self.bd1b_original_issuer_once_dev.issue_original_adoption_once` is the
first live-capable owner-bound **submission + wait + original result readback +
ADOPT-COMMIT** entry point. It accepts only an already source-frozen
`CoverageAdoptionTurn` (prepared **before** attaching the original GPU lane);
it never accepts a caller-supplied decision, ticket, QuestionRecord, or owner.

The original Resident RLock serializes post-GPU source requalification with
original `ResidentLlamaInferenceLane.submit`. The worker runs outside the
lock. `await_result` requires the completed provider task and the owned
single-slot idle readback. The original Resident lock then covers original
`read_issuer_result` and `commit_issuer_adoption`. Non-ADOPT results are
returned without Question persistence or forced escalation.

Every error after submission, including timeout, cancellation, changed
Paper/Native source, or result mismatch, fences both the GPU lane and original
resident cognition for the affected Self. This prevents new issuance and
memory publication; it **does not** prove that llama-server stopped running,
reconcile crash-era in-memory job state, fence physical actuation in all owners,
or authorize GPU release/reJOIN. Caller retains responsibility for original
Bridge/session retirement and physical quarantine.

## CPU/offline scope

```bash
python -m pytest tests/test_bd1b_original_issuer_once_dev.py
ruff check src tests
python tools/check_repository.py
```

The test provider is synthetic and does not exercise real llama.cpp, hardware
GPU, live Paper/native provenance, immutable externally authenticated proof or
a real Self's choice. A real model/World one-shot needs exclusive local owned
llama-server (PID/GGUF/slot), original Paper/Native evidence, strict preflight,
a fresh run root, and independent unmodified readback. Its outcome must not be
preselected. Do not promote `SELF_ADOPT_ISSUER_NOT_ATTESTED`, BD1b/BD1,
QUAL/SCIENCE, checkpoint durability or any physical/L2 authority on the
basis of these CPU tests.
