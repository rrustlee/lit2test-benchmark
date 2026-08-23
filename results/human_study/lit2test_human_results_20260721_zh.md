# Lit2Test 人类校准结果：两阶段结论与统计证据

> 分析日期：2026-07-21（Asia/Shanghai）  
> 结果范围：当前正式版 `20` 个 Task 1 neighborhood cases、`90` 个 Task 2 real pairs、`4` 个 hidden real-vs-naive controls、`3` 位 annotators  
> 分析原则：以 case 为统计单位；controls 单独分析；stable 与 unstable Gemini pairs 分开；不使用 LLM 重判 case；不调用外部 API  
> Bootstrap：按 case 重采样，`10,000` 次，随机种子 `20260721`

---

# 第一阶段：直观结论

## 1. 总体判断

人类反馈在宏观层面支持 Lit2Test 的核心方法论：抽样 neighborhood 总体可用，人工能够识别明显的 naive answers，Gemini 在顺序稳定且人类形成明确多数的比较上与人类高度一致，人类偏好也恢复了与 Gemini 全量评测一致的模型层级结构。

这组结果适合支撑“数据与 judge workflow 在聚合层面可靠”的论文主结论。它不适合支撑更强的表述，例如所有 200 个 neighborhood 均经人类验证、Gemini 在每个 pair 上都准确、人工能稳定恢复精确的四模型全序，或 falsifiability 是最有区分力的质量维度。

一句话概括：

> Human evaluation supports the benchmark's core data and judging workflow at the aggregate level, while revealing uncertainty in fine-grained quality dimensions, order-sensitive comparisons, and adjacent-model rankings.

## 2. 得到支持的核心结论

| 核心主张 | 主要人类证据 | 支持强度 |
|---|---|---|
| 抽样 neighborhood 总体可用 | `16/20` cases 获得 majority keep；relatedness 与 grounding 的 case-level median 接近满分 `2` | 支持，但范围仅为 20/200 分层样本 |
| 人工可以检测明显的 naive answer | 按 naive-presence detection 口径，hidden controls 为 `11/12` | 支持，可作为 sanity check |
| Gemini stable judgments 与人类偏好一致 | `39/60` stable cases 形成 decisive human majority，其中 `34/39 = 87.2%` 与 Gemini 一致 | 较强支持 |
| Gemini 的聚合模型层级合理 | Human BT 点估计恢复 `GPT > Sonnet > GLM > DeepSeek` | 支持 |
| 人类结果稳定恢复宏观 tier structure | `88.3%` 的 bootstrap 排名与 Gemini 相差不超过 1 个逆序；`100%` 保持 `{GPT, Sonnet}` 与 `{GLM, DeepSeek}` 的上下两层划分 | 较强支持 |
| 主结论不由 r3 的 A-side bias 单独制造 | 只使用 r1+r2 共识时，stable agreement 为 `26/30 = 86.7%`，BT 点排序不变 | 支持 |

## 3. 没有得到充分支持的细节结论

| 细节主张 | 实际结果 | 判断 |
|---|---|---|
| 人类标注者高度一致 | Task 1 `overall_keep` alpha=`0.127`；Task 2 winner alpha=`0.238` | 不支持 |
| Gemini unstable pairs 对人类明显更难 | unstable confidence 没有更低，五维绝对分差也没有更小 | 不支持 |
| Order instability 普遍代表 genuine ambiguity | Sonnet–GPT 等相邻模型出现明显 tie，但 stable/unstable 的总体差异较弱 | 仅局部支持 |
| Falsifiability 是最有区分力的维度 | human winner–loser falsifiability margin 为 `0`；`no_real_falsification` 很少成为 primary weakness | 不支持 |
| 人类能稳定恢复精确四模型全序 | exact-order bootstrap 仅 `40.9%` | 不充分；宏观 tier structure 更稳定 |
| 相邻模型顺序高度稳定 | GPT/Sonnet 与 GLM/DeepSeek 在 bootstrap 中会互换 | 不支持强表述 |
| 全部 200 个 neighborhoods 均经人类验证 | 人类只检查了 20/200 的分层样本 | 不支持 |
| Gemini 在所有 pair 上都准确 | 主 agreement 仅适用于 stable 且 human-decisive 的 `39/60` cases | 不支持 |
| 人类标注不存在位置偏差 | r3 在 decisive votes 中选择 A 的比例为 `52/64 = 81.3%` | 不支持 |

## 4. 最合适的论文定位

人类校准可以分成三层叙述：

1. **输入有效性。** 抽样 neighborhood 总体可用；人类对精确质量等级的统一程度有限。
2. **Judge validity。** Gemini stable judgments 与 decisive human majority 高度一致，支持 judge workflow 的聚合可靠性。
3. **聚合排序。** Human BT 点估计与 Gemini 全量排序一致；`88.3%` bootstrap 至多相差一个逆序，且 top-2/bottom-2 tier 在所有 bootstrap 中保持不变。相邻模型的先后仍有不确定性。

