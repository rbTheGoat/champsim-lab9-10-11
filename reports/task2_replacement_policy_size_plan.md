# Task 2 Replacement-Policy × LLC-Size Experiment

## Purpose

Compare these LLC replacement policies at 1 MB, 2 MB, 4 MB and 8 MB:

- LRU
- SRRIP
- DRRIP
- SHIP
- MRU
- Random

The supplied LRU data is reused from the completed LLC-size experiment.
The new runner executes the remaining five policies.

## Fixed parameters

- Predictor: hashed perceptron
- L1-I: 32 KB, 8-way, LRU
- L1-D: 32 KB, 8-way, LRU
- L2: 256 KB, 8-way, LRU
- LLC associativity: 16-way
- Block size: 64 B
- Warm-up: 1 million instructions
- Simulation: 10 million instructions
- Single-core traces: the same four traces used in the LLC-size study
- Four-core mix: the stored seeded random trace selection

## New runs

For each of the five non-LRU policies:

- Four LLC sizes
- Four single-core traces per size
- One four-core mix per size

Total new simulations:

- 80 single-core runs
- 20 four-core runs
- 100 simulations total

The runner is resume-safe: a result is skipped only when both its completed
simulator output and timing file are present.
