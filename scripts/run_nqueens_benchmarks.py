#!/usr/bin/env python3

import argparse
import csv
import json
import os
import shutil
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
JOBS = max(1, os.cpu_count() or 1)
DEFAULT_SIZES = list(range(8, 14))
DEFAULT_TIMEOUT_SEC = 500
JSYLVAN_MEMORY_MB = 2048
EXPECTED_SOLUTIONS = dict(enumerate([1, 0, 0, 2, 10, 4, 40, 92, 352, 724, 2680, 14200, 73712], start=1))
sys.path.insert(0, str(ROOT))
from benchmarks import build as adapters

EXCLUDED_DEFAULT_TARGETS = {"ZDD"}


class Implementation:
    def __init__(self, name, language, preparer, command_builder, workdir=None, extra_env=None):
        self.name = name
        self.language = language
        self.preparer = preparer
        self.command_builder = command_builder
        self.workdir = workdir or ROOT
        self.extra_env = extra_env or {}

    def ensure_ready(self):
        if self.preparer:
            self.preparer()

    def command_for(self, size, workers):
        return self.command_builder(size, workers)

    def base_env(self):
        env = os.environ.copy()
        env.update(self.extra_env)
        return env


def run(cmd, cwd=ROOT, env=None):
    cmd = list(cmd)
    cmd[0] = shutil.which(str(cmd[0])) or cmd[0]
    print(f"[build] {cwd.relative_to(ROOT) if cwd != ROOT else '.'}$ {' '.join(shlex.quote(str(c)) for c in cmd)}")
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def ensure_buddy():
    adapters.prepare("buddy", run, JOBS)


def ensure_sylvan():
    adapters.prepare("sylvan", run, JOBS)


def ensure_cudd():
    adapters.prepare("cudd", run, JOBS)


def ensure_oxidd():
    adapters.prepare("oxidd", run, JOBS)


def ensure_jdd():
    adapters.prepare("jdd", run, JOBS)


def ensure_javabdd():
    adapters.prepare("javabdd", run, JOBS)


def ensure_jsylvan():
    adapters.prepare("jsylvan", run, JOBS)


def ensure_ndd_original():
    adapters.prepare("NDD-original", run, JOBS)


def ensure_ndd():
    adapters.prepare("NDD", run, JOBS)

def ensure_ndd_reuse():
    adapters.prepare("NDD-reuse", run, JOBS)


def ensure_decisiondiagrams():
    adapters.prepare("decisiondiagrams", run, JOBS)


TIMEOUT_SENTINEL_METRICS = {
    "solutions": None,
    "nodes_created": None,
    "nodes_alive": None,
    "ndd_nodes_created": None,
    "ndd_nodes_alive": None,
    "bdd_nodes_created": None,
    "bdd_nodes_alive": None,
}

def _poll_rss(pid, interval, result):
    """Background thread: poll RSS of pid and its children, record peak (KB)."""
    peak = 0
    try:
        proc = psutil.Process(pid)
        while True:
            try:
                rss = proc.memory_info().rss
                for child in proc.children(recursive=True):
                    try:
                        rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if rss > peak:
                    peak = rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(interval)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    result["peak_rss_kb"] = peak // 1024


def execute_with_metrics(cmd, cwd, env, timeout_sec=DEFAULT_TIMEOUT_SEC):
    """Execute command and measure time/memory, returning a timeout result instead of retrying."""
    # GNU time reports the kernel high-water mark even for millisecond native runs.
    # Polling remains the fallback for timeouts and platforms without GNU time.
    resource_prefix = "NQUEENS_RESOURCE max_rss_kb="
    use_gnu_time = sys.platform.startswith("linux") and Path("/usr/bin/time").is_file()
    measured_cmd = ["/usr/bin/time", "-f", resource_prefix + "%M", "--", *cmd] if use_gnu_time else cmd
    start_time = time.perf_counter()
    proc = subprocess.Popen(
        measured_cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name == "posix",
    )

    rss_result = {}
    poller = threading.Thread(target=_poll_rss, args=(proc.pid, 0.05, rss_result), daemon=True)
    poller.start()

    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
        elapsed_time = time.perf_counter() - start_time
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        stdout, stderr = proc.communicate()
        elapsed_time = timeout_sec
        timed_out = True

    poller.join(timeout=1)
    max_rss = rss_result.get("peak_rss_kb", 0)
    if use_gnu_time and not timed_out:
        for line in stderr.splitlines():
            if line.startswith(resource_prefix):
                max_rss = int(line[len(resource_prefix):])

    return {
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed": elapsed_time,
        "max_rss": max_rss,
        "cmd": cmd,
        "timed_out": timed_out,
    }


