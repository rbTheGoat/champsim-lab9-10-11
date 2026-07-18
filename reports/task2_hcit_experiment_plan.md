# Adaptive HCIT Experiment Plan

## Goal

Evaluate the adaptive HCIT policy against the six completed replacement
policies at 1 MB, 2 MB, 4 MB and 8 MB.

## Fixed parameters

- Branch predictor: hashed perceptron
- LLC associativity: 16-way
- Block size: 64 bytes
- L1-I: 32 KB, 8-way, LRU
- L1-D: 32 KB, 8-way, LRU
- L2: 256 KB, 8-way, LRU
- Warm-up: 1 million instructions
- Simulation: 10 million instructions
- Four single-core traces per size
- One seeded four-core trace mix per size

## Runs

- 4 LLC sizes × 4 single-core traces = 16 single-core runs
- 4 LLC sizes × 1 four-core mix = 4 four-core runs
- Total = 20 simulations

## Outputs

- Raw simulator outputs
- Timing files
- Build logs
- Configuration records
- Single-core and four-core manifests
- Printed HCIT internal statistics
