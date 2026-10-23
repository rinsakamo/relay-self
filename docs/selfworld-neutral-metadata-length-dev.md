# W4 neutral metadata length control (DEV only)

Preregistration: https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6363694258

The new experiment module reuses the frozen original R/S following requests,
renderer, RelayEngine, provider, and Product/S model owner without changes.
Neutral identifiers are counterfactual model inputs only. They confer no
observation, source, Action or Memory authority.

Before any tokenizer call, freeze RULE and its SHA: session n1, epoch n2-after-5,
reference n1:5, source_ref present:n1:5:n3, self_id n0 plus a prefix of the
concatenation of SHA256 hex of UTF-8 w4-neutral-padding-v1:0 through :15.
Search prefix lengths 0 through 1024 ascending; select the first exact match
for each target, NL=486 and NS=360. Only self_id differs between neutral arms.
No model output may influence selection. If either target or counting
compatibility cannot be established, stop with generation zero.

Use the live server's /apply-template on the full renderer payload, then
/tokenize with add_special=true and parse_special=true, and independently
/v1/chat/completions/input_tokens on the same payload. Audit the fixed native
source paths and live binary/source identities. Original R/S must count 486/360.
Retain template-rendered strings, token IDs, native counts and candidate log.
Freeze all four full BOUNDED/THINK requests and allowlist differences before
calling execute_control. Model identity must match the original runtime.

Warmup R S NL NS; scored R S NL NS / S NS R NL / NS NL S R / NL R NS S.
20 BOUNDED requests, at most 40 provider calls including automatic THINK; OPEN 0.
Every provider and request start/end is fsynced. Errors retain the first terminal
and partial output; evidence paths are exclusive-new and external to checkout.
Check 82 protected files, 770 historical entries, original A/B and 60 factorial
entries before/after; independently read back evidence and PID/reap/port cleanup.
Unobserved STOP ACK and GPU VRAM release stay unknown.

Report scored and warmup separately. Assess baseline reproduction first, then
NL/NS and equal-length R/NL and S/NS contrasts. Padding vocabulary, byte length,
structure and token count still covary; no pure length causal effect or internal
reasoning is established. Four temperature-zero repeats are not World trials.
CI/FULL/World/Action/OUTCOME/S10/Memory/SCIENCE remain zero. PR #634 untouched.
