# Lit2Test Dimension-Decomposed Gemini Audit

## Executive Verdict

1. Completion/validity: 188/188 valid; 90 real cases and 4 controls each have both orders.
2. Structured overall vs. original holistic: 152/180 (0.844; 95% CI 0.789–0.894).
3. Score-sum vs. original holistic: 145/180 (0.806; 95% CI 0.744–0.861).
4. Structured overall vs. score-sum: 170/180 (0.944; 95% CI 0.911–0.972).
5. Structured overall order robustness: 65/90 (0.722; 95% CI 0.633–0.811).
6. Stable/unstable holistic agreement: stable 110/120 (0.917; 95% CI 0.858–0.967); unstable 42/60 (0.700; 95% CI 0.583–0.800).
7. Controls (structured overall selects real): 8/8 (1.000; 95% CI 1.000–1.000).
8. Human alignment: out of scope; handled in a separate session, and no human-calibration files were read.

This audit measures internal workflow consistency and rubric adherence. It does not establish objective scientific quality or reveal Gemini's latent reasoning process.

## Data and Completion Integrity

| Item | Result |
|---|---:|
| Audit tasks | 188/188 |
| Valid judgments | 188/188 |
| Real ordered judgments | 180/180 |
| Control ordered judgments | 8/8 |
| Real cases with both orders | 90/90 |
| Controls with both orders | 4/4 |
| Orientation mismatches | 0/94 |
| Duplicate final judgments | 0/188 |
| Sampling stability strata | {'order-stable': 60, 'order-unstable': 30} |
| Corrected stability strata | {'order-stable': 60, 'order-unstable': 30} |
| Cases whose stability label changed after reverse correction | 0/90 |
| Raw API attempts | 212 |
| Failed attempts retried | 24 |
| Failure reasons | {'http_429': 1, 'model_output_json_error': 4, 'schema_validation_error': 19} |
| Outer-fence normalizations | {'single_outer_markdown_json_fence_removed': 29} |
| Maximum concurrent requests | 2 |

## Winner Definitions vs. Original Holistic

| Winner definition | Exact agreement | Decisive-only agreement | Decisive coverage | Tie rate | κ |
|---|---:|---:|---:|---:|---:|
| structured_overall | 152/180 (0.844; 95% CI 0.789–0.894) | 152/176 (0.864; 95% CI 0.810–0.914) | 176/180 (0.978; 95% CI 0.956–0.994) | 4/180 (0.022; 95% CI 0.006–0.044) | 0.671 |
| score_sum | 145/180 (0.806; 95% CI 0.744–0.861) | 145/166 (0.873; 95% CI 0.818–0.923) | 166/180 (0.922; 95% CI 0.878–0.961) | 14/180 (0.078; 95% CI 0.039–0.122) | 0.609 |
| dimension_majority | 145/180 (0.806; 95% CI 0.744–0.861) | 145/166 (0.873; 95% CI 0.817–0.924) | 166/180 (0.922; 95% CI 0.878–0.961) | 14/180 (0.078; 95% CI 0.039–0.122) | 0.608 |

## Agreement by Corrected Holistic Order-Stability Stratum

| Stratum | Structured overall | Score-sum | Dimension-majority |
|---|---:|---:|---:|
| order-stable | 110/120 (0.917; 95% CI 0.858–0.967) | 105/120 (0.875; 95% CI 0.808–0.933) | 104/120 (0.867; 95% CI 0.800–0.925) |
| order-unstable | 42/60 (0.700; 95% CI 0.583–0.800) | 40/60 (0.667; 95% CI 0.567–0.767) | 41/60 (0.683; 95% CI 0.583–0.783) |

## Agreement by Presentation Order

| Order | Structured overall | Score-sum | Dimension-majority |
|---|---:|---:|---:|
| original | 76/90 (0.844; 95% CI 0.767–0.911) | 73/90 (0.811; 95% CI 0.722–0.889) | 74/90 (0.822; 95% CI 0.744–0.900) |
| reverse | 76/90 (0.844; 95% CI 0.767–0.911) | 72/90 (0.800; 95% CI 0.711–0.878) | 71/90 (0.789; 95% CI 0.700–0.867) |

