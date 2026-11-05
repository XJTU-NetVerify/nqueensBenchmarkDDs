# N-Queens benchmarks for BDD and NDD libraries

Compare N-Queens construction across native C/C++, Java, and .NET decision
diagram libraries. Each run records elapsed time, peak memory, available node
counters, and the solution count.

Primary libraries are Git submodules pinned to upstream commits. Benchmark
adapters live in [`benchmarks/`](benchmarks/README.md), separate from upstream
source. Exact source URLs and revisions, including build dependencies, are
recorded in [`benchmarks/upstream-lock.json`](benchmarks/upstream-lock.json).

## Setup

Clone the repository with its submodules:

```bash
git clone --recurse-submodules https://github.com/XJTU-NetVerify/nqueensBenchmarkDDs.git
cd nqueensBenchmarkDDs
```

For an existing checkout:

```bash
git -c core.autocrlf=false submodule update --init --recursive
```

Native targets require Linux build tools. On Windows, use Ubuntu in WSL and
install the dependencies inside Ubuntu:

```bash
sudo apt update
sudo apt install git build-essential cmake pkg-config libgmp-dev time openjdk-17-jdk maven python3-venv python3-matplotlib python3-psutil
```

The DecisionDiagrams adapter targets `net6.0`. Install the .NET 6 SDK and runtime
in the same Linux environment, and check that `dotnet --info` finds them.

The PowerShell launcher uses the Ubuntu distribution named `Ubuntu`, selects
Java 17 from `/usr/lib/jvm/java-17-openjdk-amd64`, and uses Ubuntu's Python
packages. For a separate Python environment, install the dependencies from
[`requirements.txt`](requirements.txt):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

From PowerShell at the repository root, reproduce the retained benchmark:

```powershell
.\scripts\run_nqueens_wsl.ps1 --workers 2 --output results/nqueens_metrics.csv
```

From Linux, with Java 17 and the other tools on `PATH`:

```bash
python3 scripts/run_nqueens_benchmarks.py --workers 2 --output results/nqueens_metrics.csv
```

Use `.venv/bin/python` in place of `python3` if using the virtual environment.
The runner builds selected implementations, runs them sequentially, writes the
CSV, and generates six plots in the CSV's directory. An output path under
`results/` replaces the corresponding retained CSV and plots.

| Option | Default | Purpose |
| --- | --- | --- |
| `--sizes` | `8 9 10 11 12 13` | Board sizes to run |
| `--targets` | 12 targets below | Select target names; `all` adds standalone ZDD |
| `--workers` | `0` | Sylvan/JSylvan workers; 0 enables autodetection |
| `--timeout` | `500` | Timeout in seconds for each implementation and size |
| `--output` | `results/nqueens_metrics.csv` | CSV path; plots go beside it |
| `--skip-build` | Off | Reuse existing build artifacts |

For a quick run that preserves the retained results:

```powershell
.\scripts\run_nqueens_wsl.ps1 --sizes 8 10 --workers 2 --output .bench-build/experiments/smoke/nqueens_metrics.csv
```

To compare the three maintained NDD label modes at N=13:

```powershell
.\scripts\run_nqueens_wsl.ps1 --targets NDD NDD-BCDD NDD-ZDD --sizes 13 --workers 2 --timeout 100 --output .bench-build/experiments/ndd/nqueens_metrics.csv
```

Add `--skip-build` after a successful build. Builds and runs verify the pinned
upstream revisions and reject edits to tracked upstream source files. Adapter
builds and additional pinned Lace/Sylvan dependencies are stored under ignored
`.bench-build/` directories; Maven and .NET also create normal library build
outputs.

## Implementations

All targets below run by default except standalone `ZDD`. `--targets all` runs
all 13 targets. NDD targets appear last in the default run order.

