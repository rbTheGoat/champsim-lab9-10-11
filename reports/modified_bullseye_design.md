# Modified Bullseye Predictor Design

## Assignment interpretation

The assignment specifies the following simplified control flow:

1. Predict using the existing hashed-perceptron predictor.
2. If the base prediction is wrong, increment a miss counter for that branch PC.
3. When the miss count exceeds a fixed threshold, place the PC in an H2P table.
4. Use a dedicated per-PC mini perceptron for H2P-resident branches.
5. Override the base prediction with the mini-perceptron prediction.

This implementation follows that requested pattern. It is inspired by the Bullseye
paper but does not claim to reproduce the paper's full TAGE-SC-L, HIT trial,
dual local/global perceptron, and admission system.

## Structures

### Base predictor
- 16-table hashed perceptron
- Geometric global-history lengths up to 232 branches
- Dynamic training threshold inherited from the supplied ChampSim predictor

### Miss tracker
- 256 sets
- 4 ways
- LRU-style replacement
- Saturating per-PC base-misprediction count

### Fixed H2P admission threshold
- 64 base-predictor mispredictions

### H2P table
- 16 sets
- 4 ways
- 64 total H2P entries
- LRU-style replacement
- One dedicated 24-history-bit mini perceptron per resident PC

### Prediction
- Non-H2P PC: hashed-perceptron output
- H2P-resident PC: mini-perceptron output overrides the base output

### Training
- The base predictor continues training for every branch.
- The mini perceptron trains on a misprediction or a low-confidence correct prediction.
- Actual outcomes update both the base global history and mini-perceptron history.

## Comparison target

The fixed-threshold predictor will be evaluated using the same:
- four single-core traces,
- fixed four-core trace mix,
- warm-up length,
- simulation length,
- cache hierarchy,
- measured lookup-latency instrumentation,
- parsing and graphing methodology

used for bimodal, gshare, hashed perceptron, and perceptron.