## Agreement by Model Pair

| Model pair | Structured overall | Score-sum | Dimension-majority |
|---|---:|---:|---:|
| Claude-Sonnet-4.6-hq vs DeepSeek-V3.2 | 25/30 (0.833; 95% CI 0.700–0.933) | 23/30 (0.767; 95% CI 0.633–0.900) | 23/30 (0.767; 95% CI 0.633–0.900) |
| Claude-Sonnet-4.6-hq vs GLM-5 | 25/30 (0.833; 95% CI 0.700–0.933) | 24/30 (0.800; 95% CI 0.667–0.933) | 24/30 (0.800; 95% CI 0.667–0.900) |
| Claude-Sonnet-4.6-hq vs GPT 5.2 | 24/30 (0.800; 95% CI 0.667–0.933) | 22/30 (0.733; 95% CI 0.600–0.867) | 22/30 (0.733; 95% CI 0.600–0.867) |
| DeepSeek-V3.2 vs GLM-5 | 24/30 (0.800; 95% CI 0.600–0.967) | 23/30 (0.767; 95% CI 0.567–0.933) | 23/30 (0.767; 95% CI 0.567–0.933) |
| DeepSeek-V3.2 vs GPT 5.2 | 28/30 (0.933; 95% CI 0.833–1.000) | 28/30 (0.933; 95% CI 0.833–1.000) | 28/30 (0.933; 95% CI 0.833–1.000) |
| GLM-5 vs GPT 5.2 | 26/30 (0.867; 95% CI 0.700–1.000) | 25/30 (0.833; 95% CI 0.667–0.967) | 25/30 (0.833; 95% CI 0.667–0.967) |

## Internal Structured Consistency

| Comparison | Exact agreement | Decisive-only agreement |
|---|---:|---:|
| structured_overall_vs_score_sum | 170/180 (0.944; 95% CI 0.911–0.972) | 166/166 (1.000; 95% CI 1.000–1.000) |
| structured_overall_vs_dimension_majority | 170/180 (0.944; 95% CI 0.911–0.972) | 166/166 (1.000; 95% CI 1.000–1.000) |
| score_sum_vs_dimension_majority | 178/180 (0.989; 95% CI 0.972–1.000) | 165/165 (1.000; 95% CI 1.000–1.000) |

## Per-Dimension Order Robustness

| Dimension | Score exact | Score MAE | Winner consistency |
|---|---:|---:|---:|
| grounding | 154/180 (0.856; 95% CI 0.806–0.906) | 0.144 (n=180; 95% CI 0.094–0.194) | 66/90 (0.733; 95% CI 0.644–0.822) |
| hypothesis_specificity | 167/180 (0.928; 95% CI 0.889–0.961) | 0.078 (n=180; 95% CI 0.039–0.122) | 78/90 (0.867; 95% CI 0.789–0.933) |
| minimality_feasibility | 125/180 (0.694; 95% CI 0.617–0.767) | 0.317 (n=180; 95% CI 0.239–0.400) | 57/90 (0.633; 95% CI 0.533–0.733) |
| decisive_metric | 142/180 (0.789; 95% CI 0.739–0.839) | 0.228 (n=180; 95% CI 0.172–0.289) | 52/90 (0.578; 95% CI 0.478–0.678) |
| falsifiability | 154/180 (0.856; 95% CI 0.806–0.900) | 0.156 (n=180; 95% CI 0.106–0.211) | 66/90 (0.733; 95% CI 0.644–0.822) |

| Overall order check | Consistency |
|---|---:|
| Structured overall model winner | 65/90 (0.722; 95% CI 0.633–0.811) |
| Score-sum model winner | 59/90 (0.656; 95% CI 0.556–0.756) |
| Dimension-majority model winner | 58/90 (0.644; 95% CI 0.544–0.744) |
| Confidence label | 88/90 (0.978; 95% CI 0.944–1.000) |

