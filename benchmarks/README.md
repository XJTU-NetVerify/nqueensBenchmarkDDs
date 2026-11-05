# Repository-owned benchmark adapters

Active library checkouts contain pinned upstream source. N-Queens drivers,
metrics, JNI build configuration, and adapter build logic live here. The three
archived `deprecated/NDD-SoA` targets remain custom implementations.

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
| `jdd/` (BDD and ZDD) | bitbucket.org/vahidi/jdd | `781c64e` |
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
.\scripts\run_nqueens_wsl.ps1 --targets all --sizes 8 10 --workers 2 --timeout 100 --output results/upstream/nqueens_metrics.csv
```

The deprecated SoA targets are included only when selected explicitly or with
`--targets all`. Add `--skip-build` after a successful build. Tests can be run with
`python -m unittest discover -s tests -v` using the configured Python environment.

## Measurements

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
  NDD's counters. CUDD, JDD/ZDD, JSylvan and DecisionDiagrams leave this field
  blank. A current table size or peak count is not substituted for allocations.
- `ndd_*` / `bdd_*`: graph-layer splits where available; `bdd_*` denotes label
  nodes for NDD-BCDD and NDD-ZDD as well. Unavailable counters are blank, not zero.
- `status`: `ok` or `timeout`. Timeout rows have blank solution/node counters.
- `upstream_url` and `upstream_revision`: the checked source used for that row;
  archived custom SoA rows leave them blank.

Plots omit unavailable metrics, and display an unavailable message when every
row lacks the requested counter. The CSV does not imply all node representations
have identical sizes or that native and JVM process startup costs are equal.

The Sylvan adapter uses a 2 GiB table budget, and protects intermediate roots
across library calls. JSylvan defaults to the runner's 2 GiB budget. Worker counts
are supplied by `--workers` (0 means library autodetection).

## Attribution

The adapters preserve the N-Queens models from the former benchmark forks and
upstream examples. Prior fork revisions: BuDDy `e35b26a`, Sylvan `060ce4e`, CUDD
`ada57af`, JDD `fa7f7e2`, JSylvan `8444f77`, DecisionDiagrams `4387a75`. NDD drivers
are derived from the pinned XJTU-NetVerify solver examples. Original notices and
applicable license texts are retained under `licenses/`.
