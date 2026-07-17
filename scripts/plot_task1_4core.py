#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

DETAIL_CSV = Path("results/csv/task1_four_core_results.csv")
SUMMARY_CSV = Path("results/csv/task1_four_core_summary.csv")
OUTPUT_DIR = Path("results/graphs/task1/four_core")

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
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
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
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_grouped_core_chart(
    values_by_predictor: dict[str, list[float]],
    title: str,
    ylabel: str,
    output_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))

    cores = [0, 1, 2, 3]
    width = 0.18

    for index, predictor in enumerate(PREDICTOR_ORDER):
        offset = (index - 1.5) * width
        positions = [core + offset for core in cores]

        ax.bar(
            positions,
            values_by_predictor[predictor],
            width,
            label=PREDICTOR_LABELS[predictor],
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(cores)
    ax.set_xticklabels([f"Core {core}" for core in cores])
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


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
        save_bar_chart(labels, values, title, ylabel, filename)

    indexed: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        predictor = row["predictor"]
        core = int(row["core"])
        indexed[predictor][core] = row

    for predictor in PREDICTOR_ORDER:
        missing_cores = [
            core for core in range(4)
            if core not in indexed[predictor]
        ]
        if missing_cores:
            fail(f"{predictor} is missing cores: {missing_cores}")

    core_specs = [
        (
            "accuracy_percent",
            "Branch Prediction Accuracy by Core",
            "Accuracy (%)",
            "per_core_accuracy.png",
        ),
        (
            "mpki",
            "Branch MPKI by Core",
            "MPKI",
            "per_core_mpki.png",
        ),
        (
            "lookup_latency_ns",
            "Predictor Lookup Latency by Core",
            "Lookup latency (ns)",
            "per_core_lookup_latency.png",
        ),
        (
            "ipc",
            "Cumulative IPC by Core",
            "IPC",
            "per_core_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in core_specs:
        values_by_predictor = {
            predictor: [
                float(indexed[predictor][core][field])
                for core in range(4)
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_core_chart(
            values_by_predictor,
            title,
            ylabel,
            filename,
        )

    generated = sorted(OUTPUT_DIR.glob("*.png"))

    print(f"Generated graphs: {len(generated)}")
    for path in generated:
        print(path)

    if len(generated) != 10:
        fail(f"Expected 10 graphs, found {len(generated)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