推荐正文主结论：

> Human evaluation supports the usability of the sampled benchmark inputs and shows substantial alignment between human preferences and Gemini judgments on stable comparisons. Human-derived rankings recover the same point-estimate ordering and a robust tier structure, with uncertainty concentrated in adjacent model pairs.

推荐限制边界：

> The study provides calibration evidence on a stratified subset rather than benchmark-wide human validation. Inter-annotator agreement is modest, and the data do not establish that order instability generally corresponds to human difficulty or that falsifiability is the most discriminative quality dimension.

---

# 第二阶段：详细统计证据

## 5. 数据版本、完整性与分析口径

### 5.1 正式版本确认

三套结果均属于当前正式 `90+4` 方案，不属于 legacy MVP182：

- Task 1：每位 annotator `20` rows；三人共 `60` rows；
- Task 2：每位 annotator `94` rows；三人共 `282` rows；
- Task 2 real：每人 `90`，三人共 `270` judgments；
- Hidden controls：每人 `4`，三人共 `12` judgments；
- Gemini-stable / unstable real pairs：`60/30`；
- 六个 model pairs：每组 `15` cases；
- 五个 A/B 评分维度：grounding、hypothesis specificity、minimality/feasibility、decisive metric、falsifiability。

三套结果的 case ID、case 顺序、batch、context ID 和 pair display ID 均与 formal manifest 一致。没有出现 `mvp182_cal_*` case ID 或旧版三维字段。

### 5.2 r1 CSV 修复

r1 原始 CSV 的 `notes_zh` 中存在未转义逗号：

- Task 1：`7/20` rows；
- Task 2：`1/94` row。

修复仅将最后一列之后的尾部字段重新合并进 `notes_zh`。所有 case ID、winner、维度分数、confidence、difficulty、time 和其他非备注字段逐单元格保持不变。修复前后的全部统计结果一致。

修复版：

- `human_cali/repaired/r1/annotation1.csv`
- `human_cali/repaired/r1/annotation2.csv`

### 5.3 Integrity table

| Annotator | Task 1 rows | Task 2 rows | Missing | Duplicates | Invalid values | Validator |
|---|---:|---:|---:|---:|---:|---|
| r1 | 20 | 94 | 0 | 0 | 0 | PASS |
| r2 | 20 | 94 | 0 | 0 | 0 | PASS |
| r3 | 20 | 94 | 0 | 0 | 0 | PASS |

Task 2 的 `INVALID` 是合法标注值，不属于 invalid field value。三位 annotator 在 `90` 个 real cases 中均未使用 `INVALID`；r1 的四个 `INVALID` 全部出现在 hidden controls。

### 5.4 统计原则

- 主要统计单位为 case，不将三位 annotator 的 270 条 real rows 当作 270 个独立实验样本；
- Controls 不进入 Gemini-human agreement、dimension analysis、weakness taxonomy 或 BT ranking；
- Stable Gemini pairs 提供主 agreement；unstable pairs 只作诊断；
- Confidence 不作为主结果权重；
- 比例、差值和 BT robustness 使用 case-level bootstrap；
- 主报告保留所有 annotators；r3 的 position bias 通过 sensitivity 分析处理，不作事后删除。

## 6. Task 1：Neighborhood Quality

### 6.1 Overall keep 与材料充分性

| 指标 | 结果 |
|---|---:|
| Annotator rows：keep | `44/60` |
| Annotator rows：revise | `13/60` |
| Annotator rows：drop | `3/60` |
| Case-level majority keep | `16/20` |
| Case-level majority revise | `4/20` |
| Case-level majority drop | `0/20` |
| 三人 unanimous | `9/20` |
| 2-of-3 majority | `20/20` |
| no-consensus | `0/20` |
| needs_full_text=no | `49/60` |
| needs_full_text=maybe | `10/60` |
| needs_full_text=yes | `1/60` |
| outlier count=0 | `49/60` |
| outlier count=1 | `7/60` |
| outlier count=2 | `4/60` |

三位 annotator 的基本行为：

| Annotator | Keep/Revise/Drop | Confidence high/medium/low | Difficulty easy/medium/hard | Mean time |
|---|---|---|---|---:|
| r1 | 16/4/0 | 13/6/1 | 11/9/0 | 6.45 min |
| r2 | 14/6/0 | 2/17/1 | 2/12/6 | 4.45 min |
| r3 | 14/3/3 | 14/3/3 | 7/10/3 | 8.40 min |

### 6.2 三个质量维度

全部 60 条 annotator rows 的分布：

| Dimension | Score 0 | Score 1 | Score 2 | Case-level median mean |
|---|---:|---:|---:|---:|
| paper relatedness | 0 | 11 | 49 | 1.90 |
| open-problem grounding | 2 | 8 | 50 | 1.95 |
| answerability | 4 | 22 | 34 | 1.60 |

Case-level median 不高于 1 的 cases：

