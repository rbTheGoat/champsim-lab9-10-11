#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path("results/csv/task2_replacement_policy_size_single_results_all_policies.csv")
SINGLE_SUMMARY = Path("results/csv/task2_replacement_policy_size_single_summary_all_policies.csv")
FOUR_PER_CORE = Path("results/csv/task2_replacement_policy_size_four_core_per_core_all_policies.csv")
FOUR_SUMMARY = Path("results/csv/task2_replacement_policy_size_four_core_summary_all_policies.csv")

SINGLE_OUTPUT = Path("results/graphs/task2/replacement_policy_size/single")
FOUR_OUTPUT = Path("results/graphs/task2/replacement_policy_size/four_core")

POLICIES = ["lru", "srrip", "drrip", "ship", "mru", "random"]
LABELS = {
    "lru": "LRU",
    "srrip": "SRRIP",
    "drrip": "DRRIP",
    "ship": "SHIP",
    "mru": "MRU",
    "random": "Random",
}
SIZES = [1, 2, 4, 8]


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


def prepare(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob("*.png"):
        old.unlink()


def build_summary_index(rows: list[dict[str, str]]) -> dict[tuple[str, int], dict[str, str]]:
    indexed = {
        (row["replacement_policy"].lower(), int(row["llc_size_mb"])): row
        for row in rows
    }
    missing = [
        (policy, size)
        for policy in POLICIES
        for size in SIZES
        if (policy, size) not in indexed
    ]
    if missing:
        fail(f"Missing policy/size combinations: {missing}")
    return indexed


def save_trend(
    output: Path,
    indexed: dict[tuple[str, int], dict[str, str]],
    field: str,
    title: str,
    ylabel: str,
    filename: str,
    scientific: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 7))
    for policy in POLICIES:
        values = [float(indexed[(policy, size)][field]) for size in SIZES]
        ax.plot(SIZES, values, label=LABELS[policy])

    ax.set_title(title)
    ax.set_xlabel("LLC size (MB)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(SIZES)
    ax.grid(True, alpha=0.3)
    ax.legend()

    if scientific:
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))

    fig.tight_layout()
    fig.savefig(output / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_grouped_bars(
    output: Path,
    categories: list[str],
    values_by_policy: dict[str, list[float]],
    title: str,
    ylabel: str,
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(15, 8))
    x = list(range(len(categories)))
    width = 0.82 / len(POLICIES)

    for index, policy in enumerate(POLICIES):
        offset = (index - (len(POLICIES) - 1) / 2) * width
        positions = [value + offset for value in x]
        ax.bar(positions, values_by_policy[policy], width, label=LABELS[policy])

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def short_trace(trace: str) -> str:
    return trace.replace(".champsimtrace.xz", "")


def generate_single() -> None:
    detail = load_csv(SINGLE_DETAIL)
    summary = load_csv(SINGLE_SUMMARY)

    if len(detail) != 96:
        fail(f"Expected 96 single-core detail rows, found {len(detail)}")
    if len(summary) != 24:
        fail(f"Expected 24 single-core summary rows, found {len(summary)}")

    prepare(SINGLE_OUTPUT)
    indexed = build_summary_index(summary)

    specs = [
        ("average_ipc", "Single-Core Average Cumulative IPC Across LLC Sizes", "Average IPC", "01_average_ipc_vs_size.png", False),
        ("geomean_ipc", "Single-Core Geometric-Mean IPC Across LLC Sizes", "Geometric-mean IPC", "02_geomean_ipc_vs_size.png", False),
        ("weighted_l1_combined_miss_percent", "Single-Core L1 Miss Percentage Across LLC Sizes", "L1 miss (%)", "03_l1_miss_percent_vs_size.png", False),
        ("weighted_l2_miss_percent", "Single-Core L2 Miss Percentage Across LLC Sizes", "L2 miss (%)", "04_l2_miss_percent_vs_size.png", False),
        ("weighted_llc_miss_percent", "Single-Core LLC Miss Percentage Across LLC Sizes", "LLC miss (%)", "05_llc_miss_percent_vs_size.png", False),
        ("weighted_llc_hit_rate_percent", "Single-Core LLC Hit Rate Across LLC Sizes", "LLC hit rate (%)", "06_llc_hit_rate_vs_size.png", False),
        ("total_llc_write_requests", "Single-Core Total LLC Writes Across LLC Sizes", "Total LLC write requests", "07_total_llc_writes_vs_size.png", True),
        ("average_real_seconds", "Single-Core Average Simulation Time Across LLC Sizes", "Execution time (seconds)", "08_execution_time_vs_size.png", False),
    ]

    for field, title, ylabel, filename, scientific in specs:
        save_trend(SINGLE_OUTPUT, indexed, field, title, ylabel, filename, scientific)

    traces = sorted({short_trace(row["trace"]) for row in detail})
    if len(traces) != 4:
        fail(f"Expected four traces, found {len(traces)}")

    detailed: dict[tuple[int, str, str], dict[str, str]] = {}
    for row in detail:
        detailed[
            (
                int(row["llc_size_mb"]),
                row["replacement_policy"].lower(),
                short_trace(row["trace"]),
            )
        ] = row

    for graph_number, size in enumerate(SIZES, start=9):
        save_grouped_bars(
            SINGLE_OUTPUT,
            traces,
            {
                policy: [
                    float(detailed[(size, policy, trace)]["ipc"])
                    for trace in traces
                ]
                for policy in POLICIES
            },
            f"Single-Core IPC by Trace and Replacement Policy at {size} MB LLC",
            "IPC",
            f"{graph_number:02d}_per_trace_ipc_{size}mb.png",
        )


def generate_four() -> None:
    per_core = load_csv(FOUR_PER_CORE)
    summary = load_csv(FOUR_SUMMARY)

    if len(per_core) != 96:
        fail(f"Expected 96 four-core per-core rows, found {len(per_core)}")
    if len(summary) != 24:
        fail(f"Expected 24 four-core summary rows, found {len(summary)}")

    prepare(FOUR_OUTPUT)
    indexed = build_summary_index(summary)

    specs = [
        ("sum_ipc", "Four-Core Aggregate Cumulative IPC Across LLC Sizes", "Sum IPC", "01_sum_ipc_vs_size.png", False),
        ("geomean_ipc", "Four-Core Geometric-Mean IPC Across LLC Sizes", "Geometric-mean IPC", "02_geomean_ipc_vs_size.png", False),
        ("weighted_l1_combined_miss_percent", "Four-Core L1 Miss Percentage Across LLC Sizes", "L1 miss (%)", "03_l1_miss_percent_vs_size.png", False),
        ("weighted_l2_miss_percent", "Four-Core L2 Miss Percentage Across LLC Sizes", "L2 miss (%)", "04_l2_miss_percent_vs_size.png", False),
        ("llc_miss_percent", "Four-Core Shared LLC Miss Percentage Across LLC Sizes", "LLC miss (%)", "05_llc_miss_percent_vs_size.png", False),
        ("llc_hit_rate_percent", "Four-Core Shared LLC Hit Rate Across LLC Sizes", "LLC hit rate (%)", "06_llc_hit_rate_vs_size.png", False),
        ("llc_total_write_requests", "Four-Core Total LLC Writes Across LLC Sizes", "Total LLC write requests", "07_total_llc_writes_vs_size.png", True),
        ("run_real_seconds", "Four-Core Simulation Time Across LLC Sizes", "Execution time (seconds)", "08_execution_time_vs_size.png", False),
    ]

    for field, title, ylabel, filename, scientific in specs:
        save_trend(FOUR_OUTPUT, indexed, field, title, ylabel, filename, scientific)

    detailed: dict[tuple[int, str, int], dict[str, str]] = {}
    for row in per_core:
        detailed[
            (
                int(row["llc_size_mb"]),
                row["replacement_policy"].lower(),
                int(row["core"]),
            )
        ] = row

    for graph_number, size in enumerate(SIZES, start=9):
        save_grouped_bars(
            FOUR_OUTPUT,
            [f"Core {core}" for core in range(4)],
            {
                policy: [
                    float(detailed[(size, policy, core)]["ipc"])
                    for core in range(4)
                ]
                for policy in POLICIES
            },
            f"Four-Core IPC by Core and Replacement Policy at {size} MB Shared LLC",
            "IPC",
            f"{graph_number:02d}_per_core_ipc_{size}mb.png",
        )


def main() -> int:
    generate_single()
    generate_four()

    single_graphs = sorted(SINGLE_OUTPUT.glob("*.png"))
    four_graphs = sorted(FOUR_OUTPUT.glob("*.png"))

    print("Task 2 replacement-policy × LLC-size graphs generated successfully.")
    print(f"Single-core graphs: {len(single_graphs)}")
    print(f"Four-core graphs:   {len(four_graphs)}")
    print(f"Total graphs:       {len(single_graphs) + len(four_graphs)}")

    if len(single_graphs) != 12:
        fail(f"Expected 12 single-core graphs, found {len(single_graphs)}")
    if len(four_graphs) != 12:
        fail(f"Expected 12 four-core graphs, found {len(four_graphs)}")

    print(f"Single-core directory: {SINGLE_OUTPUT}")
    print(f"Four-core directory:   {FOUR_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
