# exp12 聚类对抗性翻转(resident→state,老西门+豫园连片)— 摘要

| f | seed | dev 签名 5/5 | ρ_res | ρ_dev | 选择性存活 | state 最大偏差% | state 仍最小偏差 |
|---|---|---|---|---|---|---|---|
| 30% | 0 | True | -0.9 | 0.4 | False | 4.6 | True |
| 30% | 1 | True | -0.8 | 0.4 | False | 4.6 | True |
| 30% | 2 | True | -0.9 | 0.4 | False | 4.6 | True |
| 60% | 0 | True | -0.9 | -0.7 | False | 4.6 | True |
| 60% | 1 | True | -0.9 | -0.6 | False | 4.6 | True |
| 60% | 2 | True | -0.9 | -0.6 | False | 4.7 | True |

f=30%:签名存活 3/3,选择性存活 0/3,state 最小偏差 3/3

f=60%:签名存活 3/3,选择性存活 0/3,state 最小偏差 3/3

读法:这是**对抗性**扰动——按已知误标方向(直管公房)、空间连片地翻;比 exp2 的随机翻转更狠。存活/失守都如实进 §5.5(labels 轴升级为 random + adversarial)。