- paper relatedness：`t1_formal_006`, `t1_formal_017`；
- open-problem grounding：`t1_formal_018`；
- answerability：`t1_formal_001`, `002`, `005`, `006`, `011`, `012`, `015`, `018`。

五个 batch 每个只有 4 cases，以下统计仅作描述：

| Batch | Relatedness mean | Grounding mean | Answerability mean | Majority keep |
|---|---:|---:|---:|---:|
| expansion40 | 1.83 | 1.92 | 1.42 | `2/4` |
| next40 | 1.75 | 1.92 | 1.50 | `3/4` |
| third40 | 1.83 | 1.67 | 1.33 | `4/4` |
| fourth40 | 1.92 | 1.83 | 1.67 | `4/4` |
| fifth40 | 1.75 | 1.67 | 1.58 | `3/4` |

### 6.3 Task 1 inter-annotator agreement

| Metric | Raw all-three | Pairwise agreement r1-r2 / r1-r3 / r2-r3 | Krippendorff alpha | 95% case-bootstrap CI |
|---|---:|---|---:|---|
| overall_keep | `9/20` | `0.80 / 0.55 / 0.55` | `0.127` | `[-0.094, 0.307]` |
| paper relatedness | `13/20` | `0.85 / 0.65 / 0.80` | `0.234` | `[-0.157, 0.614]` |
| open-problem grounding | `11/20` | `0.80 / 0.60 / 0.70` | `-0.085` | `[-0.204, 0.090]` |
| answerability | `5/20` | `0.50 / 0.45 / 0.45` | `0.059` | `[-0.179, 0.293]` |

`overall_keep alpha=0.1265` 的组成：

- 60 个标签中：keep `44`、revise `13`、drop `3`；
- 观察到的 disagreement `Do=0.3667`；
- 根据总体标签分布估计的偶然 disagreement `De=0.4198`；
- `alpha = 1 - Do/De = 0.1265`。

该数值表示超出偶然水平的一致性较弱。它不是“12.65% 正确率”。项目没有预注册 IAA threshold，因此本报告不使用事后 alpha gate。

### 6.4 Task 1 结论边界

支持：

> On a stratified 20/200 sample, annotator majorities retained 16 neighborhoods, and most ratings judged the neighborhoods related and grounded at the abstract level.

不支持：

> All 200 neighborhoods were expert-validated.

人类结果支持 sampled neighborhood usability。数据来源真实性和 provenance 仍由已有自动审计支撑，不由这 20 个 case 的人评单独证明。

## 7. Hidden real-vs-naive controls

### 7.1 主口径：naive-presence detection

本报告按项目 intended purpose 将 control success 定义为：

1. 直接选中 real answer 所在的 A/B 侧；或
2. 使用 `INVALID + not_about_task`，明确识别出 pair 中存在不可接受的 naive answer。

| Case | Real side | Naive side | r1 | r2 | r3 | Detection success |
|---|---|---|---|---|---|---:|
| t2_formal_022 | B | A | INVALID | B | B | `3/3` |
| t2_formal_029 | B | A | INVALID | B | TIE | `2/3` |
| t2_formal_046 | A | B | INVALID | A | A | `3/3` |
| t2_formal_071 | A | B | INVALID | A | A | `3/3` |

合计：

- r1：`4/4`；
- r2：`4/4`；
- r3：`3/4`；
- 总计：`11/12 = 91.7%`。

这支持正文中的一句 sanity-check 结论：

> We inserted four hidden real-vs-naive controls to sanity-check human judgment. Annotators detected the naive answer in 11 of 12 judgments.

### 7.2 附录敏感性：exact real-side selection

若 success 只接受明确选择 real answer 的 A/B 侧，则：

- r1：`0/4`；
- r2：`4/4`；
- r3：`3/4`；
- 合计：`7/12`。

该差异来自 control rubric 的操作化方式。r1 在 4 个 controls 上统一使用 `INVALID + not_about_task`，而在 90 个 real cases 中的 `INVALID` 为 `0/90`。因此该现象更符合 control-handling mismatch，而非 r1 普遍无法完成 pairwise comparison。

正文使用 `11/12` 的 intended detection metric；附录同时披露 `7/12` exact-side sensitivity，以保留可审计性。

## 8. Task 2：标注行为与人类一致性

### 8.1 每位 annotator 的 real-case 行为

| Annotator | A | B | TIE | INVALID | Confidence | Difficulty | Mean time |
|---|---:|---:|---:|---:|---|---|---:|
| r1 | 26/90 | 38/90 | 26/90 | 0/90 | high 63，medium 27 | easy 45，medium 45 | 5.31 min |
| r2 | 25/90 | 36/90 | 29/90 | 0/90 | low 5，medium 85 | easy 2，medium 79，hard 9 | 4.06 min |
| r3 | 52/90 | 12/90 | 26/90 | 0/90 | high 74，medium 16 | easy 3，medium 68，hard 19 | 8.80 min |

270 条 real rows 合计：

