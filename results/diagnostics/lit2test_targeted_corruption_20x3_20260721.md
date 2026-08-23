# Lit2Test Targeted Corruption Audit（20×3×2）

本实验只支持 `localized counterfactual judge sensitivity`：它检查固定答案中单字段缺陷是否被 Gemini 的对应维度察觉，不是人类 gold label、生成质量实验或 leaderboard。

- Status: `complete`
- Valid judgments: `120/120`
- Canonical cases: `20`
- Canonical pairs: `60`
- Bootstrap: `10,000` case-level replicates
- Confidence weighting: `False`

## Results

| Target dimension | Clean overall wins | Both-order clean wins | Target drop, mean [95% CI] | Target drop, median [95% CI] | Non-target abs drift, mean [95% CI] | Order consistency | Direct flips | Corrupt wins | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `grounding` | 40/40 (1.000) | 20/20 | 1.725 [1.600, 1.850] | 1.750 [1.500, 2.000] | 0.000 [0.000, 0.000] | 20/20 (1.000) | 0 | 0 | 0 |
| `decisive_metric` | 40/40 (1.000) | 20/20 | 2.000 [2.000, 2.000] | 2.000 [2.000, 2.000] | 0.006 [0.000, 0.019] | 20/20 (1.000) | 0 | 0 | 0 |
| `falsifiability` | 40/40 (1.000) | 20/20 | 1.950 [1.850, 2.000] | 2.000 [2.000, 2.000] | 0.000 [0.000, 0.000] | 20/20 (1.000) | 0 | 0 | 0 |

## Claim Boundary

允许表述：该局部反事实审计检验 judge 是否对单个 rubric dimension 的定向缺陷敏感。若对应分数下降且非目标维度漂移较小，可称为 dimension-specific local sensitivity。

禁止据此声称 schema 提升生成 idea、falsifier 要求改善科研结果、Gemini 等于客观科研质量、falsifiability 必然最有区分力，或 Lit2Test 已获得 benchmark-wide human validation。
