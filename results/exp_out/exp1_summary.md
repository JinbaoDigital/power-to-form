# exp1 级联信度 — 摘要

## 级联深度(各街道由第几跳决定,%)

| district   |    n |   1_euluc |   2_function |   3_aoi |   unknown |
|:-----------|-----:|----------:|-------------:|--------:|----------:|
| lujiazui   | 1849 |      97.1 |          0.9 |     1.3 |       0.8 |
| caoyang    | 1072 |      97.7 |          0.8 |     0.8 |       0.7 |
| laoximen   |  923 |      95.3 |          2.3 |     0.2 |       2.2 |
| dapuqiao   |  785 |      93.5 |          2.8 |     1.7 |       2   |
| yuyuan     |  819 |      97.6 |          0.7 |     0.5 |       1.2 |

## 源间一致性(两两,重叠子集)

| district   | pair           |   n_overlap |   overlap_pct |   agreement_pct |   kappa |
|:-----------|:---------------|------------:|--------------:|----------------:|--------:|
| lujiazui   | euluc~function |        1121 |          60.6 |            76   |   0.388 |
| lujiazui   | euluc~aoi      |        1267 |          68.5 |            25.7 |   0.052 |
| lujiazui   | function~aoi   |         890 |          48.1 |            10.2 |   0.006 |
| caoyang    | euluc~function |         697 |          65   |            86.8 |   0.352 |
| caoyang    | euluc~aoi      |         808 |          75.4 |            10.6 |   0.038 |
| caoyang    | function~aoi   |         567 |          52.9 |             5.1 |   0.019 |
| laoximen   | euluc~function |         444 |          48.1 |            64.4 |   0.017 |
| laoximen   | euluc~aoi      |         363 |          39.3 |            19.3 |   0.044 |
| laoximen   | function~aoi   |         213 |          23.1 |             2.8 |  -0.01  |
| dapuqiao   | euluc~function |         438 |          55.8 |            62.8 |   0.149 |
| dapuqiao   | euluc~aoi      |         451 |          57.5 |            21.1 |   0.001 |
| dapuqiao   | function~aoi   |         295 |          37.6 |            11.2 |  -0.008 |
| yuyuan     | euluc~function |         389 |          47.5 |            53.2 |   0.141 |
| yuyuan     | euluc~aoi      |         252 |          30.8 |            12.7 |   0.029 |
| yuyuan     | function~aoi   |         156 |          19   |            11.5 |   0.024 |

## 加权合并(跨街道)

| pair           |    n |   agree_w |
|:---------------|-----:|----------:|
| euluc~aoi      | 3141 |      19.4 |
| euluc~function | 3089 |      72   |
| function~aoi   | 2121 |       8.3 |

写进论文 §3.5:深度分布回答「多源是不是单源+补丁」;κ 回答「独立证据对归属的同意度」。