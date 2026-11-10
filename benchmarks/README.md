# Repository-owned benchmark adapters

Active library checkouts contain pinned upstream source. N-Queens drivers,
metrics, JNI build configuration, and adapter build logic live here. The custom SoA
implementations are archived under `deprecated/NDD-SoA` and are not registered
in the runner.

`upstream-lock.json` records canonical URLs and exact revisions. The library
submodules use pre-benchmark upstream baselines compatible with the original
experiments, rather than silently upgrading library versions. Builds and runs
verify the checked-out revisions and reject changes to tracked upstream files
(Git normalizes Windows/Linux line endings for this check).

| Adapter | Upstream source | Revision |
| --- | --- | --- |
| `buddy/` | jgcoded/BuDDy | `80a1420` |
| `sylvan/` | trolando/sylvan 1.9.1 | `1ca6868` |
| `cudd/` | cuddorg/cudd | `e9c5eb4` |
| `oxidd/` | oxidd/oxidd | `4a68244` |
| `jdd/` (BDD and ZDD) | bitbucket.org/vahidi/jdd | `781c64e` |
| `javabdd/` (JFactory) | com-github-javabdd/com.github.javabdd | `a939fc8` |
| `jsylvan/` | utwente-fmt/jsylvan | `f97be81` |
| `decisiondiagrams/` | microsoft/DecisionDiagrams | `1d18b29` |
| `ndd/NDDPrimitiveBenchmark.java` | XJTU-NetVerify/NDD | `9c8eea1` |
| `ndd/NDDObjectBenchmark.java` | XJTU-NetVerify/NDD, original / reuse | `943476c` / `0a0811f` |

The JSylvan binding uses an additional unmodified Sylvan 1.4.1 checkout at
`6b3565f`; standalone Sylvan uses Lace 1.5.0 at `9f77066`. Both transitive
sources are pinned in the lock file. They are different Sylvan versions and
should be identified as such when reporting comparisons.

## Builds

`build.py` builds the adapters into ignored `.bench-build/` directories. Native
BuDDy, CUDD, Sylvan, and JSylvan builds run outside their source checkouts. Maven
and .NET may create their ordinary ignored library build outputs. No generated
source overlay, library-source patch, fork-only counter, or modified JNI wrapper
is required. Cached adapter builds are keyed by sources, configuration, and pins.

From PowerShell at the repository root:

```powershell
.\scripts\run_nqueens_wsl.ps1 --targets all --sizes 8 10 --workers 2 --timeout 100 --output .bench-build/experiments/smoke/nqueens_metrics.csv
```

`--targets all` selects all 15 upstream targets. Add `--skip-build` after a
successful build. Tests can be run with
`python -m unittest discover -s tests -v` using the configured Python environment.

## Measurements

Both construction strategies are available through the same adapters:
`--benchmark pairwise` (default) and `--benchmark rows`. The latter ports
SSoelvsten/bdd-benchmark's row/placement construction at commit `3c521e1` across
all targets, including NDD. Shared kernels live in `common/`; Rust and .NET
have equivalent implementations in their adapters. Algorithm provenance is in
[`common/row-construction.json`](common/row-construction.json), and the upstream
MIT notice is retained in [`licenses/bdd-benchmark-MIT.txt`](licenses/bdd-benchmark-MIT.txt).
Library pins and initialization remain shared between the two strategies.
Row runs write to `results/rows/` by default; the CSV includes a `benchmark` column.

For maintained `NDD`, `NDD-BCDD`, and `NDD-ZDD`, operation cache capacities can
be set with `--ndd-cache-size` and `--ndd-label-cache-size` (both default to
10,000 entries). These options do not change original/reuse caches. Row-run
metadata records both capacities. For example, add
`--ndd-cache-size 1000000 --ndd-label-cache-size 100000` to test larger caches.

- `time_sec`: process elapsed wall time for every implementation, including
  runtime startup and metrics output. `solver_time_sec` separately retains an
  adapter's internal solve time when available. Historical CSVs mixed these
  timing definitions and should not be combined with the new measurements.
- `max_rss_kb`: GNU time's kernel-reported peak RSS on Linux, so short native
  runs do not miss their peak. Timeouts and other platforms fall back to polling
  process-tree RSS at 50 ms intervals; that fallback can miss a short-lived peak.
- `nodes_alive`: final graph size from the library API. Object-based NDD counts
  distinct reachable nonterminal NDD and label nodes. Other APIs may include
  terminals or, for primitive NDD, retained nodes after collection.
- `nodes_created`: lifetime allocations only where an upstream API provides
  them: BuDDy's `bdd_stats.produced`, Sylvan's enabled statistics, and maintained
  NDD's counters. CUDD, OxiDD, JDD/ZDD, JavaBDD, JSylvan and DecisionDiagrams leave this field
  blank. A current table size or peak count is not substituted for allocations.
- `ndd_*` / `bdd_*`: graph-layer splits where available; `bdd_*` denotes label
  nodes for NDD-BCDD and NDD-ZDD as well. Unavailable counters are blank, not zero.
- `status`: `ok` or `timeout`. Timeout rows have blank solution/node counters.
- `upstream_url` and `upstream_revision`: the checked source used for that row;
  historical archived custom SoA rows leave them blank.

Plots omit unavailable metrics, and display an unavailable message when every
row lacks the requested counter. The CSV does not imply all node representations
have identical sizes or that native and JVM process startup costs are equal.

The Sylvan adapter uses a 2 GiB table budget, and protects intermediate roots
across library calls. JSylvan defaults to the runner's 2 GiB budget. Worker counts
are supplied by `--workers` (0 means library autodetection).

JavaBDD uses the pure Java `JFactory` backend, compiled directly from the pinned
source with Java 17. Its Boolean encoding, variable order (`i * N + j`), initial
node table (`N * N * 256`), and cache size (10,000) match the BuDDy adapter.
Automatic variable reordering is not enabled. `nodes_alive` comes from the final
root's `BDD.nodeCount()`; lifetime allocation counts remain unavailable.

OxiDD uses its native Rust BDD API with the index-based manager, multi-threaded
apply algorithms, and a direct-mapped apply cache. The fixed capacities are
2^26 inner nodes and 2^20 apply-cache entries; actual process peak RSS is measured
by the runner. `--workers` controls its worker pool (0 selects autodetection).
The Boolean encoding and variable order match BuDDy/JDD; no variable reordering
is requested. `nodes_alive` is `Function::node_count()`, including terminals.
Lifetime allocation counts remain unavailable. Release builds require Rust
1.91 or newer and use the adapter's committed Cargo lock file. Build outputs
go under `.bench-build/oxidd/`; a local toolchain under `.bench-build/tools/`
is used when `cargo` is not on `PATH`.

## Attribution

The adapters preserve the N-Queens models from the former benchmark forks and
upstream examples. Prior fork revisions: BuDDy `e35b26a`, Sylvan `060ce4e`, CUDD
`ada57af`, JDD `fa7f7e2`, JSylvan `8444f77`, DecisionDiagrams `4387a75`. NDD drivers
are derived from the pinned XJTU-NetVerify solver examples. Original notices and
applicable license texts are retained under `licenses/`.