| Target | Source directory | Implementation |
| --- | --- | --- |
| `BuDDy` | `BuDDy/` | Native BDD |
| `Sylvan` | `sylvan/` | Parallel native BDD |
| `CUDD` | `cudd/` | Native BDD |
| `JDD` | `jdd/` | Java BDD |
| `ZDD` | `jdd/` | Java ZDD; explicit selection only |
| `JSylvan` | `jsylvan/` | Java binding to native Sylvan |
| `DD-BDD` | `DecisionDiagrams/` | .NET BDD |
| `DD-CBDD` | `DecisionDiagrams/` | .NET chain-reduced BDD |
| `NDD-original` | `NDD-original/` | Object-based NDD from upstream `ndd-original` |
| `NDD` | `NDD/` | Maintained NDD with BDD labels |
| `NDD-BCDD` | `NDD/` | Maintained NDD with `COMPLEMENTED_BDD` labels |
| `NDD-ZDD` | `NDD/` | Maintained NDD with ZDD labels |
| `NDD-reuse` | `NDD-reuse/` | Object-based NDD from upstream `reuse` |

All nine source directories are submodules. The three maintained NDD modes
share one library build. JSylvan uses pinned Sylvan 1.4.1; standalone Sylvan
uses 1.9.1. See the [adapter documentation](benchmarks/README.md) for provenance,
build details, and counter APIs.

## Current results

[`results/nqueens_metrics.csv`](results/nqueens_metrics.csv) contains the retained
N=8 through N=13 run across the 12 default targets, with two Sylvan workers and
a 500-second timeout. Of 72 runs, 71 returned the expected solution count;
BuDDy timed out at N=13. Every completed N=13 run returned 73,712 solutions.
These are single-run observations, not averages over repeated trials.

`results/` retains only this CSV and its six plots:

- Execution time: [linear](results/nqueens_time_sec.png) / [log](results/nqueens_time_sec_log.png)
- Peak memory: [linear](results/nqueens_max_rss_kb.png) / [log](results/nqueens_max_rss_kb_log.png)
- [Nodes created](results/nqueens_nodes_created.png)
- [Final node count](results/nqueens_nodes_alive.png)

![Execution time for N=8 through N=13](results/nqueens_time_sec.png)

![Peak memory for N=8 through N=13](results/nqueens_max_rss_kb.png)

To regenerate plots without rerunning the benchmark:

```bash
python3 scripts/plot_nqueens_results.py --input results/nqueens_metrics.csv --output results
```

## Measurements

- `time_sec` measures process wall time, including runtime startup and metrics
  output. `solver_time_sec` records internal solve time where available.
- `max_rss_kb` is kernel-reported peak RSS from GNU time on Linux. Timeouts and
  other platforms use sampled process-tree RSS, which can miss brief peaks.
- `nodes_created` reports lifetime allocations where upstream provides a counter.
  Missing counters are blank; current table sizes are not substituted.
- `nodes_alive` follows each library's final graph-count API. Counting conventions
  differ, so these values are not interchangeable measures of memory.
- `ndd_*` and `bdd_*` split graph layers when available. For NDD, `bdd_*` includes
  the selected label backend, including complemented BDD and ZDD labels.
- `status` distinguishes completed runs (`ok`) from timeouts (`timeout`). Timeout
  solution and node fields are blank; the timeout duration is not a solve time.
- `upstream_url` and `upstream_revision` identify the pinned source for each row.

See [measurement details](benchmarks/README.md#measurements) and the
[implementation comparison](docs/bdd-implementation-comparison.md) for context.

## Validation and archived code

Run the benchmark contract tests in the configured Python environment:

```bash
python3 -m unittest discover -s tests -v
```

The historical SoA project remains under [`deprecated/NDD-SoA/`](deprecated/NDD-SoA/).
Its targets have been removed from the runner, including `--targets all`.
`NDD` and `NDD-BCDD` replace the corresponding SoA variants. The archived
finite-domain ZDD experiment has no direct equivalent in the maintained Boolean
ZDD label mode. See [`deprecated/README.md`](deprecated/README.md).