def parse_metrics(stdout):
    metric_line = None
    for line in stdout.strip().splitlines():
        if "NQUEENS_METRICS" in line:
            metric_line = line.strip()
    if not metric_line:
        raise RuntimeError("Failed to parse NQUEENS_METRICS from program output")

    parts = {}
    for token in metric_line.split():
        if token == "NQUEENS_METRICS" or "=" not in token:
            continue
        key, value = token.split("=", 1)
        parts[key] = value

    size = int(parts["n"])
    solutions = float(parts["solutions"])
    # An absent upstream counter is unavailable, rather than zero.
    def optional_int(key, fallback=None):
        return int(parts[key]) if key in parts else fallback
    nodes_created = optional_int("nodes_created")
    nodes_alive = optional_int("nodes_alive")
    ndd_nodes_created = optional_int("ndd_nodes_created", 0 if nodes_created is not None else None)
    ndd_nodes_alive = optional_int("ndd_nodes_alive", 0 if nodes_alive is not None else None)
    bdd_nodes_created = optional_int("bdd_nodes_created", nodes_created)
    bdd_nodes_alive = optional_int("bdd_nodes_alive", nodes_alive)
    seconds = float(parts["seconds"]) if "seconds" in parts else None
    return {
        "size": size,
        "solutions": solutions,
        "nodes_created": nodes_created,
        "nodes_alive": nodes_alive,
        "ndd_nodes_created": ndd_nodes_created,
        "ndd_nodes_alive": ndd_nodes_alive,
        "bdd_nodes_created": bdd_nodes_created,
        "bdd_nodes_alive": bdd_nodes_alive,
        "seconds": seconds,
    }


def run_implementation(impl, size, workers, timeout_sec=DEFAULT_TIMEOUT_SEC, record_errors=False):
    cmd = impl.command_for(size, workers)
    env = impl.base_env()
    result = execute_with_metrics(cmd, cwd=impl.workdir, env=env, timeout_sec=timeout_sec)
    if result["timed_out"] or (record_errors and result["returncode"] != 0):
        status = "timeout" if result["timed_out"] else "error"
        duration = timeout_sec if result["timed_out"] else result["elapsed"]
        print(f"[{status}] {impl.name:10s} N={size:2d} time={duration:7.3f}s rss={result['max_rss']:>8d}KB")
        if status == "error":
            print(result["stderr"], file=sys.stderr)
        return {
            **adapters.provenance(impl.name),
            "status": status,
            "implementation": impl.name,
            "language": impl.language,
            "size": size,
            "time_sec": duration,
            "solver_time_sec": None,
            "max_rss_kb": result["max_rss"],
            "nodes_created": TIMEOUT_SENTINEL_METRICS["nodes_created"],
            "nodes_alive": TIMEOUT_SENTINEL_METRICS["nodes_alive"],
            "ndd_nodes_created": TIMEOUT_SENTINEL_METRICS["ndd_nodes_created"],
            "ndd_nodes_alive": TIMEOUT_SENTINEL_METRICS["ndd_nodes_alive"],
            "bdd_nodes_created": TIMEOUT_SENTINEL_METRICS["bdd_nodes_created"],
            "bdd_nodes_alive": TIMEOUT_SENTINEL_METRICS["bdd_nodes_alive"],
            "solutions": TIMEOUT_SENTINEL_METRICS["solutions"],
        }
    if result["returncode"] != 0:
        raise subprocess.CalledProcessError(
            result["returncode"],
            result["cmd"],
            output=result["stdout"],
            stderr=result["stderr"],
        )
    metrics = parse_metrics(result["stdout"])
    if metrics["size"] != size:
        raise RuntimeError(f"Implementation {impl.name} reported size {metrics['size']} but expected {size}")
    if size in EXPECTED_SOLUTIONS and metrics["solutions"] != EXPECTED_SOLUTIONS[size]:
        raise RuntimeError(f"{impl.name} N={size}: expected {EXPECTED_SOLUTIONS[size]} solutions, got {metrics['solutions']}")
    time_sec = result["elapsed"]
    max_rss = result["max_rss"]
    print(f"[run] {impl.name:10s} N={size:2d} time={time_sec:7.3f}s rss={max_rss:>8d}KB "
          f"created={metrics['nodes_created']} alive={metrics['nodes_alive']} "
          f"(bdd={metrics['bdd_nodes_created']}/{metrics['bdd_nodes_alive']} "
          f"ndd={metrics['ndd_nodes_created']}/{metrics['ndd_nodes_alive']})")
    return {
        **adapters.provenance(impl.name),
        "status": "ok",
        "implementation": impl.name,
        "language": impl.language,
        "size": size,
        "time_sec": time_sec,
        "solver_time_sec": metrics["seconds"],
        "max_rss_kb": max_rss,
        "nodes_created": metrics["nodes_created"],
        "nodes_alive": metrics["nodes_alive"],
        "ndd_nodes_created": metrics["ndd_nodes_created"],
        "ndd_nodes_alive": metrics["ndd_nodes_alive"],
        "bdd_nodes_created": metrics["bdd_nodes_created"],
        "bdd_nodes_alive": metrics["bdd_nodes_alive"],
        "solutions": metrics["solutions"],
    }


