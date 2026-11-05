import csv
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
