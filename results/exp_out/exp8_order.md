# exp8 顺序置换(developer-led)— 摘要

## 顺序效应 vs 基底效应(极差比较)

| metric   |   median_order_spread |   substrate_spread_canonical |   order/substrate |
|:---------|----------------------:|-----------------------------:|------------------:|
| far      |                 0     |                        1.424 |             0     |
| coverage |                 0     |                        0.096 |             0     |
| h_mean   |                 0.852 |                       41.462 |             0.021 |
| h_max    |                 0     |                       75.541 |             0     |
| h_cv     |                 0.005 |                        0.226 |             0.022 |
| slender  |                 0.061 |                        2.51  |             0.024 |
| n        |                28     |                     2009     |             0.014 |
| grain    |                 2.556 |                       57.18  |             0.045 |

论文写法:非交换性真实存在(order spread ≠ 0),但顺序效应/基底效应 = 表中比值;
并论证 canonical 顺序编码权力行动的时间序(assemble→verticalize→densify)。

## 全表

| district   | order              |   far |   coverage |   h_mean |    h_max |   h_cv |   slender |    n |   grain |
|:-----------|:-------------------|------:|-----------:|---------:|---------:|-------:|----------:|-----:|--------:|
| lujiazui   | split→slim→densify | 3.47  |      0.094 |  119.746 |  480     |  1.007 |     7.014 | 3409 | 128.098 |
| lujiazui   | split→densify→slim | 3.756 |      0.094 |  127.205 | 1066.67  |  1.161 |     7.014 | 3409 | 128.098 |
| lujiazui   | slim→split→densify | 3.47  |      0.094 |  112.67  |  480     |  1.009 |     6.739 | 3285 | 120.084 |
| lujiazui   | slim→densify→split | 3.47  |      0.094 |  112.67  |  480     |  1.009 |     6.739 | 3285 | 120.084 |
| lujiazui   | densify→split→slim | 3.756 |      0.094 |  127.205 | 1066.67  |  1.161 |     7.014 | 3409 | 128.098 |
| lujiazui   | densify→slim→split | 3.756 |      0.094 |  118.102 | 1066.67  |  1.141 |     6.739 | 3285 | 120.084 |
| caoyang    | split→slim→densify | 3.13  |      0.139 |   82.594 |  426.058 |  0.781 |     5.771 | 1692 | 131.655 |
| caoyang    | split→densify→slim | 3.13  |      0.139 |   82.594 |  426.058 |  0.781 |     5.771 | 1692 | 131.655 |
| caoyang    | slim→split→densify | 3.13  |      0.139 |   81.742 |  426.058 |  0.786 |     5.71  | 1664 | 128.968 |
| caoyang    | slim→densify→split | 3.13  |      0.139 |   81.742 |  426.058 |  0.786 |     5.71  | 1664 | 128.968 |
| caoyang    | densify→split→slim | 3.13  |      0.139 |   82.594 |  426.058 |  0.781 |     5.771 | 1692 | 131.655 |
| caoyang    | densify→slim→split | 3.13  |      0.139 |   81.742 |  426.058 |  0.786 |     5.71  | 1664 | 128.968 |
| laoximen   | split→slim→densify | 4.379 |      0.19  |   78.284 |  419.621 |  0.877 |     6.022 | 1599 |  91.41  |
| laoximen   | split→densify→slim | 4.379 |      0.19  |   78.284 |  419.621 |  0.877 |     6.022 | 1599 |  91.41  |
| laoximen   | slim→split→densify | 4.379 |      0.19  |   77.811 |  419.621 |  0.881 |     5.982 | 1583 |  90.51  |
| laoximen   | slim→densify→split | 4.379 |      0.19  |   77.811 |  419.621 |  0.881 |     5.982 | 1583 |  90.51  |
| laoximen   | densify→split→slim | 4.379 |      0.19  |   78.284 |  419.621 |  0.877 |     6.022 | 1599 |  91.41  |
| laoximen   | densify→slim→split | 4.379 |      0.19  |   77.811 |  419.621 |  0.881 |     5.982 | 1583 |  90.51  |
| dapuqiao   | split→slim→densify | 4.554 |      0.154 |  117.854 |  480     |  0.803 |     8.281 | 1400 | 112.763 |
| dapuqiao   | split→densify→slim | 4.602 |      0.154 |  118.59  |  704.563 |  0.828 |     8.281 | 1400 | 112.763 |
| dapuqiao   | slim→split→densify | 4.554 |      0.154 |  116.071 |  480     |  0.8   |     8.124 | 1376 | 110.207 |
| dapuqiao   | slim→densify→split | 4.554 |      0.154 |  116.071 |  480     |  0.8   |     8.124 | 1376 | 110.207 |
| dapuqiao   | densify→split→slim | 4.602 |      0.154 |  118.59  |  704.563 |  0.828 |     8.281 | 1400 | 112.763 |
| dapuqiao   | densify→slim→split | 4.602 |      0.154 |  116.32  |  704.563 |  0.809 |     8.124 | 1376 | 110.207 |
| yuyuan     | split→slim→densify | 4.195 |      0.182 |   83.274 |  404.459 |  0.825 |     7.378 | 1666 |  74.475 |
| yuyuan     | split→densify→slim | 4.195 |      0.182 |   83.274 |  404.459 |  0.825 |     7.378 | 1666 |  74.475 |
| yuyuan     | slim→split→densify | 4.195 |      0.182 |   82.682 |  404.459 |  0.829 |     7.413 | 1636 |  71.988 |
| yuyuan     | slim→densify→split | 4.195 |      0.182 |   82.682 |  404.459 |  0.829 |     7.413 | 1636 |  71.988 |
| yuyuan     | densify→split→slim | 4.195 |      0.182 |   83.274 |  404.459 |  0.825 |     7.378 | 1666 |  74.475 |
| yuyuan     | densify→slim→split | 4.195 |      0.182 |   82.682 |  404.459 |  0.829 |     7.413 | 1636 |  71.988 |