def write_results(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "benchmark",
        "implementation",
        "upstream_url",
        "upstream_revision",
        "status",
        "language",
        "size",
        "time_sec",
        "solver_time_sec",
        "max_rss_kb",
        "nodes_created",
        "nodes_alive",
        "ndd_nodes_created",
        "ndd_nodes_alive",
        "bdd_nodes_created",
        "bdd_nodes_alive",
        "solutions",
    ]
    with output_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path
    print(f"[done] Results saved to {display_path}")


def plot_results(output_path):
    plot_script = ROOT / "scripts" / "plot_nqueens_results.py"
    print(f"[plot] Generating plots from {output_path}")
    subprocess.run(
        [
            sys.executable,
            str(plot_script),
            "--input",
            str(output_path),
            "--output",
            str(output_path.parent),
        ],
        cwd=ROOT,
        check=True,
    )


def parse_args():
    default_targets = get_default_targets()
    parser = argparse.ArgumentParser(
        description="Run N-Queens benchmarks across multiple BDD implementations.",
    )
    parser.add_argument("--benchmark", choices=("pairwise", "rows"), default="pairwise",
                        help="N-Queens construction: original pairwise constraints or external-suite row construction")
    parser.add_argument("--ndd-cache-size", type=int, default=10000,
                        help="Maintained NDD operation cache entries (default: 10000)")
    parser.add_argument("--ndd-label-cache-size", type=int, default=10000,
                        help="Maintained NDD label operation cache entries (default: 10000)")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=DEFAULT_SIZES,
        help="Board sizes to benchmark (default: 8 9 10 11 12 13)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Worker threads for Sylvan-based implementations and OxiDD (0 = autodetect, default: 0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help="Per-run timeout in seconds (default: 500)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV path (default: results/<benchmark>/nqueens_metrics.csv)",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=default_targets,
        help=f"Which implementations to run (default: {' '.join(default_targets)}). Example: --targets BuDDy Sylvan JSylvan",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Run existing build artifacts without rebuilding implementations",
    )
    args = parser.parse_args()
    if args.ndd_cache_size <= 0 or args.ndd_label_cache_size <= 0:
        parser.error("NDD cache sizes must be positive")
    if args.output is None:
        args.output = RESULTS_DIR / args.benchmark / "nqueens_metrics.csv"
    return args


