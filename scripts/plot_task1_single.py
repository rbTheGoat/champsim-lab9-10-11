#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

DETAIL_CSV = Path("results/csv/task1_single_results.csv")
SUMMARY_CSV = Path("results/csv/task1_single_summary.csv")
OUTPUT_DIR = Path("results/graphs/task1/single")

PREDICTOR_ORDER = [
    "bimodal",
    "gshare",
    "hashed_perceptron",
    "perceptron",
]

PREDICTOR_LABELS = {
    "bimodal": "Bimodal",
    "gshare": "Gshare",
    "hashed_perceptron": "Hashed Perceptron",
    "perceptron": "Perceptron",
}


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


def save_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    output_name: str,
    *,
    rotate_labels: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, values)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)

    if rotate_labels:
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
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_grouped_bar_chart(
    traces: list[str],
    values_by_predictor: dict[str, list[float]],
    title: str,
    ylabel: str,
    output_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))

    predictor_count = len(PREDICTOR_ORDER)
    width = 0.18
    x_positions = list(range(len(traces)))

    for index, predictor in enumerate(PREDICTOR_ORDER):
        offset = (index - (predictor_count - 1) / 2) * width
        predictor_positions = [x + offset for x in x_positions]

        ax.bar(
            predictor_positions,
            values_by_predictor[predictor],
            width,
            label=PREDICTOR_LABELS[predictor],
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(traces, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def shortened_trace_name(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def main() -> int:
    detail_rows = load_csv(DETAIL_CSV)
    summary_rows = load_csv(SUMMARY_CSV)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_by_predictor = {
        row["predictor"]: row
        for row in summary_rows
    }

    missing_predictors = [
        predictor
        for predictor in PREDICTOR_ORDER
        if predictor not in summary_by_predictor
    ]

    if missing_predictors:
        fail(f"Missing predictors from summary CSV: {missing_predictors}")

    predictor_labels = [
        PREDICTOR_LABELS[predictor]
        for predictor in PREDICTOR_ORDER
    ]

    average_chart_specs = [
        ("average_accuracy_percent", "Average Branch Prediction Accuracy", "Accuracy (%)", "average_accuracy.png"),
        ("average_mpki", "Average Branch Mispredictions per Kilo-Instruction", "MPKI", "average_mpki.png"),
        ("average_lookup_latency_ns", "Average Branch Predictor Lookup Latency", "Lookup latency (ns)", "average_lookup_latency.png"),
        ("average_real_seconds", "Average ChampSim Execution Time", "Execution time (seconds)", "average_execution_time.png"),
        ("geomean_ipc", "Geometric-Mean IPC", "Geometric-mean IPC", "geomean_ipc.png"),
    ]

    for field, title, ylabel, filename in average_chart_specs:
        values = [
            float(summary_by_predictor[predictor][field])
            for predictor in PREDICTOR_ORDER
        ]

        save_bar_chart(
            predictor_labels,
            values,
            title,
            ylabel,
            filename,
            rotate_labels=True,
        )

    traces = sorted({
        shortened_trace_name(row["trace"])
        for row in detail_rows
    })

    detail_index: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        predictor = row["predictor"]
        trace = shortened_trace_name(row["trace"])
        detail_index[trace][predictor] = row

    for trace in traces:
        missing = [
            predictor
            for predictor in PREDICTOR_ORDER
            if predictor not in detail_index[trace]
        ]
        if missing:
            fail(f"Trace {trace} is missing predictors: {missing}")

    per_trace_chart_specs = [
        ("accuracy_percent", "Branch Prediction Accuracy by Trace", "Accuracy (%)", "per_trace_accuracy.png"),
        ("mpki", "Branch MPKI by Trace", "MPKI", "per_trace_mpki.png"),
        ("lookup_latency_ns", "Branch Predictor Lookup Latency by Trace", "Lookup latency (ns)", "per_trace_lookup_latency.png"),
        ("real_seconds", "ChampSim Execution Time by Trace", "Execution time (seconds)", "per_trace_execution_time.png"),
        ("ipc", "Cumulative IPC by Trace", "IPC", "per_trace_ipc.png"),
    ]

    for field, title, ylabel, filename in per_trace_chart_specs:
        values_by_predictor = {
            predictor: [
                float(detail_index[trace][predictor][field])
                for trace in traces
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_bar_chart(
            traces,
            values_by_predictor,
            title,
            ylabel,
            filename,
        )

    generated_files = sorted(OUTPUT_DIR.glob("*.png"))

    print(f"Generated graphs: {len(generated_files)}")
    for path in generated_files:
        print(path)

    if len(generated_files) != 10:
        fail(f"Expected 10 graph files, found {len(generated_files)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
