# Router comparison: Jev vs Arch-Router vs RouteLLM vs small-LLM baseline
Scope: route agentic-coding prompts by **difficulty only** to one of 3 tiers: `cheap` / `mid` / `frontier`.
Status: prepared, not run. Prepared 2026-11-01.

## 1. Dataset — `queries.jsonl` (57 queries)
Fields: `id, category, query, label, rationale`. Balanced 19/19/19 across labels.
Categories: trivial_edit (8), docs_question (7), bug_fix (9), refactor (8), architecture (7), hard_debug (8),
agentic (4), adversarial_easy (3: scary wording, trivial task → tests over-routing),
adversarial_hard (3: casual wording, hard task → tests under-routing).
**Labels are our own judgement**, not measured outcomes (see §5 validation).
Generator: `make_queries.py` (edit there, re-run).

## 2. Routers under test (same 3-tier output for all)
| Router | How it decides | Where it runs | Confidence? |
|---|---|---|---|
| **Jev** (`typesafe-ai/jev`, TypeSafe) | One `choice` question `tier` with criteria cheap/mid/frontier (+ optional `score` question "difficulty 0–4" and `noul` "needs frontier reasoning") | Hosted API (Vercel AI Gateway or api.typesafe.ai) | Yes: per-option probabilities + confidence |
| **Arch-Router-1.5B** (katanemo) | Route descriptions = the 3 tiers ("cheap: trivial edits, lookups…"); returns `{"route": ...}` | Local CPU (GGUF Q8 via llama.cpp preferred; transformers OK) | Not native; can derive from token logprobs of route name |
| **RouteLLM** (lm-sys) | Binary strong/weak win-rate score; map to 3 tiers with two thresholds calibrated on a held-out 15 queries | `bert` router: local CPU. `mf`/`sw_ranking`: need OpenAI embeddings API key. `causal_llm` (Llama-3-8B): needs GPU → skip | Yes: win-rate score (uncalibrated for 3 tiers) |
| **Small-LLM baseline** | Prompted classifier, JSON output {tier, confidence} | Either local Qwen2.5-1.5B-Instruct (CPU) or a cheap hosted model via same gateway | Self-reported / logprobs |
Caveat: Arch-Router is built for domain/action *preference* routing, and RouteLLM routers were trained on 2024 Chatbot Arena preferences (GPT-4 vs Mixtral) — neither is natively a 3-tier difficulty router; that is part of what we are testing. Use the **same tier descriptions** text across Jev, Arch-Router and the baseline.

### Jev request sketch (Vercel gateway, TypeSafe-compatible route)
```
POST https://ai-gateway.vercel.sh/typesafe/v1/systemone   (Authorization: Bearer $AI_GATEWAY_API_KEY)
{"model":"typesafe-ai/jev",
 "state":{"task": "<query>", "context":"agentic coding assistant request"},
 "questions":{
   "tier":{"type":"choice","instructions":"Which model tier is the cheapest that would reliably complete this coding task?",
           "criteria":{"cheap":"Mechanical edits, typos, renames, simple factual docs questions, small scripts",
                       "mid":"Localized bug fixes, pattern-based multi-file refactors, well-known feature setups",
                       "frontier":"Open-ended architecture, concurrency/perf/production debugging, large behavior-preserving migrations, correctness-critical code"}},
   "difficulty":{"type":"score","instructions":"Reasoning difficulty of the task","criteria":["trivial","easy","moderate","hard","very hard"]},
   "needs_frontier":{"type":"noul","instructions":"A small model would likely fail or introduce subtle bugs on this task"}}}
```
Response gives `answers.tier.choice`, `.probabilities`, `.confidence`; `difficulty.score`; `needs_frontier.noul`.
Alternatives: AI SDK ≥7.0.105 `experimental_evaluate`/`experimental_decide`, `POST /v1/evaluate` or OpenAI-style `POST /v1/decisions` on the gateway, or direct `POST https://api.typesafe.ai/v1/systemone` with `typesafe-sdk` / `@typesafe-ai/sdk`.

