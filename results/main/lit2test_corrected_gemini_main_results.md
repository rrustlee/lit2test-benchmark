# Lit2Test corrected Gemini main-result analysis

本报告独立重算 Gemini 主实验；不读取人评校准文件，不调用 API，也不修改冻结的 task/judgment/manifest。旧结果使用 manifest 中每个 ordered pair 的 latest-valid judgment；corrected 结果仅替换 expansion40_adjudicated40 中 65 个真正 reverse correction judgments。

- Ordered judgments: `2400/2400` (old and corrected)
- Folded cases: `1200/1200`
- Old task orientation: `{'correctly_swapped': 1135, 'same_order': 65}`
- Corrected task orientation: `{'correctly_swapped': 1200}`
- Correction override: `65`; bootstrap: `10000` case replicates, seed `20260721`

## Ordered W/L/T and side counts

| Model | Old W | Old L | Old T | Corrected W | Corrected L | Corrected T |
|---|---:|---:|---:|---:|---:|---:|
| GPT 5.2 | 977 | 223 | 0 | 975 | 225 | 0 |
| GLM-5 | 372 | 828 | 0 | 375 | 825 | 0 |
| DeepSeek-V3.2 | 223 | 977 | 0 | 222 | 978 | 0 |
| Claude-Sonnet-4.6-hq | 828 | 372 | 0 | 828 | 372 | 0 |

- Old winner side counts: `{'A': 1430, 'B': 970, 'tie': 0}`
- Corrected winner side counts: `{'A': 1440, 'B': 960, 'tie': 0}`

## Six model-pair ordered outcomes

| Model pair | Old wins/ties | Corrected wins/ties |
|---|---|---|
| `DeepSeek-V3.2 | Claude-Sonnet-4.6-hq` | DeepSeek-V3.2 45, Claude-Sonnet-4.6-hq 355; tie 0 | DeepSeek-V3.2 45, Claude-Sonnet-4.6-hq 355; tie 0 |
| `GLM-5 | Claude-Sonnet-4.6-hq` | GLM-5 75, Claude-Sonnet-4.6-hq 325; tie 0 | GLM-5 75, Claude-Sonnet-4.6-hq 325; tie 0 |
| `GLM-5 | DeepSeek-V3.2` | GLM-5 244, DeepSeek-V3.2 156; tie 0 | GLM-5 247, DeepSeek-V3.2 153; tie 0 |
| `GPT 5.2 | Claude-Sonnet-4.6-hq` | GPT 5.2 252, Claude-Sonnet-4.6-hq 148; tie 0 | GPT 5.2 252, Claude-Sonnet-4.6-hq 148; tie 0 |
| `GPT 5.2 | DeepSeek-V3.2` | GPT 5.2 378, DeepSeek-V3.2 22; tie 0 | GPT 5.2 376, DeepSeek-V3.2 24; tie 0 |
| `GPT 5.2 | GLM-5` | GPT 5.2 347, GLM-5 53; tie 0 | GPT 5.2 347, GLM-5 53; tie 0 |

## Bradley–Terry (ordered judgments)

| Model | Old ability | Old 95% CI | Corrected ability | Corrected 95% CI |
|---|---:|---|---:|---|
| GPT 5.2 | 1.275066 | [1.145490, 1.415133] | 1.265050 | [1.135133, 1.403131] |
| GLM-5 | -0.743604 | [-0.872830, -0.621847] | -0.731306 | [-0.856724, -0.611949] |
| DeepSeek-V3.2 | -1.275066 | [-1.421077, -1.142956] | -1.276136 | [-1.422736, -1.146037] |
| Claude-Sonnet-4.6-hq | 0.743604 | [0.622878, 0.872715] | 0.742392 | [0.622307, 0.870320] |

- Old modal ranking: `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2` (1.0000)
- Corrected modal ranking: `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2` (1.0000)
- Top-5 old: `{'GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2': 10000}`
- Top-5 corrected: `{'GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2': 10000}`

## Condorcet

- Old: winner `GPT 5.2`, transitive `True`, beat counts `{'GPT 5.2': 3, 'GLM-5': 1, 'DeepSeek-V3.2': 0, 'Claude-Sonnet-4.6-hq': 2}`
- Corrected: winner `GPT 5.2`, transitive `True`, beat counts `{'GPT 5.2': 3, 'GLM-5': 1, 'DeepSeek-V3.2': 0, 'Claude-Sonnet-4.6-hq': 2}`

## Folded sensitivity

| Scope | Stable | Unstable | Folded BT ranking |
|---|---:|---:|---|
| Old | 959 | 241 | `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2` |
| Corrected | 950 | 250 | `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2` |

65-case stability transitions: `{'order-stable -> order-stable': 48, 'order-stable -> order-unstable': 11, 'order-unstable -> order-unstable': 4, 'order-unstable -> order-stable': 2}`; changed labels: `13`.

### Changed correction cases

| Pair | Old reverse winner | Corrected reverse winner | Old label | Corrected label |
|---|---|---|---|---|
| `smallari_expansion40_002_unlearning_machine_language_use_algorithms__v02_expansion40__DeepSeek-V3.2__vs__GPT_5.2` | `GPT 5.2` | `DeepSeek-V3.2` | `order-stable` | `order-unstable` |
| `smallari_expansion40_011_test_time_adaptation_active_tta_test__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `GLM-5` | `DeepSeek-V3.2` | `order-unstable` | `order-stable` |
| `smallari_expansion40_011_test_time_adaptation_active_tta_test__v02_expansion40__DeepSeek-V3.2__vs__GPT_5.2` | `GPT 5.2` | `DeepSeek-V3.2` | `order-stable` | `order-unstable` |
| `smallari_expansion40_011_test_time_adaptation_active_tta_test__v02_expansion40__GLM-5__vs__GPT_5.2` | `GLM-5` | `GPT 5.2` | `order-stable` | `order-unstable` |
| `smallari_expansion40_017_group_fairness_individual_in_processing_fair__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `GLM-5` | `DeepSeek-V3.2` | `order-stable` | `order-unstable` |
| `smallari_expansion40_021_brain_semantics_language_speech_lack__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_022_series_time_language_llms_bridge__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_024_causal_language_inference_discovery_graph__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_029_bottleneck_concept_concepts_information_cbms__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_029_bottleneck_concept_concepts_information_cbms__v02_expansion40__GLM-5__vs__GPT_5.2` | `GPT 5.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_032_jailbreak_language_attacks_adversarial_attack__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_034_equivariant_networks_breaking_symmetry_simple__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `DeepSeek-V3.2` | `GLM-5` | `order-stable` | `order-unstable` |
| `smallari_expansion40_039_generation_diffusion_multi_view_both_high_qualit__v02_expansion40__DeepSeek-V3.2__vs__GLM-5` | `GLM-5` | `DeepSeek-V3.2` | `order-unstable` | `order-stable` |

The correction changes only Gemini reverse evidence for the 65 affected pairs. Human-visible answers and human annotations are outside this analysis and remain untouched.
