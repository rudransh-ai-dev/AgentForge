# Optimal local LLM setup for a 7-agent system on 16 GB VRAM

**The RTX 5070 Ti can power a capable multi-agent system, but only with disciplined model selection and a hot-swap scheduling strategy.** No 16 GB GPU can run seven distinct large models simultaneously — the winning approach combines two to three VRAM-efficient models with role-specific system prompts and Ollama's built-in scheduler. After benchmarking every model in the user's installed list against 2025–2026 coding, reasoning, and agentic evaluations, the optimal strategy centers on **GPT-OSS 20B** (MoE, ~12 GB) as the primary workhorse, **Qwen 2.5-Coder 14B** (~11 GB) as the coding specialist, and **Qwen 3.5 9B** (~6 GB) as the lightweight utility agent — swapping between them rather than loading all at once.

---

## What actually fits in 16 GB VRAM

The RTX 5070 Ti's **896 GB/s GDDR7 bandwidth** makes it exceptionally fast for LLM inference — roughly 78% faster than the RTX 4070 Ti — but the 16 GB ceiling is the binding constraint. VRAM consumption follows a simple formula: model weights plus KV cache plus ~0.5–1 GB runtime overhead. At Q4_K_M quantization (the sweet spot for quality-to-size), the numbers break down cleanly.

| Model category | Weight size (Q4_K_M) | Total VRAM at 8K context | Fits 16 GB? | Max context in 16 GB |
|---|---|---|---|---|
| 7–8B dense | ~4.7–4.9 GB | **~6 GB** | ✅ Easily | 64K+ |
| 13–14B dense | ~8.9–9.0 GB | **~10.5–11 GB** | ✅ Comfortable | 16K–24K |
| GPT-OSS 20B (MoE, MXFP4) | ~12 GB | **~12 GB** | ✅ Good | 128K native |
| Codestral 22B dense | ~12.5 GB | **~14 GB** | ✅ Tight | 8K–16K |
| Devstral 24B dense | ~14.3 GB | **~15 GB** | ⚠️ Borderline | 4K–8K |
| Gemma 4 26B MoE | ~14 GB | **~14–16 GB** | ⚠️ Tight | 4K–8K |
| Qwen 3.5 27B dense | ~15.6 GB | **~17+ GB** | ❌ Overflows | Partial CPU offload |

The critical insight: **Qwen 3.5 27B at Q4_K_M does not fit in 16 GB VRAM.** It will partially offload to CPU RAM, dropping throughput from ~60 tokens/sec to ~18 tokens/sec — a 3× penalty. For a responsive agentic system, every model must load entirely into VRAM.

Enabling `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0` effectively doubles usable context length at no quality cost and should be considered mandatory on this hardware.

---

## How each installed model ranks for the seven agent roles

After cross-referencing SWE-bench Verified, LiveCodeBench v6, AIME 2025/2026, HumanEval, MMLU-Pro, and τ2-bench agentic scores, clear winners emerge for each role. The rankings below consider both benchmark performance and practical VRAM fit on the 5070 Ti.

**Orchestrator/Supervisor (complex reasoning, task routing):** GPT-OSS 20B dominates. Its MoE architecture activates only **3.6B of 21B parameters per token**, delivering o3-mini-class reasoning at ~156 tokens/sec on the 5070 Ti. Native function calling, configurable reasoning depth (low/medium/high), and the Harmony response format make it purpose-built for orchestration. It scores **96–98% on AIME 2025** and has strong τ-bench agentic results. At ~12 GB VRAM, it leaves headroom. Gemma 4 26B is the runner-up (3.8B active, strong tool use, 88% AIME 2026) but fits more tightly at 14–16 GB.

**Senior Coder (code generation, algorithms):** Qwen 2.5-Coder 14B is the practical winner at ~11 GB VRAM, scoring **~85–87% HumanEval** and outperforming CodeStral 22B and DeepSeek-Coder-33B despite being smaller. Codestral 22B offers superior fill-in-the-middle capability (91.6% HumanEvalFIM) but costs ~14 GB, and Devstral's 68% SWE-bench Verified is impressive for agentic coding but its 24B dense architecture makes it a very tight fit. For users willing to import a community GGUF, **Apriel 1.5 15B** scores ~73% on LiveCodeBench at just ~9 GB VRAM.

**QA Reviewer/Critic (code auditing, bug detection):** Qwen 3.5 9B is the best value here — latest-generation reasoning with `<think>` mode for deep analysis at only **~6 GB VRAM**. It outperforms GPT-OSS 120B on several benchmarks despite being 13× smaller. Phi-4 (14B) is an alternative with strong STEM reasoning (77.7% AIME 2025 for the reasoning variant) but its 16K context limit is restrictive for reviewing large files.

