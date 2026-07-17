#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path(
    "results/csv/task1_single_results_with_modified_bullseye.csv"
)
SINGLE_SUMMARY = Path(
    "results/csv/task1_single_summary_with_modified_bullseye.csv"
)
FOUR_DETAIL = Path(
    "results/csv/task1_four_core_results_with_modified_bullseye.csv"
)
FOUR_SUMMARY = Path(
    "results/csv/task1_four_core_summary_with_modified_bullseye.csv"
)

SINGLE_OUTPUT = Path(
    "results/graphs/task1/with_modified_bullseye/single"
)
FOUR_OUTPUT = Path(
    "results/graphs/task1/with_modified_bullseye/four_core"
)

PREDICTOR_ORDER = [
    "bimodal",
    "gshare",
    "hashed_perceptron",
    "perceptron",
    "modified_bullseye",
]

PREDICTOR_LABELS = {
    "bimodal": "Bimodal",
    "gshare": "Gshare",
    "hashed_perceptron": "Hashed Perceptron",
    "perceptron": "Perceptron",
    "modified_bullseye": "Modified Bullseye",
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


def save_simple_bar(
    output_dir: Path,
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(labels, values)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", labelrotation=20)

    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_grouped_chart(
    output_dir: Path,
    categories: list[str],
    values_by_predictor: dict[str, list[float]],
    title: str,
    ylabel: str,
    filename: str,
    category_label_rotation: int = 20,
) -> None:
    fig, ax = plt.subplots(figsize=(14, 7))

    width = 0.15
    x_positions = list(range(len(categories)))

    for index, predictor in enumerate(PREDICTOR_ORDER):
        offset = (index - 2) * width
        positions = [x + offset for x in x_positions]

        ax.bar(
            positions,
            values_by_predictor[predictor],
            width,
            label=PREDICTOR_LABELS[predictor],
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(
        categories,
        rotation=category_label_rotation,
        ha="right" if category_label_rotation else "center",
    )
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def shortened_trace_name(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def generate_single_core_graphs() -> None:
    detail_rows = load_csv(SINGLE_DETAIL)
    summary_rows = load_csv(SINGLE_SUMMARY)

    SINGLE_OUTPUT.mkdir(parents=True, exist_ok=True)

    summary_by_predictor = {
        row["predictor"]: row for row in summary_rows
    }

    for predictor in PREDICTOR_ORDER:
        if predictor not in summary_by_predictor:
            fail(f"Missing {predictor} in single-core summary")

    labels = [PREDICTOR_LABELS[p] for p in PREDICTOR_ORDER]

    summary_specs = [
        (
            "average_accuracy_percent",
            "Single-Core Average Branch Prediction Accuracy",
            "Accuracy (%)",
            "average_accuracy.png",
        ),
        (
            "average_mpki",
            "Single-Core Average Branch MPKI",
            "MPKI",
            "average_mpki.png",
        ),
        (
            "average_lookup_latency_ns",
            "Single-Core Average Predictor Lookup Latency",
            "Lookup latency (ns)",
            "average_lookup_latency.png",
        ),
        (
            "average_real_seconds",
            "Single-Core Average ChampSim Execution Time",
            "Execution time (seconds)",
            "average_execution_time.png",
        ),
        (
            "geomean_ipc",
            "Single-Core Geometric-Mean IPC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in summary_specs:
        values = [
            float(summary_by_predictor[predictor][field])
            for predictor in PREDICTOR_ORDER
        ]
        save_simple_bar(
            SINGLE_OUTPUT,
            labels,
            values,
            title,
            ylabel,
            filename,
        )

    traces = sorted({
        shortened_trace_name(row["trace"])
        for row in detail_rows
    })

    index: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        trace = shortened_trace_name(row["trace"])
        index[trace][row["predictor"]] = row

    for trace in traces:
        missing = [
            predictor
            for predictor in PREDICTOR_ORDER
            if predictor not in index[trace]
        ]
        if missing:
            fail(f"Trace {trace} is missing predictors: {missing}")

    detail_specs = [
        (
            "accuracy_percent",
            "Single-Core Branch Prediction Accuracy by Trace",
            "Accuracy (%)",
            "per_trace_accuracy.png",
        ),
        (
            "mpki",
            "Single-Core Branch MPKI by Trace",
            "MPKI",
            "per_trace_mpki.png",
        ),
        (
            "lookup_latency_ns",
            "Single-Core Lookup Latency by Trace",
            "Lookup latency (ns)",
            "per_trace_lookup_latency.png",
        ),
        (
            "real_seconds",
            "Single-Core Execution Time by Trace",
            "Execution time (seconds)",
            "per_trace_execution_time.png",
        ),
        (
            "ipc",
            "Single-Core Cumulative IPC by Trace",
            "IPC",
            "per_trace_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in detail_specs:
        values_by_predictor = {
            predictor: [
                float(index[trace][predictor][field])
                for trace in traces
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_chart(
            SINGLE_OUTPUT,
            traces,
            values_by_predictor,
            title,
            ylabel,
            filename,
        )


def generate_four_core_graphs() -> None:
    detail_rows = load_csv(FOUR_DETAIL)
    summary_rows = load_csv(FOUR_SUMMARY)

    FOUR_OUTPUT.mkdir(parents=True, exist_ok=True)

    summary_by_predictor = {
        row["predictor"]: row for row in summary_rows
    }

    for predictor in PREDICTOR_ORDER:
        if predictor not in summary_by_predictor:
            fail(f"Missing {predictor} in four-core summary")

    labels = [PREDICTOR_LABELS[p] for p in PREDICTOR_ORDER]

    summary_specs = [
        (
            "average_accuracy_percent",
            "Four-Core Average Branch Prediction Accuracy",
            "Accuracy (%)",
            "average_accuracy.png",
        ),
        (
            "average_mpki",
            "Four-Core Average Branch MPKI",
            "MPKI",
            "average_mpki.png",
        ),
        (
            "average_lookup_latency_ns",
            "Four-Core Average Predictor Lookup Latency",
            "Lookup latency (ns)",
            "average_lookup_latency.png",
        ),
        (
            "run_real_seconds",
            "Four-Core ChampSim Execution Time",
            "Execution time (seconds)",
            "execution_time.png",
        ),
        (
            "sum_ipc",
            "Four-Core Aggregate IPC",
            "Sum IPC",
            "sum_ipc.png",
        ),
        (
            "geomean_ipc",
            "Four-Core Geometric-Mean IPC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in summary_specs:
        values = [
            float(summary_by_predictor[predictor][field])
            for predictor in PREDICTOR_ORDER
        ]
        save_simple_bar(
            FOUR_OUTPUT,
            labels,
            values,
            title,
            ylabel,
            filename,
        )

    index: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        index[row["predictor"]][int(row["core"])] = row

    for predictor in PREDICTOR_ORDER:
        missing_cores = [
            core
            for core in range(4)
            if core not in index[predictor]
        ]
        if missing_cores:
            fail(
                f"{predictor} is missing four-core rows: {missing_cores}"
            )

    categories = [f"Core {core}" for core in range(4)]

    detail_specs = [
        (
            "accuracy_percent",
            "Four-Core Branch Prediction Accuracy by Core",
            "Accuracy (%)",
            "per_core_accuracy.png",
        ),
        (
            "mpki",
            "Four-Core Branch MPKI by Core",
            "MPKI",
            "per_core_mpki.png",
        ),
        (
            "lookup_latency_ns",
            "Four-Core Lookup Latency by Core",
            "Lookup latency (ns)",
            "per_core_lookup_latency.png",
        ),
        (
            "ipc",
            "Four-Core Cumulative IPC by Core",
            "IPC",
            "per_core_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in detail_specs:
        values_by_predictor = {
            predictor: [
                float(index[predictor][core][field])
                for core in range(4)
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_chart(
            FOUR_OUTPUT,
            categories,
            values_by_predictor,
            title,
            ylabel,
            filename,
            category_label_rotation=0,
        )


def main() -> int:
    generate_single_core_graphs()
    generate_four_core_graphs()

    single_graphs = sorted(SINGLE_OUTPUT.glob("*.png"))
    four_graphs = sorted(FOUR_OUTPUT.glob("*.png"))

    print(f"Single-core graphs generated: {len(single_graphs)}")
    print(f"Four-core graphs generated:   {len(four_graphs)}")

    if len(single_graphs) != 10:
        fail(f"Expected 10 single-core graphs, found {len(single_graphs)}")

    if len(four_graphs) != 10:
        fail(f"Expected 10 four-core graphs, found {len(four_graphs)}")

    for path in single_graphs + four_graphs:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
