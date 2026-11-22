# Stage 24c — native exploration gate / Jev UNRESOLVED differential

Parent: [Stage24 #911](https://github.com/rinsakamo/relay-self/issues/911); issue [Stage24c #933](https://github.com/rinsakamo/relay-self/issues/933); staged on **Draft Stage24b #925**. This is **not a World retry, physical MOVE, L1 learning result, or QUAL**.

## Why this exists

Stage24b's third actual World trial (HEAD `bc84edeb9319fd437fad55cc06c3b7590138fc10`) reached real SystemOne in 445.386 ms but emitted no Goal/MOVE: the native source had `oxygen_level=null`, `exploration_eligible=false`, and only `ESCALATE_L2`/ `DEFER`. Jev returned **reserved unresolved**, not explicit DEFER. Canonical WAL actions `[]`, no native physical effect, no A rejoin/World-only restoration. Original evidence manifest SHA256 `86eb610ddc966e65776c67c8ef9c8aec742e8bbc90d00b0ea2be2b3709cfcb67` is immutable; previous two pre-World HOLDs remain separate.

**Do not** force oxygen positive or use a "known-safe" environment assumption to create physical MOVE. Current code requires a positive observed oxygen measurement. No other failing predicate is ruled out without checking the actual native observation: audit all of them independently.

## A. Production cognitive gate instrumentation (no change to admission)

`relay_self.resident_exploration_gate_audit_dev.audit_exploration_gate` evaluates the exact original Stage24a exploratory predicates with `PASS`, `BLOCKED` or `UNKNOWN`:

- live intent must be absent
- health ≥16, food ≥18
- oxygen **observed** and >0; missing `null` is UNKNOWN, not zero
- World time observed
- nearby entity source coverage not truncated
- nearby entities absent

The existing `_eligible_exploration` calls this audit's all-PASS result. The original Capability gate remains independent and unchanged. This adds neither an explorational Need nor a physical permission.

On the **next separately authorized real World run**, the original `B-original-systemone-choice.json` includes `stage24c_original_gate` and `stage24c_latest_gate`, each source-scoped by native session/sequence/request ID. Compare first/last predicates and source before attributing failure to oxygen. The archive still contains parsed provider output rather than raw SystemOne HTTP response body; do not infer otherwise.

## B. Synthetic paired SystemOne calibration — **NO Minecraft World**

`experiments/stage24c_systemone_pair_dev.py` builds exactly two synthetic original typed Stage24a candidate requests through the original CPU Schema/choices and `render_llama_cpp_jev_request`, with **only one difference**:

1. `oxygen_unknown`: oxygen `None`; 0 MOVE candidates, numbered `ESCALATE_L2` and `DEFER`, plus the Jev internal `__relay_self_unresolved__` criterion.
2. `oxygen_known_positive`: oxygen `300` **synthetic fixture only**; 4 prebound `MOVE` candidates plus the same `ESCALATE_L2` / `DEFER` and Jev internal unresolved.

All other body fields (food, health, World time, coverage, nearby entities, position, synthetic owner) are equal and **fictional**; no result qualifies a real WorldBody as having oxygen=300. No candidate is automatically selected. The original parser distinguishes explicit `DEFER` from reserved `jev_model_unresolved`.

First run **pure offline** — it writes the request JSON and gate records but performs no GPU inference:

```bash
mkdir -p "$EVIDENCE_PARENT"
PYTHONPATH=src:. python3 -m experiments.stage24c_systemone_pair_dev \
  --model "$ACTUAL_SERVED_GEMMA_MODEL" \
  --evidence-dir "$EVIDENCE_PARENT/stage24c-synthetic-inspect" \
  --inspect-only
```

Read back both fixture requests and verify the expected choice set and one changed field. Use a **fresh** evidence directory for subsequent model calls. After independently verifying the **owned** llama.cpp executable, Gemma GGUF SHA, exclusive n_parallel=1, no external clients, idle /slots and loopback endpoints, run **at most one SystemOne POST per synthetic case**, no retries:

```bash
PYTHONPATH=src:. python3 -m experiments.stage24c_systemone_pair_dev \
  --model "$ACTUAL_SERVED_GEMMA_MODEL" \
  --evidence-dir "$EVIDENCE_PARENT/stage24c-synthetic-model" \
  --llama-endpoint "$LLAMA_ENDPOINT" \
  --systemone-endpoint "$SYSTEMONE_ENDPOINT" \
  --backend-ref "$EXPERIMENT_OWNED_BACKEND_REF" \
  --grant-real-llm --execute-model-pair
```

**Real LLM permission** was already granted by the user for this project, but it must still be passed explicitly for this opt-in script. The operator is responsible for verifying sole GPU/process ownership. The script uses the same production Jev request renderer and decision parser, bounded original choices, and the same locally exclusive /slots witness as Stage24b. It sends directly over the *original Jev HTTP protocol* for **calibration only**, not through the per-Self resident lane; it cannot attach model output to any physical World owner.

Per case evidence: exact request JSON body bytes and SHA256, actual HTTP **response body** bytes and SHA256 (not full wire packet/headers), original parser output (RESOLVED choice number or UNRESOLVED), prompt/output token call facts, inference latency, source label `SYNTHETIC_NOT_WORLD_EVIDENCE`. The archived manifest explicitly says zero physical actions and zero Worlds. If a call or idle readback fails, HOLD; preserve all emitted original files and do not rerun.

## C. Real native oxygen sensor investigation (separate patch)

Independently inspect Mineflayer `bot.oxygenLevel` in the exact locked 4.39.0 and Minecraft 1.21.8 bridge. Determine why the actual dry-land probe returned `null`. A missing field might mean unsupported measurement and **must never be equated with** `0`, `300`, "safe to move", or "underwater". Candidate eligibility can be changed only with independently validated observations and new contract tests for underwater/air pressure cases. Do not modify Stage24c's conservative gate to force a real MOVE.

## D. Exit conditions

- All offline gate reasons and Jev request/parse contracts PASS on an exact HEAD; no synthetic fixture mistaken for physical source.
- A local real model calibration (if performed) records distinct outcomes for two synthetic cases and preserves raw HTTP **body** bytes, without any Minecraft World or retry.
- Publish output to Issue #933, Draft PR (Stage24c), parent Issue #911. Do not reinterpret existing Stage24b `HOLD/L1_UNRESOLVED/NO_ACTION` as success.
- A further Stage24b/24d actual World trial requires a **separate new** approved scope, model owner and positive source-qualified cognitive evidence. Stage25 is still NOT authorized by these diagnostic experiments.
