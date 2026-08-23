# Lit2Test Subtle Corruption + Sham Audit（20×3×2）

- Status: `complete`
- Valid judgments: `360/360`
- Independent clusters: `20 base cases`
- Primary endpoint: case-level subtle target net preference minus sham original-text net preference
- Bootstrap: `10,000` case-level replicates

## Primary Results

| Dimension | Adjusted preference mean [95% CI] | Subtle target W/T/L | Sham original W/T/L | Sham score diff mean [95% CI] | Sham equivalence | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| `grounding` | 0.550 [0.450, 0.650] | 45/34/1 | 0/40/0 | 0.000 [0.000, 0.000] | pass | `supports_contrast_controlled_local_sensitivity` |
| `decisive_metric` | 0.775 [0.662, 0.887] | 63/16/1 | 0/40/0 | 0.000 [0.000, 0.000] | pass | `supports_contrast_controlled_local_sensitivity` |
| `falsifiability` | 0.537 [0.425, 0.650] | 43/37/0 | 0/40/0 | 0.000 [0.000, 0.000] | pass | `supports_contrast_controlled_local_sensitivity` |

Across dimensions, pooled adjusted preference is **0.621** (95% CI [0.567, 0.679]).

## Construction Audit

- Final original cases: `12`; final reserve replacements: `8`
- Reserve rounds: `4`; replacement attempts: `17`
- Candidate attempts recorded: `516`
- Final selected semantic agreement: `0.656`; tie-breaks: `62/180` (all-candidate agreement: `0.668`)
- Edited-side guess accuracy (non-unknown guesses only): `0.929` over `14` non-unknown guesses; non-unknown rate `0.039`

## Claim Boundary

允许表述：该 contrast-controlled audit 检验 structured Gemini judge 是否对自然、局部、维度定向的 scientific defects 敏感，并用 style-matched sham 校正原文/编辑风格偏好。

禁止据此声称 Gemini 等于人类或客观科研质量、自动 validator 构成人类校准、schema 改善生成质量、三个维度具有独立因果效应，或结果可替代已有 human calibration。

Strong-corruption attenuation 仅对仍使用原 v1 base answer 的 12 个 case 做 paired 描述；reserve replacements 不伪装成同 case 配对。