## Per-Dimension Margins

| Dimension | Absolute margin | Holistic-winner signed margin | Non-tie verdict | Sole non-tie dimension |
|---|---:|---:|---:|---:|
| grounding | 0.233 (n=180; 95% CI 0.161–0.311) | 0.178 (n=180; 95% CI 0.105–0.261) | 41/180 (0.228; 95% CI 0.161–0.300) | 12/180 (0.067; 95% CI 0.028–0.111) |
| hypothesis_specificity | 0.144 (n=180; 95% CI 0.083–0.211) | 0.133 (n=180; 95% CI 0.072–0.200) | 24/180 (0.133; 95% CI 0.078–0.194) | 3/180 (0.017; 95% CI 0.000–0.044) |
| minimality_feasibility | 0.817 (n=180; 95% CI 0.722–0.911) | 0.606 (n=180; 95% CI 0.478–0.728) | 133/180 (0.739; 95% CI 0.661–0.811) | 64/180 (0.356; 95% CI 0.278–0.433) |
| decisive_metric | 0.339 (n=180; 95% CI 0.267–0.411) | 0.261 (n=180; 95% CI 0.183–0.339) | 58/180 (0.322; 95% CI 0.256–0.394) | 8/180 (0.044; 95% CI 0.011–0.083) |
| falsifiability | 0.222 (n=180; 95% CI 0.144–0.311) | 0.167 (n=180; 95% CI 0.100–0.244) | 33/180 (0.183; 95% CI 0.122–0.244) | 1/180 (0.006; 95% CI 0.000–0.017) |

| Dimension | Stable absolute margin | Unstable absolute margin |
|---|---:|---:|
| grounding | 0.275 (n=120; 95% CI 0.183–0.375) | 0.150 (n=60; 95% CI 0.067–0.250) |
| hypothesis_specificity | 0.167 (n=120; 95% CI 0.083–0.250) | 0.100 (n=60; 95% CI 0.017–0.200) |
| minimality_feasibility | 0.858 (n=120; 95% CI 0.733–0.975) | 0.733 (n=60; 95% CI 0.583–0.883) |
| decisive_metric | 0.325 (n=120; 95% CI 0.242–0.417) | 0.367 (n=60; 95% CI 0.233–0.500) |
| falsifiability | 0.192 (n=120; 95% CI 0.100–0.300) | 0.283 (n=60; 95% CI 0.133–0.450) |

| Dimension | Low-confidence margin | Medium-confidence margin | High-confidence margin |
|---|---:|---:|---:|
| grounding | NA | 0.500 (n=2; 95% CI 0.000–1.000) | 0.230 (n=178; 95% CI 0.161–0.303) |
| hypothesis_specificity | NA | 0.000 (n=2; 95% CI 0.000–0.000) | 0.146 (n=178; 95% CI 0.084–0.218) |
| minimality_feasibility | NA | 0.000 (n=2; 95% CI 0.000–0.000) | 0.826 (n=178; 95% CI 0.729–0.921) |
| decisive_metric | NA | 0.000 (n=2; 95% CI 0.000–0.000) | 0.343 (n=178; 95% CI 0.270–0.418) |
| falsifiability | NA | 0.000 (n=2; 95% CI 0.000–0.000) | 0.225 (n=178; 95% CI 0.145–0.315) |

## Controls

| Method | Real answer selected |
|---|---:|
| structured_overall | 8/8 (1.000; 95% CI 1.000–1.000) |
| score_sum | 8/8 (1.000; 95% CI 1.000–1.000) |
| dimension_majority | 8/8 (1.000; 95% CI 1.000–1.000) |

