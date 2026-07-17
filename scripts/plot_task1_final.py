#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path(
    "results/csv/task1_single_results_all_predictors.csv"
)
SINGLE_SUMMARY = Path(
    "results/csv/task1_single_summary_all_predictors.csv"
)
FOUR_DETAIL = Path(
    "results/csv/task1_four_core_results_all_predictors.csv"
)
FOUR_SUMMARY = Path(
    "results/csv/task1_four_core_summary_all_predictors.csv"
)

ADAPTIVE_SINGLE_INTERNAL = Path(
    "results/csv/task1_adaptive_bullseye_single_internal_stats.csv"
)
ADAPTIVE_FOUR_INTERNAL = Path(
    "results/csv/task1_adaptive_bullseye_four_core_internal_stats.csv"
)

FINAL_SINGLE_DIR = Path(
    "results/graphs/task1/final/single"
)
FINAL_FOUR_DIR = Path(
    "results/graphs/task1/final/four_core"
)
ADAPTIVE_SINGLE_DIR = Path(
    "results/graphs/task1/final/adaptive_internal/single"
)
ADAPTIVE_FOUR_DIR = Path(
    "results/graphs/task1/final/adaptive_internal/four_core"
)

PREDICTOR_ORDER = [
    "bimodal",
    "gshare",
    "hashed_perceptron",
    "perceptron",
    "modified_bullseye",
    "adaptive_bullseye",
]

