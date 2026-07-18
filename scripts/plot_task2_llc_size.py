#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path(
    "results/csv/task2_llc_size_single_results.csv"
)
SINGLE_SUMMARY = Path(
    "results/csv/task2_llc_size_single_summary.csv"
)
FOUR_PER_CORE = Path(
    "results/csv/task2_llc_size_four_core_per_core_results.csv"
)
FOUR_SUMMARY = Path(
    "results/csv/task2_llc_size_four_core_summary.csv"
)

SINGLE_OUTPUT = Path(
    "results/graphs/task2/llc_size/single"
)
FOUR_OUTPUT = Path(
    "results/graphs/task2/llc_size/four_core"
)

SIZE_ORDER = [1, 2, 4, 8]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV file: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No data rows found in {path}")

    return rows


def prepare_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

    for old_graph in path.glob("*.png"):
        old_graph.unlink()


def annotate_bars(ax, bars, decimals: int = 3) -> None:
    for bar in bars:
        value = bar.get_height()

        ax.annotate(
            f"{value:.{decimals}f}",
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def save_bar(
    output_dir: Path,
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    filename: str,
    decimals: int = 3,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, values)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)

    annotate_bars(ax, bars, decimals)

    fig.tight_layout()
    fig.savefig(
        output_dir / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def save_grouped_bar(
    output_dir: Path,
    categories: list[str],
    series: dict[str, list[float]],
    title: str,
    ylabel: str,
    filename: str,
    rotation: int = 20,
) -> None:
    fig, ax = plt.subplots(figsize=(14, 7))

    names = list(series.keys())
    width = 0.8 / len(names)
    x_positions = list(range(len(categories)))

    for index, name in enumerate(names):
        offset = (index - (len(names) - 1) / 2) * width
        positions = [x + offset for x in x_positions]

        ax.bar(
            positions,
            series[name],
            width,
            label=name,
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(
        categories,
        rotation=rotation,
        ha="right" if rotation else "center",
    )
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(
        output_dir / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def short_trace(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def size_labels() -> list[str]:
    return [f"{size} MB" for size in SIZE_ORDER]


def summary_index(
    rows: list[dict[str, str]],
) -> dict[int, dict[str, str]]:
    indexed = {
        int(row["llc_size_mb"]): row
        for row in rows
    }

    missing = [
        size for size in SIZE_ORDER
        if size not in indexed
    ]

    if missing:
        fail(f"Missing LLC sizes from summary: {missing}")

    return indexed


def generate_single_core_graphs() -> None:
    detail_rows = load_csv(SINGLE_DETAIL)
    summary_rows = load_csv(SINGLE_SUMMARY)

    prepare_directory(SINGLE_OUTPUT)

    summary = summary_index(summary_rows)
    labels = size_labels()

    summary_specs = [
        (
            "average_ipc",
            "Single-Core Average Cumulative IPC vs LLC Size",
            "Average IPC",
            "average_ipc.png",
            4,
        ),
        (
            "geomean_ipc",
            "Single-Core Geometric-Mean IPC vs LLC Size",
            "Geometric-mean IPC",
            "geomean_ipc.png",
            4,
        ),
        (
            "weighted_l1_combined_miss_percent",
            "Single-Core L1 Miss Percentage vs LLC Size",
            "L1 miss (%)",
            "l1_miss_percent.png",
            4,
        ),
        (
            "weighted_l2_miss_percent",
            "Single-Core L2 Miss Percentage vs LLC Size",
            "L2 miss (%)",
            "l2_miss_percent.png",
            4,
        ),
        (
            "weighted_llc_miss_percent",
            "Single-Core LLC Miss Percentage vs LLC Size",
            "LLC miss (%)",
            "llc_miss_percent.png",
            4,
        ),
        (
            "weighted_llc_hit_rate_percent",
            "Single-Core LLC Hit Rate vs LLC Size",
            "LLC hit rate (%)",
            "llc_hit_rate.png",
            4,
        ),
        (
            "total_llc_write_requests",
            "Single-Core Total LLC Writes vs LLC Size",
            "Total LLC write requests",
            "total_llc_writes.png",
            0,
        ),
        (
            "average_real_seconds",
            "Single-Core Average Simulation Time vs LLC Size",
            "Execution time (seconds)",
            "execution_time.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in summary_specs:
        save_bar(
            SINGLE_OUTPUT,
            labels,
            [float(summary[size][field]) for size in SIZE_ORDER],
            title,
            ylabel,
            filename,
            decimals,
        )

    traces = sorted({
        short_trace(row["trace"])
        for row in detail_rows
    })

    indexed: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        indexed[short_trace(row["trace"])][
            int(row["llc_size_mb"])
        ] = row

    for trace in traces:
        missing = [
            size for size in SIZE_ORDER
            if size not in indexed[trace]
        ]

        if missing:
            fail(f"Trace {trace} missing LLC sizes: {missing}")

    save_grouped_bar(
        SINGLE_OUTPUT,
        traces,
        {
            f"{size} MB": [
                float(indexed[trace][size]["ipc"])
                for trace in traces
            ]
            for size in SIZE_ORDER
        },
        "Single-Core Cumulative IPC by Trace and LLC Size",
        "IPC",
        "per_trace_ipc.png",
    )


def generate_four_core_graphs() -> None:
    per_core_rows = load_csv(FOUR_PER_CORE)
    summary_rows = load_csv(FOUR_SUMMARY)

    prepare_directory(FOUR_OUTPUT)

    summary = summary_index(summary_rows)
    labels = size_labels()

    summary_specs = [
        (
            "sum_ipc",
            "Four-Core Aggregate Cumulative IPC vs LLC Size",
            "Sum IPC",
            "sum_ipc.png",
            4,
        ),
        (
            "geomean_ipc",
            "Four-Core Geometric-Mean IPC vs LLC Size",
            "Geometric-mean IPC",
            "geomean_ipc.png",
            4,
        ),
        (
            "weighted_l1_combined_miss_percent",
            "Four-Core L1 Miss Percentage vs LLC Size",
            "L1 miss (%)",
            "l1_miss_percent.png",
            4,
        ),
        (
            "weighted_l2_miss_percent",
            "Four-Core L2 Miss Percentage vs LLC Size",
            "L2 miss (%)",
            "l2_miss_percent.png",
            4,
        ),
        (
            "llc_miss_percent",
            "Four-Core Shared LLC Miss Percentage vs LLC Size",
            "LLC miss (%)",
            "llc_miss_percent.png",
            4,
        ),
        (
            "llc_hit_rate_percent",
            "Four-Core Shared LLC Hit Rate vs LLC Size",
            "LLC hit rate (%)",
            "llc_hit_rate.png",
            4,
        ),
        (
            "llc_total_write_requests",
            "Four-Core Total LLC Writes vs LLC Size",
            "Total LLC write requests",
            "total_llc_writes.png",
            0,
        ),
        (
            "run_real_seconds",
            "Four-Core Simulation Time vs LLC Size",
            "Execution time (seconds)",
            "execution_time.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in summary_specs:
        save_bar(
            FOUR_OUTPUT,
            labels,
            [float(summary[size][field]) for size in SIZE_ORDER],
            title,
            ylabel,
            filename,
            decimals,
        )

    indexed: dict[int, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in per_core_rows:
        indexed[int(row["core"])][
            int(row["llc_size_mb"])
        ] = row

    for core in range(4):
        missing = [
            size for size in SIZE_ORDER
            if size not in indexed[core]
        ]

        if missing:
            fail(f"Core {core} missing LLC sizes: {missing}")

    save_grouped_bar(
        FOUR_OUTPUT,
        [f"Core {core}" for core in range(4)],
        {
            f"{size} MB": [
                float(indexed[core][size]["ipc"])
                for core in range(4)
            ]
            for size in SIZE_ORDER
        },
        "Four-Core Cumulative IPC by Core and LLC Size",
        "IPC",
        "per_core_ipc.png",
        rotation=0,
    )


def main() -> int:
    generate_single_core_graphs()
    generate_four_core_graphs()

    single_graphs = sorted(SINGLE_OUTPUT.glob("*.png"))
    four_graphs = sorted(FOUR_OUTPUT.glob("*.png"))

    print(f"Single-core graphs generated: {len(single_graphs)}")
    print(f"Four-core graphs generated:   {len(four_graphs)}")
    print(f"Total graphs generated:       {len(single_graphs) + len(four_graphs)}")

    if len(single_graphs) != 9:
        fail(f"Expected 9 single-core graphs, found {len(single_graphs)}")

    if len(four_graphs) != 9:
        fail(f"Expected 9 four-core graphs, found {len(four_graphs)}")

    for path in single_graphs + four_graphs:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
