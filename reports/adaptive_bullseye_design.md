# Adaptive-Threshold Modified Bullseye Predictor

## Goal

The fixed Modified Bullseye predictor admits a branch PC into the H2P table
after a fixed number of base-predictor misses. The assignment additionally asks
for a predictor that changes its threshold while the simulation is running.

This implementation retains the same hashed-perceptron base and dedicated H2P
mini perceptrons, but changes the H2P admission threshold independently for
each core.

## Starting configuration

- Initial admission threshold: 64 base-predictor misses
- Minimum threshold: 16
- Maximum threshold: 128
- Adjustment step: 8
- Adaptation epoch: 8,192 observed branches

## Signals observed per epoch

1. Recent base-predictor miss rate
2. Number of H2P overrides
3. Accuracy of H2P overrides
4. Current H2P occupancy

## Threshold policy

### Lower the threshold

The threshold is reduced by 8 when:

- recent base-predictor miss rate is above 10%, and
- the H2P layer has insufficient samples or at least 75% override accuracy.

This admits difficult branches sooner when the base predictor is struggling and
the H2P mechanism appears useful.

### Raise the threshold

The threshold is increased by 8 when either:

- H2P has at least 128 recent override samples but accuracy is below 55%;
- H2P occupancy is at least 87.5% while the recent base miss rate is below 10%;
- recent base-predictor miss rate is below 4%.

This conserves H2P capacity when the base predictor already performs well, the
H2P overrides are weak, or table pressure is high.

## Bounded adaptation

The threshold is clamped to the range 16–128. Epoch counters are reset after
each adaptation decision, while predictor state and per-PC miss counters remain
live.

## Final instrumentation

At program exit, the predictor prints for every core:

- final admission threshold;
- number of threshold adjustments;
- base-predictor miss rate;
- H2P occupancy;
- H2P admissions;
- H2P overrides;
- H2P override accuracy.

These fields provide direct evidence that the threshold changed during the
simulation and help explain the measured MPKI, accuracy, lookup latency, IPC,
and simulation-time results.

## Fair comparison

The adaptive predictor will use the same:

- four single-core traces;
- fixed randomly generated four-core trace mix;
- warm-up and simulation lengths;
- cache hierarchy;
- disabled prefetchers;
- LLC LRU policy;
- latency instrumentation;
- result parsing and plotting methodology

used for all earlier Task 1 predictors.
