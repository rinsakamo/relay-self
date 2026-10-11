# RSEE 1.0 — RelaySelf Standard Experimental Environment

Status: **candidate profile + read-only offline preflight only**. Owner: [#575](https://github.com/rinsakamo/relay-self/issues/575). This is an **experimental apparatus**, not a new cognition/Action/World authority. The first Draft targets standalone protected `main` infrastructure; the integrated Self executable is still [#537](https://github.com/rinsakamo/relay-self/issues/537) / Draft #545, whose S60-B1-based implementation is not on `main`.

## Purpose and boundaries

Use exactly one stable experimental profile across Lane A/B/C/product, with **fixed declared settings** separate from **fresh physical attestation**. This profile deliberately cannot launch Minecraft or a GPU. It cannot grant World access, authorise scientific spend or produce a successful physical claim. A new local trial still needs its operator-owned authorization.

Canonical candidate: [profile.v1.json](../experiments/standard_env/profile.v1.json).

| Coordinate | Candidate value | Claim ceiling |
|---|---|---|
| Host | Linux/WSL2; CPython 3.12; Java 21; Node >=22 | Preflight verifies Linux/Python/tools/imports, **not** Windows/WSL host authenticity |
| Mineflayer | 4.39.0, npm lock + installed dependency | Preflight checks lock/installed version; does not launch bot |
| Minecraft | Mojang 1.21.8, disposable-only, localhost 25565 | jar hash and initial World seed/snapshot/rules **unbound** until an actual approved run |
| LLM | Gemma 4 12B IT Q4_K_M, SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed` | SHA pinned. Operator-local model path is not a universal authority |
| llama-server | loopback 127.0.0.1:1234, `-ngl 999 -c 8192 -np 1 --no-context-shift` | Binary SHA, effective model/template/context/slots and GPU binding verified separately |
| LLM request | explicit `reasoning_effort:"none"`; optional experiment-owned native `response_format: {type:"json_schema",json_schema:{name,strict:true,schema}}`; `cache_prompt=false` | Exact JSON-schema, max tokens, temperature/seed are **per experiment**, never silently assigned by this profile |
| GPU lease | `llama-cpp:local-gpu`, exclusive owner | Profile declaration does not acquire lease |
| Evidence | original S49/S16 World receipts + provider envelope + manifest + system resource facts | Read-only timeline is not independent World attestation |

For ordinary scientific tasks, use one slot and no context shift to minimize capacity/lease ambiguity. Future multi-agent or variable-time Worlds should have **different versioned profiles**, not hidden changes to this one.

## 1. Non-generative plan — safe default

Run from the repository root:

```bash
python3.12 -m experiments.standard_env.preflight
```

This prints `RSEE_PLAN_ONLY`, the raw profile's SHA256 and a list of **unverified** conditions. It does not run `node`, `java`, `llama-server`, Python dependency probes, network checks or hashes of large model files. It never contacts localhost.

## 2. Optional local files/import preflight

Prepare the operator-owned Python environment and `npm ci --prefix adapters/mineflayer` **outside** this read-only preflight. Freeze the exact expected hashes for the current executable and the locally obtained Mojang jar; do not fill these from a historical receipt merely to obtain PASS.

```bash
python3.12 -m experiments.standard_env.preflight --verify-local \
  --model /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --llama-server /home/rinsa/src/llama.cpp/build/bin/llama-server \
  --llama-sha256 <64-lowercase-hex-from-fresh-operator-attestation> \
  --minecraft-jar /path/to/server-1.21.8.jar \
  --minecraft-sha256 <64-lowercase-hex-from-fresh-operator-attestation>
```

Only in `--verify-local` mode, the checker:

- requires CPython 3.12, Linux, Node >=22, Java 21 and importable `pytest` + `httpx` **in the same Python interpreter**; these are minimal initial import-closure sentinels, not proof that every branch-specific module imports correctly;
- verifies the Mineflayer npm lock's declared version and the installed `node_modules/mineflayer/package.json`; it does not install packages;
- streams GGUF, llama-server and Minecraft jar hashes to check exact bytes; refuses missing, changed or unpinned binaries;
- emits `RSEE_LOCAL_PREFLIGHT_BLOCKED` (exit 2) or `RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED` (exit 0).

A local-file PASS is **not** a license to start a model/World. The verification does not prove jar provenance, the running server's linked CUDA libraries, listening port ownership, current GPU identity, source revision, operator authorization or actual World state. Where the existing #545/other-lane worktree has more import dependencies, extend the **existing local preflight** with that exact module closure before consuming the real grant.

## 3. One subsequently approved Golden Smoke (NOT_RUN here)

The *existing* product runner from #545, not this module, must own the execution lifecycle. Integration point is:

```text
read-only RSEE profile + fresh operator artifact checks
 -> acquire existing local GPU/World grants, check listener quiescence
 -> existing S57/S60 owned llama-server + live /health, /v1/models, /props, /slots
 -> compare actual serialized request reasoning, JSON schema, context and model alias
 -> existing #545 disposable original S49 Minecraft / Mineflayer session
 -> original S15/S16 authorized Action -> original World OUTCOME -> observed Memory
 -> existing passive timeline
 -> evidence, shutdown, PID/port/GPU observations, release leases
```

Runtime identity MUST bind exact llama.cpp commit/build/binary hash and loaded libraries; GGUF hash and model alias; tokenizer/chat-template identity; effective context, slots, shift, GPU offload; request schema, decoding, reasoning, cache, prompt/token budget; Minecraft jar/World seed/snapshot/gamerules/spawn and the initial Health/Food; the source HEAD and run-specific permissions. They must be checked from actual processes and native source, **not inferred** from this profile or previous comments.

Never equate HTTP client cancellation or owned server PID exit with a guaranteed per-request STOP ACK. Unknown backend state remains fail-closed. No new retry/replay/fallback and no B/C/E5 trial is automatically permitted.

## 4. Source lineage / nontransferability

- [RelayLM 2.0 #2410](https://github.com/rinsakamo/relay-lm/issues/2410): host switch to WSL2 llama.cpp, actual `-c 8192`, request Thinking OFF.
- [RelayLM 2.0 #2424](https://github.com/rinsakamo/relay-lm/issues/2424): request-level `reasoning_effort:"none"` needs same-shape exact input accounting; do not claim a new llama.cpp revision has identical semantics before observing it.
- [RelayLM 2.0 #2302](https://github.com/rinsakamo/relay-lm/issues/2302): 12/12 strict JSON-Schema protocol under **LM Studio with reasoning default ON**; not proof for Self's WSL2 combination.
- [RelayLM 2.0 #2897](https://github.com/rinsakamo/relay-lm/issues/2897) and [#2914](https://github.com/rinsakamo/relay-lm/issues/2914): later **WSL2 llama.cpp** runs with `reasoning=none`, strict schema and context 8192; historical, not fresh Self qualification.
- [RelayLM 2.0 #2363](https://github.com/rinsakamo/relay-lm/issues/2363): *Controller observes and assembles; host validates and freezes.*
- [RelayLM 2.0 #2750](https://github.com/rinsakamo/relay-lm/issues/2750) / [#2799](https://github.com/rinsakamo/relay-lm/issues/2799): shared physical queue and persistent Python generations. **Reuse the procedure**, not mutable runtime state, grants or full RelayLM code.
- [RelaySelf #537](https://github.com/rinsakamo/relay-self/issues/537): authoritative product scope. [#568](https://github.com/rinsakamo/relay-self/issues/568) and [#563](https://github.com/rinsakamo/relay-self/issues/563): still-separate Minecraft transport and LLM live diagnostics owners.

A and B and C World variants (calibration, benchmark, continuous development) require individually frozen initial World templates. They remain planned; RSEE v1 does not invent preexisting snapshots or silently reset a live user World.

**Claim ceiling for this Draft:** candidate profile + offline checker and deterministic tests. Actual Minecraft/GPU and full golden end-to-end run: `NOT_RUN`. No production GO.