| Dimension | Mean real-minus-naive score margin |
|---|---:|
| grounding | 2.000 (n=8; 95% CI 2.000–2.000) |
| hypothesis_specificity | 2.000 (n=8; 95% CI 2.000–2.000) |
| minimality_feasibility | 2.000 (n=8; 95% CI 2.000–2.000) |
| decisive_metric | 2.000 (n=8; 95% CI 2.000–2.000) |
| falsifiability | 2.000 (n=8; 95% CI 2.000–2.000) |

| Control case | Structured O/R | Score-sum O/R | Dimension-majority O/R |
|---|---|---|---|
| t2_formal_022 | True/True | True/True | True/True |
| t2_formal_029 | True/True | True/True | True/True |
| t2_formal_046 | True/True | True/True | True/True |
| t2_formal_071 | True/True | True/True | True/True |

## Gemini-Human Dimension Alignment

`out_of_scope / handled_in_separate_session`: this analyzer intentionally does not discover or read human-calibration artifacts.

## Case Audit

Large score change is preregistered here as any aligned model-dimension score changing by at least 2 points, or total aligned absolute change across ten scores reaching at least 5.

| Case | Stability | Holistic O/R | Structured O/R | Score-sum O/R | Dimension margins | Issue |
|---|---|---|---|---|---|---|
| t2_formal_003 | order-unstable→order-unstable | B/B | A/A | A/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_005 | order-stable→order-stable | A/B | A/B | A/tie | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:1/0; decisive_metric:1/0; falsifiability:0/0 | structured_vs_score_sum |
| t2_formal_008 | order-unstable→order-unstable | A/A | A/B | A/B | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/-1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_009 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/1; hypothesis_specificity:-1/0; minimality_feasibility:0/1; decisive_metric:0/0; falsifiability:-1/0 | falsifiability_order_flip |
| t2_formal_011 | order-unstable→order-unstable | A/A | A/B | A/B | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:0/-1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_012 | order-stable→order-stable | A/B | A/tie | A/tie | grounding:1/0; hypothesis_specificity:1/0; minimality_feasibility:1/0; decisive_metric:1/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_018 | order-stable→order-stable | A/B | A/B | A/B | grounding:0/0; hypothesis_specificity:1/-1; minimality_feasibility:1/-1; decisive_metric:1/-1; falsifiability:1/0 | falsifiability_order_flip |
| t2_formal_019 | order-unstable→order-unstable | A/A | A/A | A/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-1/2; decisive_metric:1/0; falsifiability:1/0 | falsifiability_order_flip |
| t2_formal_020 | order-unstable→order-unstable | A/A | A/A | A/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:2/1; decisive_metric:2/0; falsifiability:1/0 | large_order_score_change, falsifiability_order_flip |
| t2_formal_024 | order-unstable→order-unstable | A/A | A/A | A/tie | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/0; decisive_metric:1/0; falsifiability:0/0 | structured_vs_score_sum |
| t2_formal_025 | order-stable→order-stable | B/A | B/A | tie/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/1; decisive_metric:0/0; falsifiability:0/0 | structured_vs_score_sum |
| t2_formal_026 | order-stable→order-stable | B/A | A/A | A/A | grounding:0/1; hypothesis_specificity:0/0; minimality_feasibility:1/1; decisive_metric:0/0; falsifiability:0/1 | holistic_vs_structured, large_order_score_change, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_028 | order-unstable→order-unstable | A/A | A/A | tie/A | grounding:0/1; hypothesis_specificity:0/0; minimality_feasibility:1/0; decisive_metric:1/0; falsifiability:-2/2 | structured_vs_score_sum |
| t2_formal_031 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:-1/0; hypothesis_specificity:0/0; minimality_feasibility:-1/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_034 | order-stable→order-stable | A/B | A/B | A/tie | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/0; decisive_metric:0/0; falsifiability:0/0 | structured_vs_score_sum |
| t2_formal_035 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/0; decisive_metric:-1/1; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_037 | order-stable→order-stable | A/B | A/B | A/B | grounding:1/-1; hypothesis_specificity:0/0; minimality_feasibility:1/-1; decisive_metric:1/0; falsifiability:1/0 | falsifiability_order_flip |
| t2_formal_038 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/1; hypothesis_specificity:-1/1; minimality_feasibility:-1/1; decisive_metric:-1/1; falsifiability:0/1 | falsifiability_order_flip |
| t2_formal_043 | order-unstable→order-unstable | A/A | A/B | A/B | grounding:0/0; hypothesis_specificity:1/-1; minimality_feasibility:1/1; decisive_metric:1/-1; falsifiability:1/0 | holistic_vs_structured, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_045 | order-stable→order-stable | A/B | A/A | A/A | grounding:0/0; hypothesis_specificity:1/0; minimality_feasibility:0/0; decisive_metric:1/0; falsifiability:1/1 | holistic_vs_structured, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_047 | order-stable→order-stable | A/B | A/B | A/B | grounding:1/-1; hypothesis_specificity:1/0; minimality_feasibility:1/-1; decisive_metric:0/0; falsifiability:2/0 | large_order_score_change, falsifiability_order_flip |
| t2_formal_048 | order-stable→order-stable | A/B | A/B | A/B | grounding:2/-1; hypothesis_specificity:1/0; minimality_feasibility:2/-2; decisive_metric:1/0; falsifiability:1/0 | falsifiability_order_flip |
| t2_formal_049 | order-unstable→order-unstable | A/A | A/B | A/B | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/-1; decisive_metric:1/-1; falsifiability:1/-1 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_050 | order-unstable→order-unstable | A/A | A/A | A/A | grounding:0/0; hypothesis_specificity:0/2; minimality_feasibility:1/0; decisive_metric:0/0; falsifiability:0/2 | large_order_score_change, falsifiability_order_flip |
| t2_formal_053 | order-unstable→order-unstable | A/A | tie/A | tie/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/0; decisive_metric:0/1; falsifiability:0/1 | holistic_vs_structured, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_054 | order-stable→order-stable | A/B | A/tie | A/tie | grounding:0/0; hypothesis_specificity:1/0; minimality_feasibility:0/0; decisive_metric:0/0; falsifiability:1/0 | holistic_vs_structured, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_055 | order-stable→order-stable | A/B | A/A | A/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_057 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-1/1; decisive_metric:-1/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_060 | order-unstable→order-unstable | A/A | A/A | A/A | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:0/0; decisive_metric:0/1; falsifiability:1/0 | falsifiability_order_flip |
| t2_formal_061 | order-unstable→order-unstable | A/A | B/A | tie/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, structured_vs_score_sum, high_confidence_holistic_disagreement |
| t2_formal_062 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-2/1; decisive_metric:0/2; falsifiability:0/0 | large_order_score_change |
| t2_formal_063 | order-unstable→order-unstable | A/A | B/tie | tie/tie | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/0; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, structured_vs_score_sum, high_confidence_holistic_disagreement |
| t2_formal_065 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-1/1; decisive_metric:0/1; falsifiability:0/1 | falsifiability_order_flip |
| t2_formal_070 | order-stable→order-stable | B/A | A/A | A/A | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:1/1; decisive_metric:0/1; falsifiability:0/1 | holistic_vs_structured, large_order_score_change, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_072 | order-stable→order-stable | A/B | A/B | A/tie | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/0; decisive_metric:0/0; falsifiability:1/0 | structured_vs_score_sum, falsifiability_order_flip |
| t2_formal_074 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/1; decisive_metric:-1/1; falsifiability:-1/0 | falsifiability_order_flip |
| t2_formal_075 | order-stable→order-stable | A/B | A/B | tie/B | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:0/-1; decisive_metric:0/0; falsifiability:0/0 | structured_vs_score_sum |
| t2_formal_077 | order-stable→order-stable | B/A | A/B | A/B | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:1/-2; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_078 | order-stable→order-stable | B/A | A/A | A/A | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:0/0; decisive_metric:0/1; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_080 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-1/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_082 | order-stable→order-stable | A/B | A/A | A/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |
| t2_formal_083 | order-unstable→order-unstable | A/A | A/A | A/A | grounding:1/1; hypothesis_specificity:0/0; minimality_feasibility:2/0; decisive_metric:1/0; falsifiability:1/0 | large_order_score_change, falsifiability_order_flip |
| t2_formal_084 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:-1/1; decisive_metric:0/1; falsifiability:0/1 | holistic_vs_structured, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_085 | order-stable→order-stable | B/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/1; minimality_feasibility:-1/1; decisive_metric:-1/1; falsifiability:0/1 | falsifiability_order_flip |
| t2_formal_086 | order-unstable→order-unstable | A/A | B/A | B/A | grounding:0/0; hypothesis_specificity:0/1; minimality_feasibility:-1/0; decisive_metric:-2/0; falsifiability:0/1 | holistic_vs_structured, large_order_score_change, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_087 | order-unstable→order-unstable | A/A | A/B | A/tie | grounding:1/0; hypothesis_specificity:0/0; minimality_feasibility:0/1; decisive_metric:0/0; falsifiability:0/-1 | holistic_vs_structured, structured_vs_score_sum, high_confidence_holistic_disagreement, falsifiability_order_flip |
| t2_formal_092 | order-unstable→order-unstable | A/A | A/B | A/B | grounding:0/0; hypothesis_specificity:0/0; minimality_feasibility:1/-1; decisive_metric:0/0; falsifiability:0/0 | holistic_vs_structured, high_confidence_holistic_disagreement |