**Research Synthesizer (document parsing, context gathering):** Qwen 2.5 14B excels with **128K native context**, strong multilingual support (covering documentation in any language), and balanced coding/reasoning scores (83.5% HumanEval, 94.8% GSM8K). At ~11 GB VRAM it processes large documents comfortably. Qwen 3.5 9B is the lighter alternative at ~6 GB with 256K context.

**System Architect (high-level planning):** This role mirrors the Orchestrator — it needs broad knowledge, reasoning depth, and structured output. GPT-OSS 20B serves double duty here with different system prompts. If a distinct model is preferred, Gemma 4 26B's multimodal capability (reading architecture diagrams) adds unique value, though it sits at the VRAM ceiling.

**DevOps Agent (shell commands, environment management):** DeepSeek-R1 8B at **~6 GB** handles command generation and troubleshooting well, scoring 89.1% on MATH-500 and demonstrating strong step-by-step reasoning. Qwen 3.5 9B is a stronger general-purpose alternative. For this role, a smaller model is ideal since DevOps queries tend to be shorter and more formulaic.

**Context Manager (memory management):** This lightweight routing/summarization role needs minimal reasoning power. Gemma 4 E4B at **~3 GB** or Phi-3 Mini at **~2 GB** are sufficient. Keeping this model permanently loaded alongside larger specialist models is the key to efficient scheduling.

---

## GPT-OSS 20B vs Apriel 1.5 15B vs Qwen3 14B for coding

These three models represent different architectural philosophies, and the best choice depends on the specific coding task type.

**Apriel 1.5 15B leads on composite intelligence.** ServiceNow's model achieves an Artificial Analysis Intelligence Index of **52** — matching DeepSeek-R1-0528 and exceeding GPT-OSS 20B's score of 24–43 (depending on evaluation configuration). On LiveCodeBench, Apriel scores ~73% versus GPT-OSS's ~70%. It also supports vision (useful for reading screenshots or UI mockups). However, Apriel's Ollama support is community-only — no official listing, and users report chat template issues. At Q4_K_M it needs just ~9 GB VRAM, making it the most memory-efficient option.

