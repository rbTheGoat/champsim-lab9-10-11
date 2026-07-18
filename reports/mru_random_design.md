# MRU and Random LLC Replacement Policies

## Interface compatibility

Both policies implement the exact replacement interface used by this ChampSim
version:

- `CACHE::llc_initialize_replacement()`
- `CACHE::llc_find_victim(...)`
- `CACHE::llc_update_replacement_state(...)`
- `CACHE::llc_replacement_final_stats()`

The build script copies the selected `.llc_repl` file to
`replacement/llc_replacement.cc` before compilation.

## MRU

### State

MRU stores one way index per LLC set. The index identifies the block that was
accessed most recently.

### Victim selection

1. Select an invalid way when one exists.
2. Otherwise evict the stored most-recently-used way.

### State update

Every LLC hit and fill marks the accessed way as most recently used, except for
writeback hits. This exception matches the behavior of the supplied LRU policy.

### Expected behavior

MRU deliberately evicts the newest block. It can perform poorly on workloads
with strong temporal locality, but may help particular cyclic or scan-like
access patterns where the newest block is not reused soon.

## Random

### State

Random uses one deterministic xorshift64* pseudo-random generator per core.

### Victim selection

1. Select an invalid way when one exists.
2. Otherwise choose a way uniformly using `random_value % LLC_WAY`.

### Reproducibility

Fixed seeds are used instead of `srand(time(NULL))`. Repeated simulations with
the same inputs therefore use the same replacement sequence.

### State update

No per-block recency or prediction state is maintained.

## Final statistics

Each implementation prints its invalid-way and valid-victim selection counts.
MRU additionally prints the number of recency-state updates.