- A：`103/270`；
- B：`86/270`；
- TIE：`81/270`；
- INVALID：`0/270`。

### 8.2 Case-level human majority

| Human majority label | Cases |
|---|---:|
| majority_A | `29/90` |
| majority_B | `31/90` |
| majority_TIE | `23/90` |
| no-consensus | `7/90` |

| IAA metric | Result |
|---|---:|
| 三人 unanimous | `25/90 = 27.8%` |
| 2-of-3 majority coverage | `83/90 = 92.2%` |
| no-consensus | `7/90 = 7.8%` |
| Pairwise agreement r1-r2 | `56/90 = 62.2%` |
| Pairwise agreement r1-r3 | `38/90 = 42.2%` |
| Pairwise agreement r2-r3 | `39/90 = 43.3%` |
| Krippendorff alpha | `0.238` |
| Alpha 95% case-bootstrap CI | `[0.136, 0.335]` |

人类 majority coverage 较高，但三人完全一致率和 alpha 较低。该组合说明多数 case 可以形成聚合偏好，同时 annotator-level judgment 存在明显异质性。

## 9. r3 A-side preference 与敏感性分析

### 9.1 Position-bias diagnosis

只看 real cases 中 A/B decisive votes，排除 TIE：

| Annotator | A | B | A proportion | Wilson 95% CI | Exact binomial p |
|---|---:|---:|---:|---|---:|
| r1 | 26 | 38 | `40.6%` | `[29.5%, 52.9%]` | `0.169` |
| r2 | 25 | 36 | `41.0%` | `[29.5%, 53.5%]` | `0.200` |
| r3 | 52 | 12 | `81.3%` | `[70.0%, 88.9%]` | `4.57e-7` |

r3 的 A-side preference 在两个 stratum 中均存在：

| Stratum | r3 A/B | A proportion | Exact binomial p |
|---|---:|---:|---:|
| stable | 34/7 | `82.9%` | `2.53e-5` |
| unstable | 18/5 | `78.3%` | `0.0106` |

Stable stratum 的 Gemini winner side 恰好平衡：A `30` cases、B `30` cases。r3 的 stable decisive agreement 显示明显的 side asymmetry：

| Gemini winner side | r3 agreement |
|---|---:|
| Gemini winner=A | `23/24 = 95.8%` |
| Gemini winner=B | `6/17 = 35.3%` |

对比：

| Annotator | Gemini A-side agreement | Gemini B-side agreement |
|---|---:|---:|
| r1 | `14/19` | `21/22` |
| r2 | `15/20` | `19/21` |
| r3 | `23/24` | `6/17` |

因此 r3 存在真实且显著的 A-position bias。主分析仍保留 r3，并通过敏感性分析评估其影响。

### 9.2 对 majority label 的影响

三人 majority 的最终 side 分布保持平衡：

- majority_A：`29`；
- majority_B：`31`。

在 r1/r2 不一致且最终形成 A/B majority 的 16 个 cases 中，r3 决定：

- A：`13`；
- B：`3`。

r3 因而影响部分 case-level majority，但没有使聚合 A/B 数量失衡。

### 9.3 r1+r2 consensus sensitivity

只保留 r1 与 r2 判断相同的 cases：

- 共识 cases：`56/90`；
- 其中 A：`16`、B：`28`、TIE：`12`；
- r1/r2 不一致：`34/90`。

Stable 且 r1/r2 形成 A/B 共识的 cases：

- agreement：`26/30 = 86.7%`。

r1+r2 consensus BT 点排序：

> `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2`

原三人 majority 的 stable agreement 为 `34/39 = 87.2%`，BT 点排序相同。因此主要 alignment 和 ranking 结论不依赖 r3 的 A-side preference。

## 10. Stable 与 unstable Gemini pairs

| Metric | Stable (`n=60`) | Unstable (`n=30`) |
|---|---:|---:|
| Human unanimous cases | `17/60 = 28.3%` | `8/30 = 26.7%` |
| Human alpha | `0.252` | `0.213` |
| Human majority A/B/TIE/no-consensus | 19/20/17/4 | 10/11/6/3 |
| Case mean confidence | 2.472 | 2.522 |
| Mean absolute five-dimension margin | 0.267 | 0.313 |
| TIE rows | `57/180 = 31.7%` | `24/90 = 26.7%` |
| different_tradeoff rows | `10/180 = 5.6%` | `9/90 = 10.0%` |
| Cases with any TIE/tradeoff signal | `36/60 = 60.0%` | `17/30 = 56.7%` |

Confidence 采用 `low=1`、`medium=2`、`high=3` 编码。

Stable minus unstable：

- confidence difference：`-0.050`，95% CI `[-0.139, 0.044]`；
- absolute dimension-margin difference：`-0.047`，95% CI `[-0.107, 0.014]`。

两项差异的 CI 均包含 0，方向也与“unstable 更难、分差更小”的预期相反。当前数据不支持将 Gemini order instability 普遍解释为人类困难或真实 ambiguity。

