# Task 2 Results Analysis

## Experimental basis

- L1-I: 32 KB, 8-way, LRU
- L1-D: 32 KB, 8-way, LRU
- L2: 256 KB, 8-way, LRU
- Default LLC: 4 MB, 16-way
- Block size: 64 bytes
- Branch predictor held constant: hashed perceptron
- Four single-core traces per configuration
- One seeded four-program mix for four-core experiments

**LLC-write definition used in the tables:** `LLC RFO accesses + LLC WRITEBACK accesses`. These fields are also retained separately in the detailed CSV files.

## 1. LLC Size Study: 1 MB, 2 MB, 4 MB and 8 MB

All configurations use a 16-way LLC, LRU replacement and the hashed-perceptron branch predictor.

### Single-core summary

| LLC size | Geomean IPC | L1 miss % | L2 miss % | LLC miss % | LLC hit % | LLC writes | Time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 MB | 0.697613 | 10.6261 | 51.4193 | 25.1881 | 74.8119 | 1,430,619 | 15.350 |
| 2 MB | 0.775963 | 10.6380 | 51.4191 | 20.2299 | 79.7701 | 1,430,620 | 14.912 |
| 4 MB | 0.832926 | 10.6458 | 51.4189 | 18.4076 | 81.5924 | 1,430,621 | 14.320 |
| 8 MB | 0.852731 | 10.6480 | 51.4189 | 18.1427 | 81.8573 | 1,430,622 | 17.688 |

### Four-core summary

| LLC size | Sum IPC | Geomean IPC | L1 miss % | L2 miss % | LLC miss % | LLC hit % | LLC writes | Time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 MB | 2.115899 | 0.366720 | 7.8964 | 47.1916 | 92.7976 | 7.2024 | 25,646.00 | 787.520 |
| 2 MB | 3.216118 | 0.591101 | 7.9274 | 47.1864 | 73.1836 | 26.8164 | 25,349.00 | 540.080 |
| 4 MB | 3.326025 | 0.622505 | 7.9282 | 47.2070 | 45.5794 | 54.4206 | 25,851.00 | 473.710 |
| 8 MB | 3.594913 | 0.685192 | 7.9248 | 47.2330 | 24.7394 | 75.2606 | 26,036.00 | 386.640 |

### Main observations

- The best single-core geometric-mean IPC occurs at **8 MB**, while the lowest weighted single-core LLC miss percentage occurs at **8 MB**.
- Moving from 1 MB to 8 MB changes single-core geometric-mean IPC by **+22.236%** and LLC miss percentage by **-27.971%**.
- The best four-core aggregate IPC occurs at **8 MB**, while the lowest shared-LLC miss percentage occurs at **8 MB**.
- Moving from 1 MB to 8 MB changes four-core aggregate IPC by **+69.900%** and shared-LLC miss percentage by **-73.340%**.
- L1 and L2 miss percentages are included for completeness, but LLC capacity changes primarily affect the shared last-level cache. Any L1/L2 variation is indirect, caused by timing, replacement interactions and the set of requests reaching the LLC.

## 2. LLC Associativity Study: 16-way vs 8-way

The LLC capacity is held at 4 MB. Therefore, the 16-way configuration uses 4096 sets and the 8-way configuration uses 8192 sets, both with 64-byte blocks.

### Single-core comparison

| Associativity | Geomean IPC | LLC miss % | LLC hit % | LLC writes | Time (s) |
| --- | --- | --- | --- | --- | --- |
| 16-way | 0.832926 | 18.4076 | 81.5924 | 1,430,621 | 14.320 |
| 8-way | 0.832847 | 18.4412 | 81.5588 | 1,430,619 | 11.893 |

### Four-core comparison

| Associativity | Sum IPC | LLC miss % | LLC hit % | LLC writes | Time (s) |
| --- | --- | --- | --- | --- | --- |
| 16-way | 3.326025 | 45.5794 | 54.4206 | 25,851.00 | 473.710 |
| 8-way | 3.319878 | 47.4394 | 52.5606 | 26,565.00 | 400.420 |

### Main observations