## 3. Metrics
- **Accuracy** (exact tier match) + confusion matrix 3×3, per category.
- **Over-routing rate**: predicted tier > label (wasted cost). Report cheap→frontier separately (worst waste).
- **Under-routing rate**: predicted tier < label (quality risk). Report frontier→cheap separately (worst risk). Weighted error: under-routing ×2 vs over-routing ×1 (tunable).
- **Expected cost of routed traffic**: Σ tier price for the 57 queries vs "always frontier" and "always mid" (assumed per-task costs, e.g. cheap $0.002, mid $0.02, frontier $0.20 — document the assumptions).
- **Latency per decision**: p50 / p95 wall-clock over 3 runs, warm. Note Jev is served from US (West Coast) — record client region (box).
- **Cost per 1k decisions**: tokens × price (Jev $0.042/M input, output free); local models = $0 API + CPU time.
- **Calibration** (where probabilities exist: Jev, RouteLLM score, Arch-Router logprobs, baseline logprobs): Brier score, ECE (5 bins), and accuracy at confidence ≥0.8 with coverage.
- **Consistency**: same query 3× → agreement rate (Jev claims determinism-ish; LLMs at temp 0 too).
- **Robustness**: accuracy on the 6 adversarial queries reported separately.

## 4. Procedure
1. Freeze `queries.jsonl` (commit hash in results).
2. Calibration split: q-ids randomly pick 15 for threshold tuning (RouteLLM 3-tier thresholds; optional Jev threshold on `needs_frontier`), evaluate all routers on remaining 42 *and* report full-57 numbers with this caveat.
3. Run each router 3× per query; log `id, router, pred, probs, confidence, latency_ms, tokens` to `results/<router>.jsonl`.
4. `score.py` computes metrics → `results/summary.md`.
5. Prompt variants: one ablation where Jev/Arch/baseline get only "easy vs hard" wording to see sensitivity to tier descriptions.

## 5. Optional label validation (recommended on a subset)
Labels are subjective. Take ~18 queries (6 per label) that can be made concrete (small fixture repo or self-contained snippet with a test). Run each through a **cheap** model and a **frontier** model (single attempt, same harness), grade pass/fail by test or rubric. Relabel rule: cheap passes → `cheap`; only frontier passes → `frontier`; both fail → drop or `frontier`; disagreements with our label are reported. Optionally add a mid model for 3-way. Cost estimate: ~$3–15 depending on models; ~1–2 h including building fixtures.

## 6. Box feasibility (checked 2026-11-01)
8 vCPU Intel Xeon (AVX2/AVX-512), 15 GiB RAM (~6 GiB free at check time), no GPU, 84 GB disk free, Python 3.13.
- Arch-Router-1.5B: runs on CPU. ~3 GB bf16 / ~1.6 GB Q8 GGUF. Est. 1.5–4 s/decision with llama.cpp (prompt ~600–900 tokens incl. routes, ~10 output tokens); 5–15 s with transformers fp32. Must cap `max_new_tokens`≈32 (model card example uses 32768).
- RouteLLM `bert` router: CPU OK, est. 0.1–0.5 s/decision. `mf`/`sw_ranking`: need OpenAI embeddings key (tiny cost). `causal_llm` (8B): not feasible here (RAM/no GPU).
- Small-LLM baseline local (Qwen2.5-1.5B-Instruct Q8): ~1–3 s/decision. Hosted cheap model: ~0.5–2 s.
- Jev: hosted only; vendor claims 70–500 ms end-to-end.

## 7. Estimated effort / cost for full run
- Setup (deps, model downloads ~5 GB, harness + scorer): ~1.5–2 h agent time.
- Runtime: 57 queries × 3 runs × 4 routers ≈ 684 decisions → local ones ~15–30 min total on CPU, Jev ~2 min.
- API cost: Jev ≈ 171 calls × ~600 tokens ≈ 0.1 M tokens ≈ **<$0.01**; hosted baseline <$0.10; RouteLLM mf embeddings <$0.01. Validation step (optional) $3–15.
- Blocker: needs an API credential for Jev (see report) — no free path confirmed.