PREDICTOR_LABELS = {
    "bimodal": "Bimodal",
    "gshare": "Gshare",
    "hashed_perceptron": "Hashed Perceptron",
    "perceptron": "Perceptron",
    "modified_bullseye": "Modified Bullseye",
    "adaptive_bullseye": "Adaptive Bullseye",
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


def prepare_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

    for old_graph in path.glob("*.png"):
        old_graph.unlink()


def annotate_bars(ax, bars, decimals: int = 3) -> None:
    for bar in bars:
        value = bar.get_height()

        ax.annotate(
            f"{value:.{decimals}f}",
            xy=(
                bar.get_x() + bar.get_width() / 2,
                value,
            ),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
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
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(labels, values)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", labelrotation=24)

    annotate_bars(ax, bars, decimals)

    fig.tight_layout()
    fig.savefig(
        output_dir / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def save_grouped_chart(
    output_dir: Path,
    categories: list[str],
    values_by_predictor: dict[str, list[float]],
    title: str,
    ylabel: str,
    filename: str,
    category_rotation: int = 20,
) -> None:
    fig, ax = plt.subplots(figsize=(15, 8))

    width = 0.13
    x_positions = list(range(len(categories)))

    for index, predictor in enumerate(PREDICTOR_ORDER):
        offset = (index - 2.5) * width
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
        rotation=category_rotation,
        ha="right" if category_rotation else "center",
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


def save_adaptive_bar(
    output_dir: Path,
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    filename: str,
    decimals: int = 2,
    rotation: int = 20,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(labels, values)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", labelrotation=rotation)

    annotate_bars(ax, bars, decimals)

    fig.tight_layout()
    fig.savefig(
        output_dir / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)


def shortened_trace(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def validate_predictors(
    rows: list[dict[str, str]],
    label: str,
) -> dict[str, dict[str, str]]:
    indexed = {row["predictor"]: row for row in rows}

    missing = [
        predictor
        for predictor in PREDICTOR_ORDER
        if predictor not in indexed
    ]

    if missing:
        fail(f"{label} missing predictors: {missing}")

    return indexed


def generate_single_core_graphs() -> None:
    detail_rows = load_csv(SINGLE_DETAIL)
    summary_rows = load_csv(SINGLE_SUMMARY)

    prepare_directory(FINAL_SINGLE_DIR)

    summary = validate_predictors(
        summary_rows,
        "Single-core summary",
    )

    labels = [
        PREDICTOR_LABELS[predictor]
        for predictor in PREDICTOR_ORDER
    ]

    summary_specs = [
        (
            "average_accuracy_percent",
            "Final Single-Core Branch Prediction Accuracy",
            "Accuracy (%)",
            "average_accuracy.png",
        ),
        (
            "average_mpki",
            "Final Single-Core Branch MPKI",
            "MPKI",
            "average_mpki.png",
        ),
        (
            "average_lookup_latency_ns",
            "Final Single-Core Predictor Lookup Latency",
            "Host-side lookup latency (ns)",
            "average_lookup_latency.png",
        ),
        (
            "average_real_seconds",
            "Final Single-Core ChampSim Execution Time",
            "Execution time (seconds)",
            "average_execution_time.png",
        ),
        (
            "geomean_ipc",
            "Final Single-Core Geometric-Mean IPC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in summary_specs:
        values = [
            float(summary[predictor][field])
            for predictor in PREDICTOR_ORDER
        ]

        save_simple_bar(
            FINAL_SINGLE_DIR,
            labels,
            values,
            title,
            ylabel,
            filename,
        )

    traces = sorted({
        shortened_trace(row["trace"])
        for row in detail_rows
    })

    indexed: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        indexed[shortened_trace(row["trace"])][row["predictor"]] = row

    for trace in traces:
        missing = [
            predictor
            for predictor in PREDICTOR_ORDER
            if predictor not in indexed[trace]
        ]

        if missing:
            fail(f"Trace {trace} missing predictors: {missing}")

    detail_specs = [
        (
            "accuracy_percent",
            "Final Single-Core Accuracy by Trace",
            "Accuracy (%)",
            "per_trace_accuracy.png",
        ),
        (
            "mpki",
            "Final Single-Core MPKI by Trace",
            "MPKI",
            "per_trace_mpki.png",
        ),
        (
            "lookup_latency_ns",
            "Final Single-Core Lookup Latency by Trace",
            "Host-side lookup latency (ns)",
            "per_trace_lookup_latency.png",
        ),
        (
            "real_seconds",
            "Final Single-Core Execution Time by Trace",
            "Execution time (seconds)",
            "per_trace_execution_time.png",
        ),
        (
            "ipc",
            "Final Single-Core IPC by Trace",
            "IPC",
            "per_trace_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in detail_specs:
        values_by_predictor = {
            predictor: [
                float(indexed[trace][predictor][field])
                for trace in traces
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_chart(
            FINAL_SINGLE_DIR,
            traces,
            values_by_predictor,
            title,
            ylabel,
            filename,
        )


def generate_four_core_graphs() -> None:
    detail_rows = load_csv(FOUR_DETAIL)
    summary_rows = load_csv(FOUR_SUMMARY)

    prepare_directory(FINAL_FOUR_DIR)

    summary = validate_predictors(
        summary_rows,
        "Four-core summary",
    )

    labels = [
        PREDICTOR_LABELS[predictor]
        for predictor in PREDICTOR_ORDER
    ]

    summary_specs = [
        (
            "average_accuracy_percent",
            "Final Four-Core Branch Prediction Accuracy",
            "Average accuracy (%)",
            "average_accuracy.png",
        ),
        (
            "average_mpki",
            "Final Four-Core Branch MPKI",
            "Average MPKI",
            "average_mpki.png",
        ),
        (
            "average_lookup_latency_ns",
            "Final Four-Core Predictor Lookup Latency",
            "Average host-side lookup latency (ns)",
            "average_lookup_latency.png",
        ),
        (
            "run_real_seconds",
            "Final Four-Core ChampSim Execution Time",
            "Execution time (seconds)",
            "execution_time.png",
        ),
        (
            "sum_ipc",
            "Final Four-Core Aggregate IPC",
            "Sum IPC",
            "sum_ipc.png",
        ),
        (
            "geomean_ipc",
            "Final Four-Core Geometric-Mean IPC",
            "Geometric-mean IPC",
            "geomean_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in summary_specs:
        values = [
            float(summary[predictor][field])
            for predictor in PREDICTOR_ORDER
        ]

        save_simple_bar(
            FINAL_FOUR_DIR,
            labels,
            values,
            title,
            ylabel,
            filename,
        )

    indexed: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)

    for row in detail_rows:
        indexed[row["predictor"]][int(row["core"])] = row

    for predictor in PREDICTOR_ORDER:
        missing_cores = [
            core
            for core in range(4)
            if core not in indexed[predictor]
        ]

        if missing_cores:
            fail(
                f"{predictor} missing four-core rows: {missing_cores}"
            )

    categories = [f"Core {core}" for core in range(4)]

    detail_specs = [
        (
            "accuracy_percent",
            "Final Four-Core Accuracy by Core",
            "Accuracy (%)",
            "per_core_accuracy.png",
        ),
        (
            "mpki",
            "Final Four-Core MPKI by Core",
            "MPKI",
            "per_core_mpki.png",
        ),
        (
            "lookup_latency_ns",
            "Final Four-Core Lookup Latency by Core",
            "Host-side lookup latency (ns)",
            "per_core_lookup_latency.png",
        ),
        (
            "ipc",
            "Final Four-Core IPC by Core",
            "IPC",
            "per_core_ipc.png",
        ),
    ]

    for field, title, ylabel, filename in detail_specs:
        values_by_predictor = {
            predictor: [
                float(indexed[predictor][core][field])
                for core in range(4)
            ]
            for predictor in PREDICTOR_ORDER
        }

        save_grouped_chart(
            FINAL_FOUR_DIR,
            categories,
            values_by_predictor,
            title,
            ylabel,
            filename,
            category_rotation=0,
        )


def generate_adaptive_single_graphs() -> None:
    rows = load_csv(ADAPTIVE_SINGLE_INTERNAL)
    prepare_directory(ADAPTIVE_SINGLE_DIR)

    if len(rows) != 4:
        fail(
            "Expected four adaptive single-core internal rows, "
            f"found {len(rows)}"
        )

    rows = sorted(rows, key=lambda row: row["trace"])
    labels = [shortened_trace(row["trace"]) for row in rows]

    specs = [
        (
            "final_admission_threshold",
            "Adaptive Bullseye Final Threshold by Trace",
            "Admission threshold",
            "final_threshold.png",
            0,
        ),
        (
            "threshold_adjustments",
            "Adaptive Bullseye Threshold Adjustments by Trace",
            "Adjustment count",
            "threshold_adjustments.png",
            0,
        ),
        (
            "base_miss_rate_percent",
            "Adaptive Bullseye Base Miss Rate by Trace",
            "Base miss rate (%)",
            "base_miss_rate.png",
            3,
        ),
        (
            "h2p_occupancy_percent",
            "Adaptive Bullseye H2P Occupancy by Trace",
            "H2P occupancy (%)",
            "h2p_occupancy.png",
            2,
        ),
        (
            "h2p_admissions",
            "Adaptive Bullseye H2P Admissions by Trace",
            "Admissions",
            "h2p_admissions.png",
            0,
        ),
        (
            "h2p_overrides",
            "Adaptive Bullseye H2P Overrides by Trace",
            "Overrides",
            "h2p_overrides.png",
            0,
        ),
        (
            "h2p_override_accuracy_percent",
            "Adaptive Bullseye H2P Override Accuracy by Trace",
            "Override accuracy (%)",
            "h2p_override_accuracy.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in specs:
        save_adaptive_bar(
            ADAPTIVE_SINGLE_DIR,
            labels,
            [float(row[field]) for row in rows],
            title,
            ylabel,
            filename,
            decimals=decimals,
        )


def generate_adaptive_four_core_graphs() -> None:
    rows = load_csv(ADAPTIVE_FOUR_INTERNAL)
    prepare_directory(ADAPTIVE_FOUR_DIR)

    if len(rows) != 4:
        fail(
            "Expected four adaptive four-core internal rows, "
            f"found {len(rows)}"
        )

    rows = sorted(rows, key=lambda row: int(row["core"]))
    labels = [f"Core {row['core']}" for row in rows]

    specs = [
        (
            "final_admission_threshold",
            "Adaptive Bullseye Four-Core Final Threshold",
            "Admission threshold",
            "final_threshold.png",
            0,
        ),
        (
            "threshold_adjustments",
            "Adaptive Bullseye Four-Core Threshold Adjustments",
            "Adjustment count",
            "threshold_adjustments.png",
            0,
        ),
        (
            "base_miss_rate_percent",
            "Adaptive Bullseye Four-Core Base Miss Rate",
            "Base miss rate (%)",
            "base_miss_rate.png",
            3,
        ),
        (
            "h2p_occupancy_percent",
            "Adaptive Bullseye Four-Core H2P Occupancy",
            "H2P occupancy (%)",
            "h2p_occupancy.png",
            2,
        ),
        (
            "h2p_admissions",
            "Adaptive Bullseye Four-Core H2P Admissions",
            "Admissions",
            "h2p_admissions.png",
            0,
        ),
        (
            "h2p_overrides",
            "Adaptive Bullseye Four-Core H2P Overrides",
            "Overrides",
            "h2p_overrides.png",
            0,
        ),
        (
            "h2p_override_accuracy_percent",
            "Adaptive Bullseye Four-Core H2P Override Accuracy",
            "Override accuracy (%)",
            "h2p_override_accuracy.png",
            3,
        ),
    ]

    for field, title, ylabel, filename, decimals in specs:
        save_adaptive_bar(
            ADAPTIVE_FOUR_DIR,
            labels,
            [float(row[field]) for row in rows],
            title,
            ylabel,
            filename,
            decimals=decimals,
            rotation=0,
        )


def main() -> int:
    generate_single_core_graphs()
    generate_four_core_graphs()
    generate_adaptive_single_graphs()
    generate_adaptive_four_core_graphs()

    counts = {
        "final single-core": len(list(FINAL_SINGLE_DIR.glob("*.png"))),
        "final four-core": len(list(FINAL_FOUR_DIR.glob("*.png"))),
        "adaptive single-core": len(
            list(ADAPTIVE_SINGLE_DIR.glob("*.png"))
        ),
        "adaptive four-core": len(
            list(ADAPTIVE_FOUR_DIR.glob("*.png"))
        ),
    }

    expected = {
        "final single-core": 10,
        "final four-core": 10,
        "adaptive single-core": 7,
        "adaptive four-core": 7,
    }

    for label, count in counts.items():
        print(f"{label}: {count} graphs")

        if count != expected[label]:
            fail(
                f"Expected {expected[label]} {label} graphs, "
                f"found {count}"
            )

    print(f"Total graphs generated: {sum(counts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