- Reducing associativity from 16-way to 8-way produces a **negligible** single-core geometric-mean IPC change of **-0.009%**.
- The weighted single-core LLC miss percentage increased by **+0.183%**.
- Four-core aggregate IPC changes by **-0.185%**, while shared-LLC miss percentage changes by **+4.081%**.
- At fixed capacity, lower associativity reduces the number of candidate locations available to each address and can increase conflict misses. However, doubling the number of sets changes address mapping, so particular workloads may show little loss or even a small improvement. The measured workload results, rather than associativity alone, determine the final conclusion.

## 3. Replacement-Policy × LLC-Size Study

The comparison includes LRU, SRRIP, DRRIP, SHIP, the implemented MRU policy and the implemented deterministic Random policy.

### IPC winners by LLC size

| LLC size | Single-core winner | Geomean IPC | Four-core winner | Sum IPC |
| --- | --- | --- | --- | --- |
| 1 MB | LRU | 0.697613 | SRRIP | 2.904598 |
| 2 MB | LRU | 0.775963 | SHIP | 3.267608 |
| 4 MB | LRU | 0.832926 | SHIP | 3.390684 |
| 8 MB | SRRIP | 0.854861 | SHIP | 3.623260 |

### Cross-size policy consistency

| Policy | Avg single rank | Avg four-core rank | Mean single geomean IPC | Mean four-core sum IPC |
| --- | --- | --- | --- | --- |
| LRU | 1.25 | 2.75 | 0.789808 | 3.063239 |
| SHIP | 2.75 | 1.25 | 0.787901 | 3.284071 |
| SRRIP | 2.75 | 3.00 | 0.786920 | 3.230460 |
| DRRIP | 3.25 | 3.00 | 0.786454 | 3.175593 |
| Random | 5.25 | 5.00 | 0.763528 | 2.848260 |
| MRU | 5.75 | 6.00 | 0.732199 | 1.784757 |

### Main observations

- **LRU** has the best average single-core IPC rank across the four LLC sizes.
- **SHIP** has the best average four-core aggregate-IPC rank across the four LLC sizes.
- At 1 MB, MRU changes IPC relative to LRU by **-10.503%** in single-core and **-25.176%** in four-core; Random changes it by **-4.713%** and **-5.707%**, respectively.
- At 2 MB, MRU changes IPC relative to LRU by **-12.015%** in single-core and **-50.140%** in four-core; Random changes it by **-5.291%** and **-14.344%**, respectively.
- At 4 MB, MRU changes IPC relative to LRU by **-6.809%** in single-core and **-50.773%** in four-core; Random changes it by **-2.674%** and **-5.861%**, respectively.
- At 8 MB, MRU changes IPC relative to LRU by **-0.847%** in single-core and **-35.604%** in four-core; Random changes it by **-1.045%** and **-2.306%**, respectively.
- LRU exploits temporal locality, SRRIP/DRRIP estimate re-reference distance, and SHIP uses PC-based reuse prediction. MRU intentionally discards the newest line, while Random maintains no locality state. Differences between policies are therefore expected to be workload- and capacity-dependent.
- A policy should not be declared universally best from IPC alone. LLC miss rate, hit rate, writes and execution time must be checked for the same configuration, especially when policies have similar IPC.

## 4. Report-ready overall conclusion

Increasing LLC capacity generally provides more opportunity to retain reusable blocks, but the measured IPC benefit depends on whether the selected workloads are capacity- or conflict-sensitive. The LLC miss and hit-rate trends should therefore be interpreted together with IPC rather than in isolation.

Reducing associativity from 16-way to 8-way at fixed 4 MB capacity changes both the number of ways and the number of sets. The measured result captures the combined effect of reduced placement flexibility and changed address mapping.

The replacement-policy study demonstrates that no policy is automatically optimal at every capacity and workload mix. Re-reference-prediction policies can outperform simple recency when they identify low-reuse lines, while LRU remains a strong baseline. MRU and Random provide useful contrast because they intentionally remove or ignore temporal-locality information.

## 5. Graph locations

- LLC size: `results/graphs/task2/llc_size/`
- Associativity: `results/graphs/task2/llc_associativity/`
- Replacement policy × size: `results/graphs/task2/replacement_policy_size/`

## 6. Methodology note

The assignment states that the 64-byte block size has an exception for Task 2(d), but it does not provide alternative block sizes. Therefore, the experiments retain the specified 64-byte block size and document this assumption rather than inventing an unsupported configuration.
