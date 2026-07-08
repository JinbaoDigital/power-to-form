# exp7 参数敏感性(OAT ±30%)— 摘要

| regime              |   step | param              | signature_5of5   |   dip_bimodal_count |
|:--------------------|-------:|:-------------------|:-----------------|--------------------:|
| developer_led       |      1 | above_m2 x0.7      | False            |                 nan |
| developer_led       |      1 | above_m2 x1.3      | True             |                 nan |
| developer_led       |      1 | k x0.7             | True             |                 nan |
| developer_led       |      1 | k x1.3             | True             |                 nan |
| developer_led       |      2 | ratio x0.7         | False            |                 nan |
| developer_led       |      2 | ratio x1.3         | True             |                 nan |
| developer_led       |      3 | far_gain x0.7      | True             |                 nan |
| developer_led       |      3 | far_gain x1.3      | False            |                 nan |
| developer_led       |      3 | cap_m x0.7         | False            |                 nan |
| developer_led       |      3 | cap_m x1.3         | True             |                 nan |
| state_led           |      0 | weights.state x0.7 | True             |                 nan |
| state_led           |      0 | weights.state x1.3 | True             |                 nan |
| state_led           |      1 | reach_frac x0.7    | True             |                 nan |
| state_led           |      1 | reach_frac x1.3    | True             |                 nan |
| state_led           |      1 | cap_m x0.7         | True             |                 nan |
| state_led           |      1 | cap_m x1.3         | True             |                 nan |
| resident_self_build |      1 | cell_m2 x0.7       | True             |                   5 |
| resident_self_build |      1 | cell_m2 x1.3       | True             |                   5 |
| resident_self_build |      2 | alpha x0.7         | True             |                   5 |
| resident_self_build |      2 | alpha x1.3         | True             |                   5 |
| shared              |      0 | ratio x0.7         | True             |                 nan |
| shared              |      0 | ratio x1.3         | True             |                 nan |
| shared              |      0 | cap_m x0.7         | True             |                 nan |
| shared              |      0 | cap_m x1.3         | True             |                 nan |
| shared              |      1 | alpha x0.7         | True             |                 nan |
| shared              |      1 | alpha x1.3         | True             |                 nan |

**翻转的格子:4 个**(空 = 所有涌现签名对 ±30% 扰动稳健)。
论文写法:'each recipe's emergent signature survives ±30% one-at-a-time perturbation of its parameters except …' 按此表填空。