def build_implementations(benchmark="pairwise"):
    if benchmark not in ("pairwise", "rows"):
        raise ValueError(f"Unknown benchmark: {benchmark}")
    def ndd(name, prepare, mode=None, source="NDD"):
        return Implementation(name, "Java", prepare,
                              lambda size, _: adapters.ndd_command(source, size, mode))

    implementations = [
        Implementation("BuDDy", "C", ensure_buddy,
                       lambda size, _: [str(adapters.executable("buddy")), str(size)]),
        Implementation("Sylvan", "C", ensure_sylvan,
                       lambda size, workers: [str(adapters.executable("sylvan")), "-w", str(workers), str(size)]),
        Implementation("CUDD", "C", ensure_cudd,
                       lambda size, _: [str(adapters.executable("cudd")), str(size)]),
        Implementation("OxiDD", "Rust", ensure_oxidd,
                       lambda size, workers: [str(adapters.executable("oxidd")), str(size), str(workers)]),
        Implementation("JDD", "Java", ensure_jdd,
                       lambda size, _: ["java", "-cp", str(adapters.BUILD / "jdd/classes"), "benchmark.jdd.BDDQueens", str(size)]),
        Implementation("JavaBDD", "Java", ensure_javabdd,
                       lambda size, _: ["java", "-cp", str(adapters.BUILD / "javabdd/classes"),
                                        "benchmark.javabdd.JavaBDDQueens", str(size)]),
        Implementation("ZDD", "Java", ensure_jdd,
                       lambda size, _: ["java", "-cp", str(adapters.BUILD / "jdd/classes"), "benchmark.jdd.ZDDQueens", str(size)]),
        Implementation("JSylvan", "Java", ensure_jsylvan,
                       lambda size, workers: ["java", "-cp", str(adapters.executable("jsylvan")),
                           "benchmark.jsylvan.JSylvanNQueens", "-w", str(workers),
                           "--memory-mb", str(JSYLVAN_MEMORY_MB), str(size)]),
        Implementation("DD-BDD", "C#", ensure_decisiondiagrams,
                       lambda size, _: ["dotnet", str(adapters.executable("decisiondiagrams")), str(size), "--use-bdd"]),
        Implementation("DD-CBDD", "C#", ensure_decisiondiagrams,
                       lambda size, _: ["dotnet", str(adapters.executable("decisiondiagrams")), str(size)]),
        ndd("NDD-original", ensure_ndd_original, source="NDD-original"),
        ndd("NDD", ensure_ndd),
        ndd("NDD-BCDD", ensure_ndd, "--bcdd"),
        ndd("NDD-ZDD", ensure_ndd, "--zdd"),
        ndd("NDD-reuse", ensure_ndd_reuse, source="NDD-reuse"),
    ]
    if benchmark == "rows":
        for impl in implementations:
            builder = impl.command_builder
            impl.command_builder = lambda size, workers, builder=builder: [*builder(size, workers), "--rows"]
    return implementations


def get_default_targets():
    return [impl.name for impl in build_implementations() if impl.name not in EXCLUDED_DEFAULT_TARGETS]


def main():
    args = parse_args()
    available_impls = build_implementations(args.benchmark)
    for impl in available_impls:
        if impl.name in ("NDD", "NDD-BCDD", "NDD-ZDD"):
            builder = impl.command_builder
            impl.command_builder = lambda size, workers, builder=builder: [
                "java", f"-Dbenchmark.ndd.cacheSize={args.ndd_cache_size}",
                f"-Dbenchmark.ndd.labelCacheSize={args.ndd_label_cache_size}",
                *builder(size, workers)[1:]]
    impl_map = {impl.name.lower(): impl for impl in available_impls}
    requested = [t.lower() for t in args.targets]
    if requested == ["all"]:
        selected_impls = available_impls
    else:
        missing = [t for t in requested if t not in impl_map]
        if missing:
            raise ValueError(f"Unknown implementations requested: {', '.join(missing)}. Available: {', '.join(impl_map.keys())}")
        seen = set()
        selected_impls = []
        for name in requested:
            if name in seen:
                continue
            seen.add(name)
            selected_impls.append(impl_map[name])

    if not args.skip_build:
        prepared = set()
        for impl in selected_impls:
            if impl.preparer not in prepared:
                impl.ensure_ready()
                prepared.add(impl.preparer)

    # Verify even --skip-build runs against the declared upstream sources.
    sources = {adapters.TARGET_SOURCES[impl.name] for impl in selected_impls
               if impl.name in adapters.TARGET_SOURCES}
    if "sylvan" in sources:
        sources.add("lace")
    if "jsylvan" in sources:
        sources.add("jsylvan-native")
    for name in sorted(sources):
        adapters.source(name)

    rows = []
    if args.benchmark == "rows":
        metadata = json.loads((ROOT / "benchmarks/common/row-construction.json").read_text())
        metadata.update(sizes=args.sizes, workers=args.workers, timeout_sec=args.timeout,
                        ndd_cache_size=args.ndd_cache_size, ndd_label_cache_size=args.ndd_label_cache_size,
                        targets=[impl.name for impl in selected_impls])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        (args.output.parent / "benchmark.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for size in args.sizes:
        for impl in selected_impls:
            result = run_implementation(impl, size, args.workers, timeout_sec=args.timeout,
                                        record_errors=args.benchmark == "rows")
            rows.append({"benchmark": args.benchmark, **result})
        # Preserve completed sizes if a later run fails or is interrupted.
        write_results(rows, args.output)

    plot_results(args.output)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"[error] Command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(exc.returncode)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
