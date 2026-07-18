# Adaptive Hard-to-Cache Identification Table (HCIT) Policy

## Objective

The policy is inspired by the observation that a small subset of branches can
account for most branch-prediction misses. It applies the same idea to the LLC:
only repeatedly difficult PCs or memory regions receive detailed tracking and
preferential cache protection.

## 1. Candidate identification

Every LLC request is mapped to a signature:

- Demand, RFO and prefetch requests use a hash of the instruction PC.
- Writebacks, which do not carry a useful PC in this simulator, use a hashed
  4-KB memory-region signature.

A 4096-entry, 4-bit candidate filter tracks recent miss pressure for all
signatures. The filter is deliberately small and approximate. It prevents the
larger HCIT from being allocated to ordinary one-off misses.

## 2. HCIT structure

The detailed HCIT contains 2048 entries arranged as 512 sets × 4 ways. An entry
is allocated only after its candidate-filter pressure reaches the current
adaptive admission threshold.

Each HCIT entry stores:

- signature,
- misses,
- insertions,
- hits,
- evictions,
- hardness score,
- last-touch timestamp,
- stale-epoch count.

This directly satisfies the requirement to track misses, insertions, hits and
evictions per PC or memory region.

## 3. Hardness metric

At the end of every 16,384 LLC updates, counters are decayed and the score is
recomputed as:

`hardness = clamp(2×misses + 2×evictions + insertions − 2×hits, 0, 31)`

Misses and evictions increase difficulty. Hits decrease difficulty because they
show that the block is now being retained and reused successfully.

An HCIT entry is considered hard when:

`score >= adaptive admission threshold`

## 4. Adaptive admission and removal

The admission threshold begins at 6 and is restricted to the range 3–12.

It increases when:

- HCIT occupancy is high and protected-block utility is low, or
- protected evictions substantially exceed protected hits.

It decreases when:

- HCIT occupancy is low and protected-block utility is high, or
- protected hits strongly exceed protected evictions.

HCIT sets replace their lowest-score entry, with oldest touch as a tie-breaker.
A candidate is rejected when it is clearly weaker than the selected HCIT
victim.

Old entries leave the HCIT after repeated low-score, low-activity epochs.

## 5. Adaptive protection mechanism

The cache itself uses a 2-bit RRIP state:

- Normal insertion: RRPV = 2.
- Hard-candidate insertion: RRPV = 0.
- Cache hit: RRPV = 0.

Victim selection first searches for an unprotected block with maximum RRPV.
Unprotected blocks are aged before protected blocks. A protected block is
selected only when all ways in the set are protected.

This combines:

- preferential insertion,
- delayed eviction,
- adaptive admission,
- adaptive removal.

## 6. Storage overhead

Approximate policy storage at the default 4-MB, 16-way LLC:

- RRIP state: 2 bits per LLC block.
- Per-block signature metadata: 64 bits plus one valid bit per LLC block.
- Candidate filter: 4096 × 4 bits.
- HCIT: 2048 detailed entries.

The large per-block signature is used here for implementation clarity and
experimental correctness. A hardware implementation could store compressed
signatures or tags to reduce overhead.

## 7. Printed statistics

The policy prints:

- final adaptive threshold,
- threshold increases/decreases,
- HCIT occupancy,
- admissions and rejected admissions,
- HCIT replacements and stale removals,
- protected and normal fills,
- protected hits and evictions,
- protection utility,
- protected/unprotected victim selections.
