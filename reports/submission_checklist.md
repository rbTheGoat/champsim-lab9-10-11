# Computer Architecture Lab 9–11 Submission Checklist

## General
- [ ] Final GitHub repository pushed
- [ ] README with build and reproduction instructions
- [ ] Baseline cache configuration documented
- [ ] All experiments use documented warm-up and simulation lengths
- [ ] No trace files or binaries committed
- [ ] Final report exported as PDF
- [ ] Final report source retained as DOCX

## Random Multicore Trace Selection
- [x] Random trace generator program
- [x] Fixed random seed documented
- [x] Selected four-core traces saved
- [ ] Same selected traces used consistently for fair multicore comparisons

## Task 1: Existing Branch Predictors
- [ ] Bimodal single-core results
- [ ] Gshare single-core results
- [ ] Hashed perceptron single-core results
- [ ] Perceptron single-core results
- [ ] Bimodal four-core results
- [ ] Gshare four-core results
- [ ] Hashed perceptron four-core results
- [ ] Perceptron four-core results
- [ ] MPKI tables and graphs
- [ ] Prediction accuracy tables and graphs
- [ ] Prediction latency method and results
- [ ] Simulation execution-time tables and graphs

## Task 1 Bonus
- [ ] Modified Bullseye source
- [ ] Modified Bullseye explanation
- [ ] Modified Bullseye single-core results
- [ ] Modified Bullseye four-core results
- [ ] Adaptive-threshold Bullseye source
- [ ] Adaptive-threshold algorithm explanation
- [ ] Adaptive-threshold single-core results
- [ ] Adaptive-threshold four-core results
- [ ] Comparison with all existing predictors
- [ ] Design insights and limitations

## Task 2: LLC Size
- [ ] 1 MB LLC results
- [ ] 2 MB LLC results
- [ ] 4 MB LLC results
- [ ] 8 MB LLC results
- [ ] LLC-size graphs and explanation

## Task 2: Associativity
- [ ] 16-way LLC results
- [ ] 8-way LLC results
- [ ] Associativity graphs and explanation

## Task 2: Replacement Policies
- [ ] LRU results
- [ ] SRRIP results
- [ ] DRRIP results
- [ ] SHIP results
- [ ] MRU implementation
- [ ] MRU results
- [ ] Random implementation
- [ ] Random results

## Task 2 Metrics
- [ ] Cumulative IPC
- [ ] L1-I miss percentage
- [ ] L1-D miss percentage
- [ ] L2 miss percentage
- [ ] LLC miss percentage
- [ ] LLC hit rate
- [ ] Total LLC writes
- [ ] Simulation execution time
- [ ] Single-core tables and graphs
- [ ] Four-core tables and graphs

## Task 2 Bonus: HCIT
- [ ] HCIT source file
- [ ] Miss tracking
- [ ] Insertion tracking
- [ ] Hit tracking
- [ ] Eviction tracking
- [ ] Hard-to-cache metric
- [ ] Adaptive protection mechanism
- [ ] Adaptive admission mechanism
- [ ] Adaptive eviction mechanism
- [ ] Baseline comparisons
- [ ] HCIT results and analysis

## Final Evidence
- [ ] Raw output files retained
- [ ] Timing files retained
- [ ] Parsed CSV files retained
- [ ] All graphs retained as image files
- [ ] Every graph value traceable to raw output
- [ ] Final conclusions supported by measured results