**GPT-OSS 20B leads on reasoning and agentic tasks.** With 96–98% on AIME 2025 and 60.7% on SWE-bench Verified, it outperforms Apriel on mathematical reasoning by a wide margin. Its MoE architecture makes inference dramatically faster (3.6B active params versus Apriel's full 15B). Native function calling and the Harmony response format give it the best out-of-the-box agentic capability. The trade-off is verbosity — GPT-OSS generates significantly more reasoning tokens, especially at high effort.

**Qwen3 14B is the most practical all-rounder.** Its base model scores 72.23% on EvalPlus (coding) — matching Qwen 2.5-32B despite half the parameters. The hybrid thinking mode lets it toggle between fast responses and deep reasoning. Official Ollama support, Apache 2.0 licensing, and a massive community make it the safest choice. At ~9–10 GB VRAM, it coexists well with smaller models.

| Metric | GPT-OSS 20B | Apriel 1.5 15B | Qwen3 14B |
|---|---|---|---|
| Active params per token | **3.6B** (MoE) | 15B (dense) | 14.8B (dense) |
| LiveCodeBench | ~70% | **~73%** | ~72% (EvalPlus) |
| AIME 2025 | **96–98%** | 87–88% | ~comparable to Q2.5-32B |
| SWE-bench Verified | **60.7%** | N/A | N/A |
| VRAM (Q4_K_M) | ~12 GB | **~9 GB** | ~9–10 GB |
| Ollama support | ✅ Official | ⚠️ Community | ✅ Official |
| Inference speed | **Fastest** (MoE) | Moderate | Moderate |
| Vision/multimodal | ❌ | ✅ | ❌ |

**Recommendation:** Install GPT-OSS 20B as the primary reasoning/orchestration model and keep Qwen 2.5-Coder 14B for pure code generation. Add Apriel 1.5 15B only after its Ollama support matures — its intelligence density is exceptional but ecosystem friction is real.

---

## The optimal scheduling strategy for seven agents on 16 GB

Running seven distinct models simultaneously is impossible on 16 GB. But Ollama's scheduler, introduced in September 2025, performs **exact memory measurement** and handles model swapping automatically. The practical architecture uses three tiers.

**Tier 1 — Always resident (~6 GB).** Keep Qwen 3.5 9B loaded permanently with `keep_alive=-1`. This model handles Context Manager duties and serves as a fast fallback for QA Review and DevOps tasks via different system prompts. At 6 GB, it leaves 10 GB for specialist models.

**Tier 2 — Primary specialists (~10–12 GB each, hot-swapped).** GPT-OSS 20B handles Orchestrator and System Architect roles. Qwen 2.5-Coder 14B handles Senior Coder tasks. These swap into the remaining ~10 GB as needed. Swap time is **10–20 seconds** on NVMe SSD, which is acceptable for agentic workflows where each agent's task takes 30–120 seconds anyway.

**Tier 3 — On-demand specialists.** Codestral 22B, Devstral, or Gemma 4 26B load only for specialized tasks requiring their unique capabilities (fill-in-the-middle completion, multi-file refactoring, or multimodal input). These evict the Tier 2 model currently loaded.

The single most impactful optimization: **reuse the same model for multiple agent roles with different system prompts.** Ollama loads a model once and can serve parallel requests via `OLLAMA_NUM_PARALLEL`. GPT-OSS 20B with different system prompts can credibly serve as Orchestrator, System Architect, and Research Synthesizer — three roles from one 12 GB model load.

**Recommended Ollama configuration:**

```bash
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_KEEP_ALIVE=5m"
Environment="OLLAMA_GPU_OVERHEAD=536870912"
```

---

## Recommended model-to-role assignment map

Based on all benchmarks, VRAM constraints, and scheduling realities, this is the optimal assignment:

| Agent role | Primary model | VRAM | Why this model | Fallback |
|---|---|---|---|---|
| **Orchestrator** | gpt-oss:20b | ~12 GB | Best tool calling, MoE speed, configurable reasoning | gemma4:26b |
| **Senior Coder** | qwen2.5-coder:14b | ~11 GB | 85–87% HumanEval, best coding specialist that fits | codestral:22b (~14 GB) |
| **QA Reviewer** | qwen3.5:9b | ~6 GB | Think mode for deep analysis, tiny footprint | phi4 (~11 GB) |
| **Research Synthesizer** | qwen2.5:14b | ~11 GB | 128K context, strong comprehension | qwen3.5:9b (256K ctx) |
| **System Architect** | gpt-oss:20b* | ~0 GB* | *Shares model with Orchestrator, different prompt | gemma4:26b |
| **DevOps Agent** | qwen3.5:9b* | ~0 GB* | *Shares model with QA Reviewer, different prompt | deepseek-r1:8b |
| **Context Manager** | gemma4:e4b | ~3 GB | Ultra-light, summarization-grade, always loadable | phi3:mini (~2 GB) |

*Models marked with asterisk share a loaded model with another role — zero additional VRAM cost.

This configuration requires only **three distinct model loads** at peak: Qwen 3.5 9B (~6 GB, resident) + GPT-OSS 20B (~12 GB, swapped in) or Qwen 2.5-Coder/14B (~11 GB, swapped in). Two models fit simultaneously when the smaller one is resident. Total peak VRAM: **~14–15 GB** — comfortably within the 16 GB envelope.

---

## Models to retire and models to add

From the installed list, several models are now redundant. **CodeLlama 13B** (August 2023) is outperformed by Qwen 2.5-Coder 14B on every metric. **Mistral 7B** (September 2023) is superseded by Qwen 3.5 9B. **Phi-3 Mini** is replaced by Gemma 4 E4B for lightweight tasks. **DeepSeek-Coder-V2 16B** offers no advantage over Qwen 2.5-Coder 14B. Removing these frees disk space and reduces confusion in model selection.

Models worth adding: **Qwen3 14B** (`ollama pull qwen3:14b`) offers hybrid thinking mode and matches Qwen 2.5-32B on coding benchmarks at half the parameters — a strong candidate for QA Review if Phi-4's 16K context limit proves restrictive. **Apriel 1.5 15B** is worth monitoring but should wait for official Ollama library inclusion before production use. The user's existing GPT-OSS 20B is already the optimal orchestrator choice.

The RTX 5070 Ti's native **FP4 hardware acceleration** (Blackwell architecture) gives GPT-OSS 20B a unique advantage: its MXFP4 quantization runs at **156 tokens/sec at 4K context** — faster than any dense 14B model. This hardware-model synergy makes GPT-OSS the single most impactful model in the entire stack for this specific GPU.

---

## Conclusion

The path to a responsive 7-agent system on 16 GB VRAM is **model consolidation, not model proliferation**. Three carefully chosen models — GPT-OSS 20B for reasoning/orchestration, Qwen 2.5-Coder 14B for code generation, and Qwen 3.5 9B as a versatile lightweight agent — cover all seven roles through prompt differentiation and hot-swapping. The MoE architecture of GPT-OSS 20B is the linchpin: it delivers 27B-class intelligence at 7B-class inference speed, and the 5070 Ti's Blackwell FP4 hardware accelerates it beyond anything a dense model can achieve at this VRAM tier. Avoid the temptation to load the largest models possible — a 14B model fully in VRAM will always outperform a 27B model partially spilled to CPU RAM. Enable Flash Attention and KV cache quantization, keep context windows conservative (4K–8K for most agents), and let Ollama's scheduler handle the swapping. The bottleneck is not model intelligence — it is VRAM discipline.