局部例外仍有诊断价值。例如 Sonnet–GPT 的人类 tie 很多，符合该相邻模型 pair 在全量 Gemini 中最接近的事实。该局部现象不足以推广到所有 unstable pairs。

## 11. Gemini-human calibration

### 11.1 Stable stratum 主结果

60 个 stable real cases 中：

- decisive human majority：`39/60 = 65.0%`；
- 与 Gemini stable winner 一致：`34/39 = 87.2%`；
- 95% case-bootstrap CI：`[76.9%, 97.4%]`；
- 若将 non-decisive cases 也放入总分母：`34/60 = 56.7%`。

按 model pair：

| Stable model pair | Decisive coverage | Agreement | TIE majority | No consensus |
|---|---:|---:|---:|---:|
| Sonnet–DeepSeek | `10/10` | `10/10` | 0 | 0 |
| Sonnet–GLM | `7/10` | `7/7` | 3 | 0 |
| Sonnet–GPT | `0/10` | — | 8 | 2 |
| DeepSeek–GLM | `6/10` | `2/6` | 3 | 1 |
| DeepSeek–GPT | `7/10` | `7/7` | 2 | 1 |
| GLM–GPT | `9/10` | `8/9` | 1 | 0 |
| Total | `39/60` | `34/39` | 17 | 4 |

按 human consensus strength：

| Subset | Agreement |
|---|---:|
| unanimous and decisive | `13/13 = 100%` |
| 2-of-3 decisive | `21/26 = 80.8%` |
| high-confidence decisive | `17/20 = 85.0%` |
| medium-confidence decisive | `17/19 = 89.5%` |

### 11.2 Sonnet–GPT 的 `0/0`

Sonnet–GPT 共 15 个 sampled cases：stable `10`、unstable `5`。

在 10 个 stable cases 中：

- human majority TIE：`8/10`；
- no-consensus：`2/10`；
- A/B decisive majority：`0/10`；
- 30 条 raw votes：TIE `20`、A `6`、B `4`。

因此 stable agreement table 中不存在 eligible denominator，应显示为 `—`，而非把 `0/0` 解释为缺少数据或 0% agreement。

将全部 15 个 Sonnet–GPT human cases用于 BT：

- GPT wins：`1`；
- Sonnet wins：`2`；
- TIE：`9`；
- no-consensus：`3`。

这说明人类将 GPT 与 Sonnet 视为非常接近的相邻模型。全量 Gemini 中该 pair 的 order stability 也是最低的，约为 `128/200 = 64%`。

### 11.3 Unstable stratum 诊断

30 个 unstable cases：

- majority_A：`10`；
- majority_B：`11`；
- majority_TIE：`6`；
- no-consensus：`3`。

66 条 decisive human votes 与 Gemini 两个方向的接近程度：

- forward verdict：`40/66`；
- reverse verdict：`26/66`。

在 21 个具有 decisive human majority 的 unstable cases 中：

- 接近 forward：`11/21`；
- 接近 reverse：`10/21`。

人类 majority 在 case level 上没有明显偏向 Gemini 的某一方向。任何一侧都不应被事后指定为 unstable pair 的 Gemini gold label。

### 11.4 Folded sensitivity

若 stable 使用 Gemini winner、unstable 折成 TIE，与 human majority 做 exact agreement：

- `40/83 = 48.2%`；
- 95% case-bootstrap CI：`[37.4%, 59.0%]`。

该结果作为 folded sensitivity，不能替代 stable-stratum 的 `34/39` 主 agreement。

## 12. 五个质量维度

以下统计只纳入 human majority 为 A/B 且无 INVALID 的 `60` 个 real cases。每个 answer 的分数先在 case 内对三位 annotator 取 median，再按 human winner 方向计算 winner–loser margin。

| Dimension | r1 A/B mean | r2 A/B mean | r3 A/B mean | Winner–loser mean margin | 95% bootstrap CI |
|---|---|---|---|---:|---|
| grounding | 2.98 / 2.96 | 2.98 / 2.99 | 2.99 / 2.82 | 0.00 | `[0.000, 0.000]` |
| hypothesis specificity | 3.00 / 3.00 | 2.64 / 2.76 | 2.92 / 2.63 | 0.10 | `[0.033, 0.183]` |
| minimality/feasibility | 2.46 / 2.58 | 2.76 / 2.92 | 2.90 / 2.66 | 0.53 | `[0.383, 0.683]` |
| decisive metric | 2.68 / 2.73 | 2.72 / 2.69 | 2.87 / 2.49 | 0.57 | `[0.433, 0.683]` |
| falsifiability | 3.00 / 3.00 | 2.98 / 2.97 | 2.98 / 2.78 | 0.00 | `[0.000, 0.000]` |

人类 winner 更明显地体现在 minimality/feasibility 与 decisive metric 上。Grounding 和 falsifiability 的 case-median winner–loser margin 为 0。

