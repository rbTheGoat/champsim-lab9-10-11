#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SINGLE_DETAIL = Path("results/csv/task2_replacement_policy_size_single_results_with_hcit.csv")
SINGLE_SUMMARY = Path("results/csv/task2_replacement_policy_size_single_summary_with_hcit.csv")
FOUR_PER_CORE = Path("results/csv/task2_replacement_policy_size_four_core_per_core_with_hcit.csv")
FOUR_SUMMARY = Path("results/csv/task2_replacement_policy_size_four_core_summary_with_hcit.csv")
INTERNAL_SINGLE = Path("results/csv/task2_hcit_internal_single.csv")
INTERNAL_FOUR = Path("results/csv/task2_hcit_internal_four_core.csv")

SINGLE_OUT = Path("results/graphs/task2/hcit_comparison/single")
FOUR_OUT = Path("results/graphs/task2/hcit_comparison/four_core")

POLICIES = ["lru", "srrip", "drrip", "ship", "mru", "random", "hcit"]
LABELS = {"lru":"LRU","srrip":"SRRIP","drrip":"DRRIP","ship":"SHIP","mru":"MRU","random":"Random","hcit":"HCIT"}
SIZES = [1, 2, 4, 8]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def read_csv(path: Path):
    if not path.is_file():
        fail(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        fail(f"No rows in {path}")
    return rows


def prepare(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob("*.png"):
        old.unlink()


def summary_index(rows):
    indexed = {(row["replacement_policy"].lower(), int(row["llc_size_mb"])): row for row in rows}
    missing = [(p, s) for p in POLICIES for s in SIZES if (p, s) not in indexed]
    if missing:
        fail(f"Missing summary combinations: {missing}")
    return indexed


def trend(output, indexed, field, title, ylabel, filename, scientific=False):
    fig, ax = plt.subplots(figsize=(11, 7))
    for policy in POLICIES:
        ax.plot(SIZES, [float(indexed[(policy, size)][field]) for size in SIZES], label=LABELS[policy])
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


def grouped(output, categories, values, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(16, 8))
    x = list(range(len(categories)))
    width = 0.84 / len(POLICIES)
    for index, policy in enumerate(POLICIES):
        offset = (index - (len(POLICIES) - 1) / 2) * width
        ax.bar([value + offset for value in x], values[policy], width, label=LABELS[policy])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def hcit_internal_graph(output, sizes, values, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sizes, values)
    ax.set_title(title)
    ax.set_xlabel("LLC size (MB)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sizes)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def hcit_dual_graph(output, sizes, first, second, first_label, second_label, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sizes, first, label=first_label)
    ax.plot(sizes, second, label=second_label)
    ax.set_title(title)
    ax.set_xlabel("LLC size (MB)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sizes)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def aggregate_internal(rows, scope):
    grouped_rows = defaultdict(list)
    for row in rows:
        grouped_rows[int(row["llc_size_mb"])].append(row)

    result = {}
    for size in SIZES:
        group = grouped_rows[size]
        if not group:
            fail(f"No HCIT internal rows at {size} MB for {scope}")
        result[size] = {
            "final_threshold": sum(float(r["final_threshold"]) for r in group) / len(group),
            "occupancy_percent": sum(float(r["occupancy_percent"]) for r in group) / len(group),
            "protected_utility_percent": sum(float(r["protected_utility_percent"]) for r in group) / len(group),
            "admissions": sum(float(r["admissions"]) for r in group),
            "protected_hits": sum(float(r["protected_hits"]) for r in group),
            "protected_evictions": sum(float(r["protected_evictions"]) for r in group),
            "protected_fills": sum(float(r["protected_fills"]) for r in group),
            "normal_fills": sum(float(r["normal_fills"]) for r in group),
        }
    return result


def generate_single():
    detail = read_csv(SINGLE_DETAIL)
    summary = read_csv(SINGLE_SUMMARY)
    internal = read_csv(INTERNAL_SINGLE)
    prepare(SINGLE_OUT)

    indexed = summary_index(summary)
    specs = [
        ("geomean_ipc","Single-Core Geometric-Mean IPC Including HCIT","Geometric-mean IPC","01_geomean_ipc.png",False),
        ("weighted_llc_miss_percent","Single-Core LLC Miss Percentage Including HCIT","LLC miss (%)","02_llc_miss.png",False),
        ("weighted_llc_hit_rate_percent","Single-Core LLC Hit Rate Including HCIT","LLC hit rate (%)","03_llc_hit_rate.png",False),
        ("weighted_l1_combined_miss_percent","Single-Core L1 Miss Percentage Including HCIT","L1 miss (%)","04_l1_miss.png",False),
        ("weighted_l2_miss_percent","Single-Core L2 Miss Percentage Including HCIT","L2 miss (%)","05_l2_miss.png",False),
        ("total_llc_write_requests","Single-Core LLC Writes Including HCIT","LLC write requests","06_llc_writes.png",True),
        ("average_real_seconds","Single-Core Execution Time Including HCIT","Execution time (seconds)","07_execution_time.png",False),
    ]
    for field, title, ylabel, filename, scientific in specs:
        trend(SINGLE_OUT, indexed, field, title, ylabel, filename, scientific)

    traces = sorted({row["trace"].replace(".champsimtrace.xz", "") for row in detail})
    detailed = {}
    for row in detail:
        detailed[(int(row["llc_size_mb"]), row["replacement_policy"].lower(), row["trace"].replace(".champsimtrace.xz", ""))] = row
    for number, size in enumerate(SIZES, start=8):
        grouped(
            SINGLE_OUT, traces,
            {policy: [float(detailed[(size, policy, trace)]["ipc"]) for trace in traces] for policy in POLICIES},
            f"Single-Core Per-Trace IPC Including HCIT at {size} MB",
            "IPC", f"{number:02d}_per_trace_ipc_{size}mb.png",
        )

    agg = aggregate_internal(internal, "single-core")
    hcit_internal_graph(SINGLE_OUT, SIZES, [agg[s]["final_threshold"] for s in SIZES],
                        "HCIT Average Final Threshold: Single-Core", "Threshold",
                        "12_hcit_final_threshold.png")
    hcit_internal_graph(SINGLE_OUT, SIZES, [agg[s]["occupancy_percent"] for s in SIZES],
                        "HCIT Average Occupancy: Single-Core", "Occupancy (%)",
                        "13_hcit_occupancy.png")
    hcit_internal_graph(SINGLE_OUT, SIZES, [agg[s]["protected_utility_percent"] for s in SIZES],
                        "HCIT Protection Utility: Single-Core", "Protected utility (%)",
                        "14_hcit_utility.png")
    hcit_internal_graph(SINGLE_OUT, SIZES, [agg[s]["admissions"] for s in SIZES],
                        "HCIT Total Admissions: Single-Core", "Admissions across four traces",
                        "15_hcit_admissions.png")
    hcit_dual_graph(SINGLE_OUT, SIZES, [agg[s]["protected_hits"] for s in SIZES],
                    [agg[s]["protected_evictions"] for s in SIZES],
                    "Protected hits", "Protected evictions",
                    "HCIT Protected Hits and Evictions: Single-Core", "Events",
                    "16_hcit_hits_evictions.png")
    hcit_dual_graph(SINGLE_OUT, SIZES, [agg[s]["protected_fills"] for s in SIZES],
                    [agg[s]["normal_fills"] for s in SIZES],
                    "Protected fills", "Normal fills",
                    "HCIT Fill Classification: Single-Core", "Fills",
                    "17_hcit_fills.png")


def generate_four():
    per_core = read_csv(FOUR_PER_CORE)
    summary = read_csv(FOUR_SUMMARY)
    internal = read_csv(INTERNAL_FOUR)
    prepare(FOUR_OUT)

    indexed = summary_index(summary)
    specs = [
        ("sum_ipc","Four-Core Aggregate IPC Including HCIT","Sum IPC","01_sum_ipc.png",False),
        ("llc_miss_percent","Four-Core LLC Miss Percentage Including HCIT","LLC miss (%)","02_llc_miss.png",False),
        ("llc_hit_rate_percent","Four-Core LLC Hit Rate Including HCIT","LLC hit rate (%)","03_llc_hit_rate.png",False),
        ("weighted_l1_combined_miss_percent","Four-Core L1 Miss Percentage Including HCIT","L1 miss (%)","04_l1_miss.png",False),
        ("weighted_l2_miss_percent","Four-Core L2 Miss Percentage Including HCIT","L2 miss (%)","05_l2_miss.png",False),
        ("llc_total_write_requests","Four-Core LLC Writes Including HCIT","LLC write requests","06_llc_writes.png",True),
        ("run_real_seconds","Four-Core Execution Time Including HCIT","Execution time (seconds)","07_execution_time.png",False),
    ]
    for field, title, ylabel, filename, scientific in specs:
        trend(FOUR_OUT, indexed, field, title, ylabel, filename, scientific)

    detailed = {}
    for row in per_core:
        detailed[(int(row["llc_size_mb"]), row["replacement_policy"].lower(), int(row["core"]))] = row
    for number, size in enumerate(SIZES, start=8):
        grouped(
            FOUR_OUT, [f"Core {core}" for core in range(4)],
            {policy: [float(detailed[(size, policy, core)]["ipc"]) for core in range(4)] for policy in POLICIES},
            f"Four-Core Per-Core IPC Including HCIT at {size} MB",
            "IPC", f"{number:02d}_per_core_ipc_{size}mb.png",
        )

    agg = aggregate_internal(internal, "four-core")
    hcit_internal_graph(FOUR_OUT, SIZES, [agg[s]["final_threshold"] for s in SIZES],
                        "HCIT Final Threshold: Four-Core", "Threshold",
                        "12_hcit_final_threshold.png")
    hcit_internal_graph(FOUR_OUT, SIZES, [agg[s]["occupancy_percent"] for s in SIZES],
                        "HCIT Occupancy: Four-Core", "Occupancy (%)",
                        "13_hcit_occupancy.png")
    hcit_internal_graph(FOUR_OUT, SIZES, [agg[s]["protected_utility_percent"] for s in SIZES],
                        "HCIT Protection Utility: Four-Core", "Protected utility (%)",
                        "14_hcit_utility.png")
    hcit_internal_graph(FOUR_OUT, SIZES, [agg[s]["admissions"] for s in SIZES],
                        "HCIT Admissions: Four-Core", "Admissions",
                        "15_hcit_admissions.png")
    hcit_dual_graph(FOUR_OUT, SIZES, [agg[s]["protected_hits"] for s in SIZES],
                    [agg[s]["protected_evictions"] for s in SIZES],
                    "Protected hits", "Protected evictions",
                    "HCIT Protected Hits and Evictions: Four-Core", "Events",
                    "16_hcit_hits_evictions.png")
    hcit_dual_graph(FOUR_OUT, SIZES, [agg[s]["protected_fills"] for s in SIZES],
                    [agg[s]["normal_fills"] for s in SIZES],
                    "Protected fills", "Normal fills",
                    "HCIT Fill Classification: Four-Core", "Fills",
                    "17_hcit_fills.png")


def main() -> int:
    generate_single()
    generate_four()
    single_count = len(list(SINGLE_OUT.glob("*.png")))
    four_count = len(list(FOUR_OUT.glob("*.png")))
    print("HCIT comparison graphs generated.")
    print(f"Single-core graphs: {single_count}")
    print(f"Four-core graphs:   {four_count}")
    print(f"Total graphs:       {single_count + four_count}")
    if single_count != 17 or four_count != 17:
        fail("Expected 17 graphs in each HCIT comparison directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
