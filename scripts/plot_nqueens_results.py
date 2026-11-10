#!/usr/bin/env python3

"""
Simple visualization helper for the aggregated CSV produced by run_nqueens_benchmarks.py

Usage:
    python scripts/plot_nqueens_results.py --input results/nqueens_metrics.csv --output results
"""

import argparse
import csv
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
except ImportError as exc:
    raise SystemExit("matplotlib is required for plotting. Install it via `pip install matplotlib`.") from exc


LINE_MARKERS = ["o", "+", "*", "s", "^", "v", "D", "x", "p",
                {"marker": "o", "markerfacecolor": "none"}, ">", "<", "h", "d", "H"]
NDD_COLORS = {
    "NDD": "#D62728",
    "NDD-BCDD": "#E66101",
    "NDD-ZDD": "#C51B7D",
    "NDD-original": "#7B3294",
    "NDD-reuse": "#A63603",
}
OTHER_COLOR = "#A8BAC4"
DEFAULT_MIN_SIZE = 8
DEFAULT_MAX_SIZE = 13


def read_rows(csv_path):
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]
    for row in rows:
        row["size"] = int(row["size"])
        row["time_sec"] = float(row["time_sec"])
        row["max_rss_kb"] = int(row["max_rss_kb"])
        for metric in ("nodes_created", "nodes_alive"):
            value = row.get(metric)
            row[metric] = int(value) if value not in (None, "") else None
            for prefix, fallback in (("ndd_", 0 if row[metric] is not None else None),
                                     ("bdd_", row[metric])):
                key = prefix + metric
                value = row.get(key, fallback)
                row[key] = int(value) if value not in (None, "") else None
        row["solutions"] = float(row["solutions"]) if row.get("solutions") else None
    return rows


def filter_rows(rows, min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE):
    return [row for row in rows if min_size <= row["size"] <= max_size]


def get_implementation_markers(implementations):
    return {
        impl: LINE_MARKERS[index % len(LINE_MARKERS)]
        for index, impl in enumerate(implementations)
    }


def plot_line_metric(rows, metric, implementations):
    colors = get_implementation_colors(implementations)
    markers = get_implementation_markers(implementations)
    for impl in implementations:
        is_ndd = impl.startswith("NDD")
        subset = sorted((r for r in rows if r["implementation"] == impl), key=lambda r: r["size"])
        marker_spec = markers[impl]
        marker_extra = marker_spec if isinstance(marker_spec, dict) else {"marker": marker_spec}
        plot_kwargs = {
            **marker_extra,
            "label": impl,
            "color": colors[impl],
            "linestyle": "-" if is_ndd else ":",
            "linewidth": 2.0 if is_ndd else 1.6,
            "zorder": 3 if is_ndd else 2,
            "markersize": 9,
            "markerfacecolor": "none",
            "markeredgewidth": 1.3,
        }
        plt.plot([r["size"] for r in subset], [r[metric] for r in subset], **plot_kwargs)


def get_implementation_colors(implementations):
    colors = {}
    for impl in implementations:
        if impl.startswith("NDD"):
            colors[impl] = NDD_COLORS.get(impl, NDD_COLORS["NDD"])
        else:
            colors[impl] = OTHER_COLOR
    return colors


def plot_bar_metric(rows, metric, implementations, sizes):
    width = 0.8 / max(len(implementations), 1)
    colors = get_implementation_colors(implementations)
    labeled_implementations = set()
    for size in sizes:
        size_rows = [
            next((r for r in rows if r["size"] == size and r["implementation"] == impl), None)
            for impl in implementations
        ]
        size_rows = [row for row in size_rows if row is not None]
        size_rows.sort(key=lambda row: (row[metric], row["implementation"]))
        count = len(size_rows)
        positions = [
            size - (count * width) / 2 + width / 2 + index * width
            for index in range(count)
        ]
        for row, position in zip(size_rows, positions):
            impl = row["implementation"]
            label = impl if impl not in labeled_implementations else "_nolegend_"
            if metric in ("nodes_created", "nodes_alive"):
                bdd_metric = f"bdd_{metric}"
                ndd_metric = f"ndd_{metric}"
                base_color = colors[impl]
                top_color = lighten_color(base_color, 0.45)
                plt.bar(
                    [position],
                    [row[bdd_metric]],
                    width=width,
                    label=label,
                    color=base_color,
                )
                plt.bar(
                    [position],
                    [row[ndd_metric]],
                    width=width,
                    bottom=[row[bdd_metric]],
                    label="_nolegend_",
                    color=top_color,
                )
            else:
                plt.bar(
                    [position],
                    [row[metric]],
                    width=width,
                    label=label,
                    color=colors[impl],
                )
            labeled_implementations.add(impl)


def lighten_color(color, amount):
    red, green, blue = to_rgb(color)
    return (
        red + (1.0 - red) * amount,
        green + (1.0 - green) * amount,
        blue + (1.0 - blue) * amount,
    )


def plot_metric(rows, metric, ylabel, output_dir, use_log_scale=False):
    rows = [r for r in filter_rows(rows) if r[metric] is not None and r.get("status") != "error"]
    plt.rcParams.update({
        "font.size": 13,
        "axes.titlesize": 17,
        "axes.labelsize": 15,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 12,
    })
    plt.figure(figsize=(10, 5))
    implementations = sorted(set(r["implementation"] for r in rows))
    sizes = sorted(set(r["size"] for r in rows))
    if metric in ("time_sec", "max_rss_kb"):
        plot_line_metric(rows, metric, implementations)
    else:
        plot_bar_metric(rows, metric, implementations, sizes)
    plt.xticks(sizes)
    if use_log_scale and all(r[metric] > 0 for r in rows):
        plt.yscale("log")
    plt.xlabel("Board size (N)")
    plt.ylabel(ylabel)
    title = "N-Queens row construction" if rows and all(r.get("benchmark") == "rows" for r in rows) else "N-Queens"
    plt.title(f"{title} {ylabel}")
    plt.grid(True, linestyle="--", alpha=0.4)
    if rows:
        plt.legend(ncol=2)
    else:
        plt.text(0.5, 0.5, "Metric unavailable from upstream APIs",
                 ha="center", va="center", transform=plt.gca().transAxes)
    suffix = "_log" if use_log_scale else ""
    output_path = output_dir / f"nqueens_{metric}{suffix}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"[plot] Saved {output_path}")


def plot_all_metrics(rows, output_dir):
    metrics = [
        ("time_sec", "Runtime (s)"),
        ("max_rss_kb", "Peak RSS (KB)"),
    ]
    for metric, ylabel in metrics:
        plot_metric(rows, metric, ylabel, output_dir, use_log_scale=True)


def main():
    parser = argparse.ArgumentParser(description="Plot N-Queens benchmark metrics.")
    parser.add_argument("--input", type=Path, required=True, help="CSV file produced by run_nqueens_benchmarks.py")
    parser.add_argument("--output", type=Path, default=Path("results"), help="Directory to store plots (default: results)")
    args = parser.parse_args()

    rows = read_rows(args.input)
    args.output.mkdir(parents=True, exist_ok=True)

    plot_all_metrics(rows, args.output)


if __name__ == "__main__":
    main()