Falsifiability 的结果边界：

- A/B falsifiability 原始均值较高，存在 ceiling effect；
- winner–loser median margin 为 0；
- `no_real_falsification` primary weakness 仅 `1/60`；
- primary 或 secondary 任一出现为 `3/60`。

因此当前人类结果不支持“falsifiability 是最有区分力的维度”。它仍是 benchmark schema 的核心设计目标，但这一设计动机与当前人类区分效度应分开表述。

## 13. Weakness taxonomy

主 taxonomy 仅纳入 `60` 个 human-majority A/B cases，并先做 case-level 聚合。

### 13.1 Primary weakness

| Primary weakness | Cases | Proportion |
|---|---:|---:|
| generic hypothesis | `21/60` | 35.0% |
| missing baseline/control | `14/60` | 23.3% |
| weak decisive metric | `12/60` | 20.0% |
| overbroad/infeasible | `12/60` | 20.0% |
| no real falsification | `1/60` | 1.7% |

### 13.2 Primary 或 secondary 任一出现

| Weakness | Cases | Proportion |
|---|---:|---:|
| weak decisive metric | `52/60` | 86.7% |
| overbroad/infeasible | `42/60` | 70.0% |
| generic hypothesis | `37/60` | 61.7% |
| missing baseline/control | `26/60` | 43.3% |
| weak grounding | `21/60` | 35.0% |
| no real falsification | `3/60` | 5.0% |
| other | `1/60` | 1.7% |

人类最常识别出的失败模式集中在实验可执行性、decisive metric、hypothesis specificity 和 baseline/control。该结果支持 Lit2Test 作为诊断 benchmark 的定位，同时不支持把 falsifiability weakness 作为主要 empirical headline。

## 14. Human-derived model ranking

### 14.1 BT 输入

- 90 个 real cases；
- case-level human majority preference edge；
- no-consensus `7` cases 排除；
- TIE 使用 `0.5/0.5`；
- 主 BT edges：`83`；
- controls 不进入。

### 14.2 Human head-to-head

| Pair | First model wins | Second model wins | Ties | n |
|---|---:|---:|---:|---:|
| GPT 5.2 vs Sonnet | 1 | 2 | 9 | 12 |
| GPT 5.2 vs GLM-5 | 14 | 0 | 1 | 15 |
| GPT 5.2 vs DeepSeek | 12 | 0 | 2 | 14 |
| Sonnet vs GLM-5 | 11 | 0 | 3 | 14 |
| Sonnet vs DeepSeek | 11 | 1 | 2 | 14 |
| GLM-5 vs DeepSeek | 5 | 3 | 6 | 14 |

Human BT 点估计：

> `GPT 5.2 > Claude-Sonnet-4.6-hq > GLM-5 > DeepSeek-V3.2`

与 Gemini full ranking 的点估计相关性：

- Kendall tau：`1.0`；
- Spearman rho：`1.0`。

### 14.3 Exact 与 relaxed bootstrap stability

以 Gemini full ranking

> `GPT > Sonnet > GLM > DeepSeek`

为参考，定义 Kendall inversion distance：

- distance 0：四模型全序完全一致；
- distance 1：六个 pairwise order relations 中仅一个反转；
- distance 2：两个反转。

10,000 次 case bootstrap：

| Bootstrap ranking | Count | Proportion | Inversions vs Gemini |
|---|---:|---:|---:|
| GPT > Sonnet > GLM > DeepSeek | 4,088 | 40.88% | 0 |
| GPT > Sonnet > DeepSeek > GLM | 2,660 | 26.60% | 1 |
| Sonnet > GPT > GLM > DeepSeek | 2,082 | 20.82% | 1 |
| Sonnet > GPT > DeepSeek > GLM | 1,170 | 11.70% | 2 |

汇总：

- exact full order：`4,088/10,000 = 40.9%`；
- at most one inversion：`8,830/10,000 = 88.3%`；
- at most two inversions：`10,000/10,000 = 100%`；
- top-2 set `{GPT, Sonnet}`：`10,000/10,000` 保持；
- bottom-2 set `{GLM, DeepSeek}`：`10,000/10,000` 保持。

Bootstrap 不确定性只发生在两个相邻 pairs：GPT/Sonnet 和 GLM/DeepSeek。没有任何 bootstrap 将 GPT 或 Sonnet 排在 GLM 或 DeepSeek 之后。

因此 exact-order `40.9%` 不应单独解释为 human ranking failure。更合适的结论是：人类样本稳定恢复宏观 tier structure，精确的相邻模型顺序仍不稳定。

推荐论文措辞：

> The human BT point estimate exactly recovered the full Gemini ordering. Across 10,000 case-level bootstrap samples, 40.9% recovered the exact four-model order, while 88.3% differed by at most one pairwise inversion. Every bootstrap sample preserved the separation between the top pair (GPT and Sonnet) and the bottom pair (GLM and DeepSeek).

## 15. Case-level disagreement audit

