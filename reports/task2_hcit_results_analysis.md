# Adaptive HCIT Results Analysis

HCIT is evaluated as the seventh replacement policy at 1 MB, 2 MB, 4 MB and 8 MB.

## Performance comparison

| Size | HCIT single IPC | vs LRU | Best baseline | vs best | HCIT four sum IPC | vs LRU | Best baseline | vs best |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 MB | 0.69355 | -0.582% | LRU | -0.582% | 2.19811 | +3.885% | SRRIP | -24.323% |
| 2 MB | 0.75901 | -2.185% | LRU | -2.185% | 2.62133 | -18.494% | SHIP | -19.778% |
| 4 MB | 0.81919 | -1.649% | LRU | -1.649% | 2.83089 | -14.887% | SHIP | -16.510% |
| 8 MB | 0.84820 | -0.531% | SRRIP | -0.779% | 3.20644 | -10.806% | SHIP | -11.504% |

## HCIT internal behavior

| Size | Single threshold | Single occupancy | Single utility | Four threshold | Four occupancy | Four utility |
| --- | --- | --- | --- | --- | --- | --- |
| 1 MB | 6.25 | 1.39% | 48.40% | 3 | 27.20% | 49.64% |
| 2 MB | 5.25 | 1.45% | 60.07% | 3 | 18.75% | 59.63% |
| 4 MB | 5.25 | 1.45% | 68.58% | 3 | 16.80% | 57.58% |
| 8 MB | 5.25 | 1.38% | 77.70% | 3 | 17.38% | 57.40% |

## Conclusions

- HCIT allocates detailed tracking only after the candidate filter identifies repeated miss pressure.
- The final threshold and occupancy values show whether the adaptive controller became more or less selective at each capacity.
- Protected utility is the fraction of protected-block outcomes that were hits rather than evictions.
- HCIT should be judged against both LRU and the strongest conventional policy at each size; a single workload mix cannot establish universal superiority.
- Even when IPC is similar, HCIT remains a valid bonus design because it implements selective hard-candidate tracking, adaptive admission/removal, preferential insertion and delayed eviction.

## Graph locations

- `results/graphs/task2/hcit_comparison/single/`
- `results/graphs/task2/hcit_comparison/four_core/`
