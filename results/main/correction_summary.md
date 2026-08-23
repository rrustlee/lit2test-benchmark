# Lit2Test expansion40 Reverse Correction (65) Summary

The isolated correction completed all 65 true-reverse Gemini judgments and rebuilt order stability without modifying frozen human cases or legacy source artifacts.

## Completion

- Valid correction judgments: `65/65`.
- Correctly oriented full pairs: `1200/1200`.
- Corrected ordered judgments available: `2400/2400`.
- Affected formal cases retained: `4/4`.

## Corrected Stability

| Scope | Stable | Unstable | Total |
|---|---:|---:|---:|
| Old all-pair metadata | 959 | 241 | 1200 |
| Corrected all pairs | 950 | 250 | 1200 |
| Old formal 90 | 60 | 30 | 90 |
| Corrected formal 90 | 60 | 30 | 90 |

Correction-set transitions: `{'order-stable -> order-stable': 48, 'order-stable -> order-unstable': 11, 'order-unstable -> order-stable': 2, 'order-unstable -> order-unstable': 4}`.

## Four Retained Formal Cases

| Case | Pair | Original winner | Corrected reverse winner | Old label | Corrected label |
|---|---|---|---|---|---|
| `t2_formal_017` | `smallari_expansion40_040_critic_reinforcement_actor_critic_actor_continuo__v02_expansion40__DeepSeek-V3.2__vs__GPT_5.2` | `GPT 5.2` | `GPT 5.2` | `order-stable` | `order-stable` |
| `t2_formal_085` | `smallari_expansion40_024_causal_language_inference_discovery_graph__v02_expansion40__DeepSeek-V3.2__vs__GPT_5.2` | `GPT 5.2` | `GPT 5.2` | `order-stable` | `order-stable` |
| `t2_formal_088` | `smallari_expansion40_001_cache_compression_llms_long_context__v02_expansion40__GLM-5__vs__GPT_5.2` | `GPT 5.2` | `GPT 5.2` | `order-stable` | `order-stable` |
| `t2_formal_093` | `smallari_expansion40_025_audio_visual_multimodal_aligned_language_visual__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `GLM-5` | `GLM-5` | `order-stable` | `order-stable` |

The human-visible context and original A/B answers are unchanged. These cases remain in the completed 90-case human study; only Gemini reverse evidence and derived stability metadata are corrected.

## Per-Model-Pair Corrected Stability

| Model pair | Stable | Unstable | Total |
|---|---:|---:|---:|
| `Claude-Sonnet-4.6-hq | DeepSeek-V3.2` | 177 | 23 | 200 |
| `Claude-Sonnet-4.6-hq | GLM-5` | 161 | 39 | 200 |
| `Claude-Sonnet-4.6-hq | GPT 5.2` | 128 | 72 | 200 |
| `DeepSeek-V3.2 | GLM-5` | 139 | 61 | 200 |
| `DeepSeek-V3.2 | GPT 5.2` | 184 | 16 | 200 |
| `GLM-5 | GPT 5.2` | 161 | 39 | 200 |