### 15.1 三位人类完全不同

- `t2_formal_024`
- `t2_formal_064`
- `t2_formal_073`
- `t2_formal_075`
- `t2_formal_077`
- `t2_formal_085`
- `t2_formal_092`

### 15.2 Stable human majority 与 Gemini 不一致

- `t2_formal_016`
- `t2_formal_040`
- `t2_formal_042`
- `t2_formal_055`
- `t2_formal_089`

### 15.3 Gemini unstable 但人类 unanimous

- `t2_formal_003`
- `t2_formal_008`
- `t2_formal_020`
- `t2_formal_028`
- `t2_formal_049`
- `t2_formal_076`
- `t2_formal_079`
- `t2_formal_080`

### 15.4 Dimension extremes

最大五维平均绝对差距：

- `t2_formal_010`
- `t2_formal_017`
- `t2_formal_006`

最小五维平均绝对差距：

- `t2_formal_062`
- `t2_formal_082`
- `t2_formal_090`

### 15.5 Falsifiability 与 tradeoff cases

`no_real_falsification` 出现：

- `t2_formal_032`
- `t2_formal_041`
- `t2_formal_044`

含 `different_tradeoff` 或 `insufficient_context` 的 real cases：`18/90`。

Real INVALID cases：`0/90` per annotator。

代表性案例表：

| Case | Stratum | Human labels | Gemini | Observed issue |
|---|---|---|---|---|
| t2_formal_016 | stable | TIE/A/A | B | human tie + A；差距较小 |
| t2_formal_040 | stable | A/A/TIE | B | both_good |
| t2_formal_042 | stable | B/B/A | A | 人类多数与 Gemini 相反 |
| t2_formal_003 | unstable | B/B/B | B/A | Gemini 翻转，人类 unanimous |
| t2_formal_008 | unstable | B/B/B | A/B | Gemini 翻转，人类 unanimous |
| t2_formal_020 | unstable | A/A/A | A/B | Gemini 翻转，人类 unanimous |
| t2_formal_024 | unstable | B/TIE/A | A/B | 三人完全不同 |
| t2_formal_064 | unstable | TIE/B/A | A/B | different_tradeoff |
| t2_formal_073 | stable | B/TIE/A | A | 三人完全不同 |

## 16. Claim matrix

| Claim | Evidence | Status | Safe paper wording |
|---|---|---|---|
| Sampled neighborhoods are usable | majority keep `16/20`；relatedness/grounding 高；Task 1 alpha 较低 | partial | “Annotator majorities retained 16 of 20 stratified neighborhoods, although agreement on exact quality labels was limited.” |
| Humans can detect naive controls | intended detection `11/12` | supported as sanity check | “Hidden naive controls were detected in 11 of 12 judgments.” |
| Gemini stable judgments align with humans | `34/39 = 87.2%` on decisive stable cases | supported on a stratified subset | “Human preferences substantially align with Gemini on stable, decisive comparisons.” |
| Order instability reflects ambiguity | unstable confidence/margin 没有显著下降 | unsupported globally | 不写一般性因果解释；仅作 case-level diagnosis |
| Human ranking matches Gemini | point estimate exact；≤1 inversion `88.3%`；tier `100%` | supported at aggregate/tier level | “Human preferences recover the Gemini point ordering and a robust tier structure.” |
| Exact adjacent-model ranking is stable | exact full order `40.9%`；相邻 pair 会互换 | partial | “Uncertainty is concentrated in adjacent model pairs.” |
| Falsifiability is the main discriminative dimension | winner–loser margin `0`；primary weakness `1/60` | unsupported | 只报告维度分布，不作 headline |
| Human labels are position-unbiased | r3 A-side `52/64` | unsupported | 附录披露 position bias 与 r1+r2 sensitivity |
| The full benchmark is human-validated | Task 1 仅 20/200；Task 2 仅 90/1200 canonical pairs | unsupported | “Human calibration on a stratified subset” |

## 17. Paper-facing summary

### 17.1 中文结论

我们在 20 个分层抽样 neighborhood 和 90 个 real pair 上进行了人类校准，并加入 4 个 hidden real-vs-naive controls。标注者在 `11/12` 个 control judgments 中检测出 naive answer。对 60 个 Gemini 顺序稳定的 pairs，其中 39 个形成 decisive human majority，34 个与 Gemini 一致。Human BT 点估计恢复了与 Gemini 全量评测一致的模型排序；`88.3%` 的 case bootstrap 排名与该排序相差不超过一个逆序，且所有 bootstrap 均保持 GPT/Sonnet 与 GLM/DeepSeek 的上下层划分。人类一致性较低，stable/unstable 的总体差异也不明显。因此，人评支持核心数据与 judge workflow 的聚合可靠性，同时限制了细粒度机制解释和全面人类验证的表述。

### 17.2 Experiments 英文草稿

