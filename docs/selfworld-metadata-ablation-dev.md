# W4 metadata × request_id DEV probe

Preregistered plan: https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6363138292

`experiments.self_world_metadata_ablation` reuses the original saved replay,
synthetic-empty fixture factory, renderer, RelayEngine and llama.cpp provider.
The original A/B apparatus, core and model owner remain unchanged. These are
counterfactual transient model inputs, never qualified observation/Memory/Action.

A = real metadata / real request_id; B = real / synthetic;
C = synthetic / real; D = synthetic / synthetic.
All expected choices are DEFER_RECHECK. Frozen diagonal renderer hashes match
the original measured following requests. Any source or nonallowlisted change
blocks execution before model calls. The complete metadata bundle is exchanged
as one unit; both datums retain coherent mineflayer references.

Before opening the existing `owned_model` lifetime, call `prepare_arms` on the
pinned original W4 observation root, then `freeze_requests` into an exclusive-new
external evidence root. This saves both BOUNDED and optional THINK payloads,
SHA256 digests, semantic field differences and the fixed order. Validate source,
protected and historical hashes and focused Python3.12/Ruff/contracts first.

Inside one Product/S `owned_model` scope, verify live runtime identity against
the original alias/GGUF/template/runtime, then call `execute_factorial` with
`LlamaCppRelayProvider` and the frozen manifest SHA. Warmup ABCD; scored ABCD,
BDAC, DCBA, CADB. Exactly 20 BOUNDED requests, at most 40 provider calls including
existing automatic THINK. No OPEN. No adaptive changes or retry after error.

Outputs reserve both report and journal exclusively before calls. Every
provider start/end and request start/end is journaled with fsync, including
errors/cancellation. A partial report survives exceptions; the first exception
propagates for existing owned cleanup. No replacement of failed evidence.
Operational code must independently observe child PID/starttime, reap records,
/proc absence and port settlement and retain source hashes before/after.

Report warmup separately from the four scored decisions per arm; retain choice,
unresolved, THINK, API errors, calls, tokens, wall latency and request SHA.
Check A/D reproduction first. Compare DEFER rates, metadata and request-ID
contrasts and their difference in differences. A metadata effect does not
separate vocabulary from length or individual fields. Temperature-zero repeats
of one empty pair are not independent World trials. No internal reasoning or
scientific causal effect is certified. CI, FULL, World, Action, OUTCOME, S10,
Memory and SCIENCE are outside this experiment; PR #634 remains unchanged.
