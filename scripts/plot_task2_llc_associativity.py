#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path(
    "results/csv/task2_llc_associativity_single_results.csv"
)
SINGLE_SUMMARY = Path(
    "results/csv/task2_llc_associativity_single_summary.csv"
)
SINGLE_COMPARISON = Path(
    "results/csv/task2_llc_associativity_single_comparison.csv"
)

FOUR_PER_CORE = Path(
    "results/csv/task2_llc_associativity_four_core_per_core_results.csv"
)
FOUR_SUMMARY = Path(
    "results/csv/task2_llc_associativity_four_core_summary.csv"
)
FOUR_COMPARISON = Path(
    "results/csv/task2_llc_associativity_four_core_comparison.csv"
)

SINGLE_OUTPUT = Path(
    "results/graphs/task2/llc_associativity/single"
)
FOUR_OUTPUT = Path(
    "results/graphs/task2/llc_associativity/four_core"
)

ASSOC_ORDER = [16, 8]
ASSOC_LABELS = {
    16: "16-way",
    8: "8-way",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV file: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No rows found in {path}")

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
            xytext=(0, 4 if value >= 0 else -12),
            textcoords="offset points",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
        )


def save_simple_bar(
    output_dir: Path,
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    filename: str,
    decimals: int = 3,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
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
    values_by_assoc: dict[int, list[float]],
    title: str,
    ylabel: str,
    filename: str,
    rotation: int = 20,
) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))

    width = 0.34
    x_positions = list(range(len(categories)))

    for index, associativity in enumerate(ASSOC_ORDER):
        offset = (index - 0.5) * width
        positions = [x + offset for x in x_positions]

        ax.bar(
            positions,
            values_by_assoc[associativity],
            width,
            label=ASSOC_LABELS[associativity],
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


def save_percent_change_chart(
    output_dir: Path,
    rows: list[dict[str, str]],
    title: str,
    filename: str,
) -> None:
    selected_metrics = [
        "average_ipc",
        "sum_ipc",
        "weighted_l1_combined_miss_percent",
        "weighted_l2_miss_percent",
        "weighted_llc_miss_percent",
        "llc_miss_percent",
        "weighted_llc_hit_rate_percent",
        "llc_hit_rate_percent",
        "total_llc_write_requests",
        "llc_total_write_requests",
        "average_real_seconds",
        "run_real_seconds",
    ]

    label_map = {
        "average_ipc": "Average IPC",
        "sum_ipc": "Sum IPC",
        "weighted_l1_combined_miss_percent": "L1 miss %",
        "weighted_l2_miss_percent": "L2 miss %",
        "weighted_llc_miss_percent": "LLC miss %",
        "llc_miss_percent": "LLC miss %",
        "weighted_llc_hit_rate_percent": "LLC hit rate",
        "llc_hit_rate_percent": "LLC hit rate",
        "total_llc_write_requests": "LLC writes",
        "llc_total_write_requests": "LLC writes",
        "average_real_seconds": "Execution time",
        "run_real_seconds": "Execution time",
    }

    indexed = {
        row["metric"]: float(row["percent_change_from_16way"])
        for row in rows
    }

    metrics = [
        metric
        for metric in selected_metrics
        if metric in indexed
    ]

    labels = [label_map[metric] for metric in metrics]
    values = [indexed[metric] for metric in metrics]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(labels, values)

    ax.axhline(0, linewidth=1)
    ax.set_title(title)
    ax.set_ylabel("Change from 16-way to 8-way (%)")
    ax.tick_params(axis="x", labelrotation=25)
    ax.grid(axis="y", alpha=0.3)

    annotate_bars(ax, bars, decimals=3)

    fig.tight_layout()
    fig.savefig(
        output_dir / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def short_trace(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def summary_index(
    rows: list[dict[str, str]],
) -> dict[int, dict[str, str]]:
    indexed = {
        int(row["llc_associativity"]): row
        for row in rows
    }

    missing = [
        associativity
        for associativity in ASSOC_ORDER
        if associativity not in indexed
    ]

    if missing:
        fail(f"Missing associativity values: {missing}")

    return indexed


def generate_single_core_graphs() -> None:
    detail_rows = load_csv(SINGLE_DETAIL)
    summary_rows = load_csv(SINGLE_SUMMARY)
    comparison_rows = load_csv(SINGLE_COMPARISON)

    prepare_directory(SINGLE_OUTPUT)

    summary = summary_index(summary_rows)
    labels = [ASSOC_LABELS[value] for value in ASSOC_ORDER]

    summary_specs = [
        (
            "average_ipc",
            "Single-Core Average IPC: 16-way vs 8-way LLC",
            "Average IPC",
            "average_ipc.png",
            5,
        ),
        (
            "geomean_ipc",
            "Single-Core Geometric-Mean IPC: 16-way vs 8-way LLC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
            5,
        ),
        (
            "weighted_l1_combined_miss_percent",
            "Single-Core L1 Miss Percentage: 16-way vs 8-way LLC",
            "L1 miss (%)",
            "l1_miss_percent.png",
            5,
        ),
        (
            "weighted_l2_miss_percent",
            "Single-Core L2 Miss Percentage: 16-way vs 8-way LLC",
            "L2 miss (%)",
            "l2_miss_percent.png",
            5,
        ),
        (
            "weighted_llc_miss_percent",
            "Single-Core LLC Miss Percentage: 16-way vs 8-way LLC",
            "LLC miss (%)",
            "llc_miss_percent.png",
            5,
        ),
        (
            "weighted_llc_hit_rate_percent",
            "Single-Core LLC Hit Rate: 16-way vs 8-way LLC",
            "LLC hit rate (%)",
            "llc_hit_rate.png",
            5,
        ),
        (
            "total_llc_write_requests",
            "Single-Core Total LLC Writes: 16-way vs 8-way LLC",
            "Total LLC write requests",
            "total_llc_writes.png",
            0,
        ),
        (
            "average_real_seconds",
            "Single-Core Simulation Time: 16-way vs 8-way LLC",
            "Execution time (seconds)",
            "execution_time.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in summary_specs:
        save_simple_bar(
            SINGLE_OUTPUT,
            labels,
            [
                float(summary[associativity][field])
                for associativity in ASSOC_ORDER
            ],
            title,
            ylabel,
            filename,
            decimals,
        )

    indexed: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        indexed[short_trace(row["trace"])][
            int(row["llc_associativity"])
        ] = row

    traces = sorted(indexed)

    for trace in traces:
        missing = [
            associativity
            for associativity in ASSOC_ORDER
            if associativity not in indexed[trace]
        ]

        if missing:
            fail(f"Trace {trace} missing associativity rows: {missing}")

    save_grouped_bar(
        SINGLE_OUTPUT,
        traces,
        {
            associativity: [
                float(indexed[trace][associativity]["ipc"])
                for trace in traces
            ]
            for associativity in ASSOC_ORDER
        },
        "Single-Core IPC by Trace: 16-way vs 8-way LLC",
        "IPC",
        "per_trace_ipc.png",
    )

    save_percent_change_chart(
        SINGLE_OUTPUT,
        comparison_rows,
        "Single-Core Percentage Change After Reducing LLC Associativity",
        "percent_change_overview.png",
    )


def generate_four_core_graphs() -> None:
    per_core_rows = load_csv(FOUR_PER_CORE)
    summary_rows = load_csv(FOUR_SUMMARY)
    comparison_rows = load_csv(FOUR_COMPARISON)

    prepare_directory(FOUR_OUTPUT)

    summary = summary_index(summary_rows)
    labels = [ASSOC_LABELS[value] for value in ASSOC_ORDER]

    summary_specs = [
        (
            "sum_ipc",
            "Four-Core Aggregate IPC: 16-way vs 8-way LLC",
            "Sum IPC",
            "sum_ipc.png",
            5,
        ),
        (
            "geomean_ipc",
            "Four-Core Geometric-Mean IPC: 16-way vs 8-way LLC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
            5,
        ),
        (
            "weighted_l1_combined_miss_percent",
            "Four-Core L1 Miss Percentage: 16-way vs 8-way LLC",
            "L1 miss (%)",
            "l1_miss_percent.png",
            5,
        ),
        (
            "weighted_l2_miss_percent",
            "Four-Core L2 Miss Percentage: 16-way vs 8-way LLC",
            "L2 miss (%)",
            "l2_miss_percent.png",
            5,
        ),
        (
            "llc_miss_percent",
            "Four-Core LLC Miss Percentage: 16-way vs 8-way LLC",
            "LLC miss (%)",
            "llc_miss_percent.png",
            5,
        ),
        (
            "llc_hit_rate_percent",
            "Four-Core LLC Hit Rate: 16-way vs 8-way LLC",
            "LLC hit rate (%)",
            "llc_hit_rate.png",
            5,
        ),
        (
            "llc_total_write_requests",
            "Four-Core Total LLC Writes: 16-way vs 8-way LLC",
            "Total LLC write requests",
            "total_llc_writes.png",
            0,
        ),
        (
            "run_real_seconds",
            "Four-Core Simulation Time: 16-way vs 8-way LLC",
            "Execution time (seconds)",
            "execution_time.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in summary_specs:
        save_simple_bar(
            FOUR_OUTPUT,
            labels,
            [
                float(summary[associativity][field])
                for associativity in ASSOC_ORDER
            ],
            title,
            ylabel,
            filename,
            decimals,
        )

    indexed: dict[int, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in per_core_rows:
        indexed[int(row["core"])][
            int(row["llc_associativity"])
        ] = row

    for core in range(4):
        missing = [
            associativity
            for associativity in ASSOC_ORDER
            if associativity not in indexed[core]
        ]

        if missing:
            fail(f"Core {core} missing associativity rows: {missing}")

    save_grouped_bar(
        FOUR_OUTPUT,
        [f"Core {core}" for core in range(4)],
        {
            associativity: [
                float(indexed[core][associativity]["ipc"])
                for core in range(4)
            ]
            for associativity in ASSOC_ORDER
        },
        "Four-Core IPC by Core: 16-way vs 8-way LLC",
        "IPC",
        "per_core_ipc.png",
        rotation=0,
    )

    save_percent_change_chart(
        FOUR_OUTPUT,
        comparison_rows,
        "Four-Core Percentage Change After Reducing LLC Associativity",
        "percent_change_overview.png",
    )


def main() -> int:
    generate_single_core_graphs()
    generate_four_core_graphs()

    single_graphs = sorted(SINGLE_OUTPUT.glob("*.png"))
    four_graphs = sorted(FOUR_OUTPUT.glob("*.png"))

    print(f"Single-core graphs generated: {len(single_graphs)}")
    print(f"Four-core graphs generated:   {len(four_graphs)}")
    print(f"Total graphs generated:       {len(single_graphs) + len(four_graphs)}")

    if len(single_graphs) != 10:
        fail(f"Expected 10 single-core graphs, found {len(single_graphs)}")

    if len(four_graphs) != 10:
        fail(f"Expected 10 four-core graphs, found {len(four_graphs)}")

    for path in single_graphs + four_graphs:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