> We conducted human calibration on 20 stratified neighborhood-quality cases and 90 real pairwise comparisons, together with four hidden real-vs-naive controls. Annotators detected the naive answer in 11 of 12 control judgments. Among 60 order-stable comparisons, 39 yielded a decisive human majority, of which 34 matched the Gemini verdict (87.2%, case-level bootstrap 95% CI: 76.9–97.4%). The human Bradley–Terry point estimate recovered the full Gemini ordering. Across 10,000 case-level bootstrap samples, 88.3% differed from that ordering by at most one pairwise inversion, and every sample preserved the top-pair versus bottom-pair tier structure. A sensitivity analysis based only on r1–r2 consensus retained both the stable-pair agreement rate (26/30) and the model ordering.

### 17.3 Honest limitations 英文草稿

> The human study covers a stratified subset rather than the full benchmark, and inter-annotator agreement was modest (Krippendorff’s alpha = 0.238 for real-pair winners). One annotator exhibited a strong A-side preference, although excluding that annotator in a consensus sensitivity did not change the principal alignment or ranking conclusions. Order-unstable Gemini comparisons were not consistently associated with lower human confidence or smaller dimension margins. The results therefore support aggregate calibration of the data and judge workflow, while leaving uncertainty in fine-grained dimensions, order-sensitive comparisons, and adjacent-model rankings.

## 18. 正文与附录的建议分工

### 正文

正文建议只保留四项结果：

1. Sampled neighborhood majority keep：`16/20`；
2. Hidden-control detection：`11/12`；
3. Stable Gemini-human agreement：`34/39 = 87.2%`；
4. Human BT point ordering + at-most-one-inversion stability：exact `40.9%`，relaxed `88.3%`，tier stability `100%`。

正文用一句话说明 r1+r2 sensitivity 不改变结论。避免展开单个 annotator 或单个 case 的细节。

### 附录

附录建议完整报告：

- Data integrity 与 SHA-256；
- `11/12` detection 与 `7/12` exact-side 两种 control operationalization；
- Task 1/Task 2 IAA；
- r3 A-side bias；
- r1+r2 consensus sensitivity；
- stable/unstable comparison；
- five-dimension margins；
- weakness taxonomy；
- Sonnet–GPT `0/10` decisive coverage 的解释；
- exact 与 relaxed BT bootstrap；
- disagreement case IDs。

## 19. 复现信息与文件指纹

### 19.1 输入文件 SHA-256

| Artifact | SHA-256 |
|---|---|
| r1 raw Task 1 | `2c03e734f93e319a28b18ff366ef2dfd77ee98ed370e2b0d29956dcb7374024a` |
| r1 repaired Task 1 | `acb50a10b84b3b9d68824065dfa57cb3bfcd47dd385026638a5150071998f7d2` |
| r1 raw Task 2 | `8237957d88591851662ffd0a0da63df8ff7c057f2a7f1d24ef789c22c9128c81` |
| r1 repaired Task 2 | `ef4dd770f54b15a2138c684c7f1fe30568e4582d54745ae6a33878d53d66c849` |
| r2 zip | `9cc5b1f1248c65abcac76245ff0353613cb88055f07412844e9e1fb031246b62` |
| r2 Task 1 CSV | `c9516110151195aab068f4027dcde0b0298877af821f146f70b60f399c85b0f0` |
| r2 Task 2 CSV | `26f9b628a18b0f824507b15683cdd18426c5d41f74f7d5218b67e7f3481a358a` |
| r3 tar | `ce511516040d34915f076fef18e43dc572ffa19a7abe7740f23f65ef4f5e18d7` |
| r3 Task 1 CSV | `a52ec537e2a89fa7e88da81b122000cfd30a865daeb27b0fa61573977b71d9fb` |
| r3 Task 2 CSV | `f98a24afbc2b298eb487348606d5f10019242fe4f5f12c176620748b4b1c80f9` |
| formal package manifest | `62c7db43eddec27bc717853d455883585a350a1ac38c032b01512dbda256fed9` |

### 19.2 Source-of-truth paths

- `outputs/lit2test_human_acceptance_internal/package_manifest.json`
- `outputs/lit2test_human_acceptance_internal/formal_cases.jsonl`
- `outputs/lit2test_human_acceptance_internal/field_schema.json`
- `outputs/lit2test_human_acceptance_formal_package/`
- `human_cali/`
- `human_cali/repaired/r1/`

---

# 最终结论

人类反馈总体支持 Lit2Test 的核心主张：抽样输入数据具有可用性，hidden controls 能够被识别，Gemini stable judgments 与人类偏好高度一致，人类排序也恢复了相同的点估计顺序和稳定的模型 tier structure。

人类反馈同时限定了论文的证据边界：annotator-level agreement 较低，r3 存在显著位置偏差，unstable pairs 没有表现出普遍更高的人类困难，falsifiability 也没有成为最有区分力的维度。这些结果要求论文将 validity claim 保持在“aggregate workflow calibration”层面，并将细粒度机制解释、相邻模型排序和全面人类验证留作限制或后续工作。
