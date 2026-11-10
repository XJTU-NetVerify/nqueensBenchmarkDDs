import csv
import configparser
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_nqueens_benchmarks as runner
import plot_nqueens_results as plots
from benchmarks import build


class MetricsContractTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") and build.executable("NDD").is_file(),
                         "Built maintained NDD adapter on Linux required")
    def test_bitset_field_width_boundary(self):
        for strategy in ("pairwise", "rows"):
            for size in (7, 8):
                with self.subTest(strategy=strategy, size=size):
                    command = build.ndd_command("NDD", size, "--bitset")
                    if strategy == "rows":
                        command.append("--rows")
                    output = subprocess.check_output(command, cwd=ROOT, text=True, timeout=30)
                    self.assertEqual(runner.parse_metrics(output)["solutions"],
                                     runner.EXPECTED_SOLUTIONS[size])

    def test_imported_library_paths_match_submodules(self):
        modules = configparser.ConfigParser()
        modules.read(ROOT / ".gitmodules")
        paths = {modules[section]["path"] for section in modules.sections()}
        primary = {name for name in build.LOCK if name not in ("lace", "jsylvan-native")}
        self.assertEqual(paths, {build.LOCK[name]["path"] for name in primary})
        for name in primary:
            self.assertEqual(build.LOCK[name]["path"], "libraries/" + name)

    def test_ndd_tuning_arguments(self):
        with patch.object(sys, "argv", ["benchmark", "--benchmark", "rows",
                "--ndd-cache-size", "1000000",
                "--ndd-label-cache-size", "100000"]):
            args = runner.parse_args()
        self.assertEqual(args.ndd_cache_size, 1000000)
        self.assertEqual(args.ndd_label_cache_size, 100000)

    @unittest.skipUnless(sys.platform.startswith("linux") and build.executable("NDD").is_file(),
                         "Built maintained NDD adapter on Linux required")
    def test_tuned_ndd_solution_counts(self):
        for implementation in runner.build_implementations("rows"):
            if implementation.name not in ("NDD", "NDD-BCDD", "NDD-ZDD"):
                continue
            for size in range(1, 9):
                with self.subTest(implementation=implementation.name, size=size):
                    command = implementation.command_for(size, 0)
                    command[1:1] = ["-Dbenchmark.ndd.cacheSize=1000000",
                                    "-Dbenchmark.ndd.labelCacheSize=100000"]
                    output = subprocess.check_output(command, cwd=ROOT, text=True, timeout=30)
                    self.assertEqual(runner.parse_metrics(output)["solutions"],
                                     runner.EXPECTED_SOLUTIONS[size])

    def test_row_commands_are_separate_from_original_benchmark(self):
        original = runner.build_implementations()
        rows = runner.build_implementations("rows")
        self.assertEqual([impl.name for impl in original], [impl.name for impl in rows])
        for pairwise, row in zip(original, rows):
            self.assertEqual(row.command_for(8, 2), pairwise.command_for(8, 2) + ["--rows"])
            self.assertNotIn("--rows", pairwise.command_for(8, 2))

    def test_row_output_does_not_overwrite_original_results(self):
        with patch.object(sys, "argv", ["benchmark", "--benchmark", "rows"]):
            self.assertEqual(runner.parse_args().output, ROOT / "results/rows/nqueens_metrics.csv")
        with patch.object(sys, "argv", ["benchmark"]):
            self.assertEqual(runner.parse_args().output, ROOT / "results/pairwise/nqueens_metrics.csv")

    @unittest.skipUnless(sys.platform.startswith("linux") and all(build.executable(name).is_file()
        for name in ("buddy", "sylvan", "cudd", "oxidd", "jdd", "javabdd", "jsylvan",
                     "decisiondiagrams", "NDD", "NDD-original", "NDD-reuse")),
        "Build all adapters on Linux first")
    def test_row_solution_counts_across_all_libraries(self):
        for implementation in runner.build_implementations("rows"):
            for size in range(1, 9):
                with self.subTest(implementation=implementation.name, size=size):
                    output = subprocess.check_output(implementation.command_for(size, 2),
                                                     cwd=ROOT, text=True, timeout=30)
                    metrics = runner.parse_metrics(output)
                    self.assertEqual(metrics["size"], size)
                    self.assertEqual(metrics["solutions"], runner.EXPECTED_SOLUTIONS[size])

    def test_row_process_errors_have_no_solution_or_node_measurements(self):
        implementation = runner.build_implementations("rows")[0]
        result = dict(timed_out=False, returncode=1, elapsed=0.25, max_rss=512,
                      stdout="", stderr="table full", cmd=["benchmark"])
        with patch.object(runner, "execute_with_metrics", return_value=result):
            row = runner.run_implementation(implementation, 8, 2, record_errors=True)
        self.assertEqual(row["status"], "error")
        self.assertIsNone(row["solutions"])
        self.assertIsNone(row["nodes_alive"])
        self.assertEqual(row["time_sec"], 0.25)

    def test_oxidd_registration_and_provenance(self):
        implementation = next(impl for impl in runner.build_implementations() if impl.name == "OxiDD")
        self.assertIn("OxiDD", runner.get_default_targets())
        self.assertEqual(implementation.command_for(8, 2)[-2:], ["8", "2"])
        self.assertEqual(build.provenance("OxiDD")["upstream_revision"],
                         build.LOCK["oxidd"]["revision"])

    @unittest.skipUnless(sys.platform.startswith("linux") and build.executable("oxidd").is_file(),
                         "Built OxiDD adapter on Linux required")
    def test_oxidd_solution_counts(self):
        implementation = next(impl for impl in runner.build_implementations() if impl.name == "OxiDD")
        for size, expected in enumerate([1, 0, 0, 2, 10, 4, 40, 92], start=1):
            with self.subTest(size=size):
                output = subprocess.check_output(implementation.command_for(size, 2), text=True, timeout=30)
                metrics = runner.parse_metrics(output)
                self.assertEqual(metrics["size"], size)
                self.assertEqual(metrics["solutions"], expected)
                self.assertIsNone(metrics["nodes_created"])
                self.assertIsNotNone(metrics["nodes_alive"])

    def test_javabdd_registration_and_provenance(self):
        implementation = next(impl for impl in runner.build_implementations() if impl.name == "JavaBDD")
        self.assertIn("JavaBDD", runner.get_default_targets())
        self.assertEqual(implementation.command_for(8, 2)[-2:],
                         ["benchmark.javabdd.JavaBDDQueens", "8"])
        self.assertEqual(build.provenance("JavaBDD")["upstream_revision"],
                         build.LOCK["JavaBDD"]["revision"])

    @unittest.skipUnless(sys.platform.startswith("linux") and build.executable("javabdd").is_file(),
                         "Built JavaBDD adapter on Linux required")
    def test_javabdd_solution_counts(self):
        implementation = next(impl for impl in runner.build_implementations() if impl.name == "JavaBDD")
        for size, expected in enumerate([1, 0, 0, 2, 10, 4, 40, 92], start=1):
            with self.subTest(size=size):
                output = subprocess.check_output(implementation.command_for(size, 2), text=True, timeout=30)
                metrics = runner.parse_metrics(output)
                self.assertEqual(metrics["size"], size)
                self.assertEqual(metrics["solutions"], expected)
                self.assertIsNone(metrics["nodes_created"])
                self.assertIsNotNone(metrics["nodes_alive"])

    @unittest.skipUnless(sys.platform.startswith("linux") and Path("/usr/bin/time").is_file(), "GNU time required")
    def test_short_process_uses_kernel_peak_rss(self):
        result = runner.execute_with_metrics([sys.executable, "-c",
            "data = bytearray(b'x' * 20_000_000)"], ROOT, None, timeout_sec=10)
        self.assertEqual(result["returncode"], 0)
        self.assertGreater(result["max_rss"], 16_384)

    def test_timeout_terminates_measured_process(self):
        result = runner.execute_with_metrics([sys.executable, "-c", "import time; time.sleep(10)"],
                                              ROOT, None, timeout_sec=0.1)
        self.assertTrue(result["timed_out"])

    def test_unavailable_allocation_counter_is_not_zero(self):
        metrics = runner.parse_metrics("NQUEENS_METRICS n=8 solutions=92 nodes_alive=2451")
        self.assertIsNone(metrics["nodes_created"])
        self.assertIsNone(metrics["bdd_nodes_created"])
        self.assertIsNone(metrics["ndd_nodes_created"])
        self.assertEqual(metrics["bdd_nodes_alive"], 2451)

    def test_zero_is_a_valid_measurement(self):
        metrics = runner.parse_metrics("NQUEENS_METRICS n=2 solutions=0 nodes_created=0 nodes_alive=0")
        self.assertEqual(metrics["nodes_created"], 0)
        self.assertEqual(metrics["solutions"], 0)

    def test_split_ndd_metrics_are_preserved(self):
        metrics = runner.parse_metrics("NQUEENS_METRICS n=8 solutions=92 nodes_alive=330 "
            "ndd_nodes_alive=287 bdd_nodes_alive=43 seconds=0.1")
        self.assertEqual(metrics["ndd_nodes_alive"] + metrics["bdd_nodes_alive"], metrics["nodes_alive"])
        self.assertEqual(metrics["seconds"], 0.1)

    def test_blank_csv_metrics_roundtrip_and_plot(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            csv_path = directory / "metrics.csv"
            with csv_path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["implementation", "size", "time_sec", "max_rss_kb",
                    "nodes_created", "nodes_alive", "solutions"])
                writer.writeheader()
                writer.writerow(dict(implementation="JDD", size=8, time_sec=1, max_rss_kb=100,
                                     nodes_created="", nodes_alive=2451, solutions=92))
            rows = plots.read_rows(csv_path)
            self.assertIsNone(rows[0]["nodes_created"])
            self.assertEqual(rows[0]["ndd_nodes_alive"], 0)
            plots.plot_metric(rows, "nodes_created", "Nodes created", directory)
            self.assertTrue((directory / "nqueens_nodes_created.png").is_file())

    def test_source_guard_rejects_local_code_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(directory), *args], stderr=subprocess.DEVNULL, text=True)
            git("init")
            (directory / "source.txt").write_text("upstream\n")
            git("add", "source.txt")
            git("-c", "user.name=Contract Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")
            revision = git("rev-parse", "HEAD").strip()
            with patch.dict(build.LOCK, {"test": {"path": str(directory), "revision": revision}}):
                self.assertEqual(build.source("test"), directory)
                (directory / "source.txt").write_text("modified\n")
                with self.assertRaisesRegex(RuntimeError, "local edits"):
                    build.source("test")


if __name__ == "__main__":
    unittest.main()