## Claim Matrix

| Claim | Evidence | Status | Safe paper wording |
|---|---|---|---|
| Explicit rubric reproduces holistic preferences | 152/180 (0.844; 95% CI 0.789–0.894) | supported | Explicit dimension-level scoring recovered the original holistic preference at the reported case-clustered agreement rate. |
| Dimension scores are order-robust | structured overall model-winner consistency 65/90 (0.722; 95% CI 0.633–0.811) | partial | Bidirectional auditing yielded the reported order consistency; this measures workflow robustness rather than objective correctness. |
| Unstable pairs have smaller rubric margins | mean across dimensions: stable=0.363, unstable=0.327; stable higher on 3/5 dimensions | partial | Order-unstable pairs had a slightly smaller mean rubric margin, but the direction was not uniform across dimensions; we treat this as descriptive evidence. |
| Falsifiability contributes diagnostic signal | non-tie dimension verdict 33/180 (0.183; 95% CI 0.122–0.244) | partial | Falsifiability produced non-tied score differences at the reported frequency, but rarely served as the sole decisive dimension. |
| Structured Gemini dimensions align with humans | Handled by a separate human-calibration session; no human files were read here. | out_of_scope | No human-alignment claim follows from this automatic audit alone. |

## Paper-Facing Wording

### 中文结论

在90个分层抽样的真实模型对上，五维显式评分的 structured overall 与原 holistic Gemini 判断一致 152/180（84.4%），等权 score-sum 一致 145/180（80.6%）。映射回同一模型身份后，structured overall 的正反序一致为 65/90（72.2%）。这些结果衡量显式 rubric 与既有自动判分流程的内部一致性；它们不证明 Gemini 的隐式推理必然采用五个维度，也不建立客观科研质量真值。

### Experiments

On a stratified 90-pair audit evaluated in both answer orders, the explicit five-dimension protocol matched the original holistic Gemini verdict on 152/180 ordered judgments (84.4%). The preregistered equal-weight score-sum rule matched on 145/180 (80.6%). After aligning answer identity across orders, the structured overall winner was consistent for 65/90 cases (72.2%). All confidence intervals use 10,000 case-clustered bootstrap resamples.

### Limitation

This audit measures consistency between two prompting protocols applied to the same Gemini judge. Agreement does not show that the original holistic judge internally followed each rubric dimension, and disagreement may reflect prompt-induced behavior as well as position sensitivity. The four real-versus-naive controls provide only a lower-anchor sanity check. Human alignment is evaluated separately and is outside this automatic audit.
