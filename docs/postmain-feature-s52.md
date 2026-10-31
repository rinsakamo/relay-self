# S52 real inference transport seam

Implements explicit localhost-only OpenAI-compatible chat completions for existing RelayEngine, with bounded prompt/output, redirect denial, finite-choice ID validation, transient OPEN response and token-usage facts. S47 allocator remains the owner of total call budget; no new cognition or Action authority. Actual llama.cpp/LM Studio live model call has **not** been run/qualified in GitHub CI; integration evidence and latency costs remain open (#395).
