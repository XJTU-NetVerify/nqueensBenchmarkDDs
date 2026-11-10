# Benchmark results

The overview comparisons retain their CSVs and runtime/memory plots:

| Comparison | CSV | Coverage |
| --- | --- | --- |
| Pairwise | [pairwise/nqueens_metrics.csv](pairwise/nqueens_metrics.csv) | N=8–13, 14 default targets |
| Row-based | [rows/nqueens_metrics.csv](rows/nqueens_metrics.csv) | N=8–12, all 15 targets |

The row overview metadata records the requested N=8–13 range; only N=8–12
completed and were saved. Timeout values are limits, not completed solve times.

## NDD cache experiments

These single-run comparisons were measured on November 10, 2026, with a
100-second timeout per process. Each directory contains a CSV and its settings
in `benchmark.json`. Default caches use 10,000 NDD and 10,000 label entries;
larger caches use 1,000,000 NDD and 100,000 label entries.

| Experiment | CSV | Coverage |
| --- | --- | --- |
| Pairwise, default caches | [CSV](experiments/pairwise-default-cache/nqueens_metrics.csv) | N=13; NDD, NDD-BCDD, NDD-ZDD |
| Pairwise, larger caches | [CSV](experiments/pairwise-large-cache/nqueens_metrics.csv) | N=13; NDD, NDD-BCDD, NDD-ZDD |
| Rows, default caches | [CSV](experiments/rows-default-cache/nqueens_metrics.csv) | N=13; all five NDD variants; all timed out |
| Rows, larger caches | [CSV](experiments/rows-large-cache/nqueens_metrics.csv) | N=12–13; NDD, NDD-BCDD, NDD-ZDD |

## BITSET with smaller fields

The November 10, 2026 BITSET experiment splits each row into fields of at most
seven bits. At N=13, this gives 26 fields alternating between widths 7 and 6,
with no padding variables. These runs use 1,000,000 NDD cache entries and a
100-second timeout. The label cache setting is 100,000; BITSET uses its own
truth-table backend rather than a BDD label engine.

| Construction | CSV | N=13 wall time | Solutions |
| --- | --- | ---: | ---: |
| Rows | [CSV](experiments/ndd-bitset-width7/rows/nqueens_metrics.csv) | 24.36 s | 73,712 |
| Pairwise | [CSV](experiments/ndd-bitset-width7/pairwise/nqueens_metrics.csv) | 45.96 s | 73,712 |

These are single runs with a different field grouping from the ordinary NDD
comparisons; they do not isolate the effect of the label backend alone.

Incomplete reruns and experiments for the removed column-grouping implementation
are omitted. Historical versions remain available in Git history.

Experiment plots can be regenerated from the repository root, for example:

```bash
python3 scripts/plot_nqueens_results.py --input results/experiments/rows-large-cache/nqueens_metrics.csv --output .bench-build/plots/rows-large-cache
```
