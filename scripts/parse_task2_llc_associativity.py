#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

BASE_SINGLE_DETAIL = Path(
    "results/csv/task2_llc_size_single_results.csv"
)
BASE_SINGLE_SUMMARY = Path(
    "results/csv/task2_llc_size_single_summary.csv"
)
BASE_FOUR_PER_CORE = Path(
    "results/csv/task2_llc_size_four_core_per_core_results.csv"
)
BASE_FOUR_SUMMARY = Path(
    "results/csv/task2_llc_size_four_core_summary.csv"
)

EIGHT_SINGLE_MANIFEST = Path(
    "results/raw/task2/llc_associativity/8way/single/run_manifest.csv"
)
EIGHT_FOUR_MANIFEST = Path(
    "results/raw/task2/llc_associativity/8way/four_core/run_manifest.csv"
)

OUT_SINGLE_DETAIL = Path(
    "results/csv/task2_llc_associativity_single_results.csv"
)
OUT_SINGLE_SUMMARY = Path(
    "results/csv/task2_llc_associativity_single_summary.csv"
)
OUT_FOUR_PER_CORE = Path(
    "results/csv/task2_llc_associativity_four_core_per_core_results.csv"
)
OUT_FOUR_SUMMARY = Path(
    "results/csv/task2_llc_associativity_four_core_summary.csv"
)
OUT_SINGLE_COMPARISON = Path(
    "results/csv/task2_llc_associativity_single_comparison.csv"
)
OUT_FOUR_COMPARISON = Path(
    "results/csv/task2_llc_associativity_four_core_comparison.csv"
)

NUMBER = r"[0-9][0-9,]*"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

IPC_RE = re.compile(
    rf"CPU\s+(\d+)\s+cumulative IPC:\s*({FLOAT})",
    re.IGNORECASE,
)

CACHE_TOTAL_RE = re.compile(
    rf"^\s*(?:CPU\s+(\d+)\s+)?"
    rf"(L1I|L1D|L2C|LLC)\s+TOTAL\s+"
    rf"ACCESS:\s*({NUMBER})\s+"
    rf"HIT:\s*({NUMBER})\s+"
    rf"MISS:\s*({NUMBER})",
    re.IGNORECASE | re.MULTILINE,
)

CACHE_OPERATION_RE = re.compile(
    rf"^\s*(?:CPU\s+(\d+)\s+)?"
    rf"(L1I|L1D|L2C|LLC)\s+"
    rf"(LOAD|RFO|PREFETCH|WRITEBACK)\s+"
    rf"ACCESS:\s*({NUMBER})\s+"
    rf"HIT:\s*({NUMBER})\s+"
    rf"MISS:\s*({NUMBER})",
    re.IGNORECASE | re.MULTILINE,
)

SINGLE_DETAIL_FIELDS = [
    "predictor",
    "llc_size_mb",
    "llc_sets",
    "llc_associativity",
    "block_size_bytes",
    "trace",
    "ipc",
    "l1i_accesses",
    "l1i_hits",
    "l1i_misses",
    "l1i_miss_percent",
    "l1d_accesses",
    "l1d_hits",
    "l1d_misses",
    "l1d_miss_percent",
    "l1_combined_accesses",
    "l1_combined_hits",
    "l1_combined_misses",
    "l1_combined_miss_percent",
    "l2_accesses",
    "l2_hits",
    "l2_misses",
    "l2_miss_percent",
    "llc_accesses",
    "llc_hits",
    "llc_misses",
    "llc_miss_percent",
    "llc_hit_rate_percent",
    "llc_rfo_accesses",
    "llc_writeback_accesses",
    "llc_total_write_requests",
    "real_seconds",
    "user_seconds",
    "sys_seconds",
    "result_file",
    "timing_file",
]

SINGLE_SUMMARY_FIELDS = [
    "predictor",
    "llc_size_mb",
    "llc_sets",
    "llc_associativity",
    "block_size_bytes",
    "trace_count",
    "average_ipc",
    "geomean_ipc",
    "weighted_l1i_miss_percent",
    "weighted_l1d_miss_percent",
    "weighted_l1_combined_miss_percent",
    "weighted_l2_miss_percent",
    "weighted_llc_miss_percent",
    "weighted_llc_hit_rate_percent",
    "total_llc_rfo_accesses",
    "total_llc_writeback_accesses",
    "total_llc_write_requests",
    "average_real_seconds",
    "total_real_seconds",
]

FOUR_PER_CORE_FIELDS = [
    "predictor",
    "llc_size_mb",
    "llc_sets",
    "llc_associativity",
    "block_size_bytes",
    "mix_number",
    "core",
    "trace",
    "ipc",
    "l1i_accesses",
    "l1i_hits",
    "l1i_misses",
    "l1i_miss_percent",
    "l1d_accesses",
    "l1d_hits",
    "l1d_misses",
    "l1d_miss_percent",
    "l1_combined_accesses",
    "l1_combined_hits",
    "l1_combined_misses",
    "l1_combined_miss_percent",
    "l2_accesses",
    "l2_hits",
    "l2_misses",
    "l2_miss_percent",
    "result_file",
]

FOUR_SUMMARY_FIELDS = [
    "predictor",
    "llc_size_mb",
    "llc_sets",
    "llc_associativity",
    "block_size_bytes",
    "mix_number",
    "core_count",
    "average_ipc",
    "geomean_ipc",
    "sum_ipc",
    "weighted_l1i_miss_percent",
    "weighted_l1d_miss_percent",
    "weighted_l1_combined_miss_percent",
    "weighted_l2_miss_percent",
    "llc_accesses",
    "llc_hits",
    "llc_misses",
    "llc_miss_percent",
    "llc_hit_rate_percent",
    "llc_rfo_accesses",
    "llc_writeback_accesses",
    "llc_total_write_requests",
    "run_real_seconds",
    "run_user_seconds",
    "run_sys_seconds",
    "result_file",
    "timing_file",
]

COMPARISON_FIELDS = [
    "metric",
    "value_16way",
    "value_8way",
    "absolute_change_8way_minus_16way",
    "percent_change_from_16way",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def to_int(value: str) -> int:
    return int(value.replace(",", ""))


def percentage(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else 100.0 * numerator / denominator


def percent_change(new_value: float, old_value: float) -> float:
    if old_value == 0:
        return 0.0
    return 100.0 * (new_value - old_value) / old_value


def geometric_mean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        fail("Geometric mean requires positive IPC values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV file: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No rows found in {path}")

    return rows


def write_csv(path: Path, rows, fieldnames) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_timing(path: Path) -> dict[str, float]:
    if not path.is_file():
        fail(f"Timing file not found: {path}")

    values: dict[str, float] = {}

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        parts = line.split()

        if len(parts) == 2 and parts[0] in {"real", "user", "sys"}:
            values[parts[0]] = float(parts[1])

    missing = {"real", "user", "sys"} - values.keys()

    if missing:
        fail(f"Missing timing values {sorted(missing)} in {path}")

    return values


def parse_ipc(text: str, expected_cores: int, path: Path) -> dict[int, float]:
    values: dict[int, float] = {}

    for core_text, ipc_text in IPC_RE.findall(text):
        core = int(core_text)
        if core < expected_cores:
            values[core] = float(ipc_text)

    missing = set(range(expected_cores)) - values.keys()

    if missing:
        fail(f"Missing IPC for cores {sorted(missing)} in {path}")

    return values


def parse_cache_totals(
    text: str,
    expected_cores: int,
    path: Path,
) -> tuple[
    dict[int, dict[str, dict[str, int]]],
    dict[str, dict[str, int]],
]:
    private: dict[int, dict[str, dict[str, int]]] = defaultdict(dict)
    unprefixed_private: dict[str, list[dict[str, int]]] = defaultdict(list)
    shared_candidates: list[dict[str, int]] = []

    for cpu_text, cache_text, access_text, hit_text, miss_text in (
        CACHE_TOTAL_RE.findall(text)
    ):
        cache = cache_text.upper()
        stats = {
            "accesses": to_int(access_text),
            "hits": to_int(hit_text),
            "misses": to_int(miss_text),
        }

        if cache == "LLC":
            shared_candidates.append(stats)
            continue

        if cpu_text:
            cpu = int(cpu_text)
            if cpu < expected_cores:
                private[cpu][cache] = stats
        else:
            unprefixed_private[cache].append(stats)

    for cache in ("L1I", "L1D", "L2C"):
        missing_cores = [
            cpu
            for cpu in range(expected_cores)
            if cache not in private[cpu]
        ]

        if missing_cores:
            candidates = unprefixed_private.get(cache, [])

            if len(candidates) < expected_cores:
                fail(
                    f"Expected at least {expected_cores} unprefixed "
                    f"{cache} TOTAL lines in {path}, found {len(candidates)}"
                )

            roi_group = candidates[-expected_cores:]

            for cpu in range(expected_cores):
                private[cpu][cache] = roi_group[cpu]

    if not shared_candidates:
        fail(f"Missing LLC TOTAL in {path}")

    return private, {"LLC": shared_candidates[-1]}


def parse_llc_operations(text: str) -> dict[str, dict[str, int]]:
    operations: dict[str, dict[str, int]] = {}

    for _, cache_text, operation_text, access_text, hit_text, miss_text in (
        CACHE_OPERATION_RE.findall(text)
    ):
        if cache_text.upper() != "LLC":
            continue

        operations[operation_text.upper()] = {
            "accesses": to_int(access_text),
            "hits": to_int(hit_text),
            "misses": to_int(miss_text),
        }

    return operations


def private_metrics(caches: dict[str, dict[str, int]]) -> dict[str, object]:
    l1i = caches["L1I"]
    l1d = caches["L1D"]
    l2 = caches["L2C"]

    l1_accesses = l1i["accesses"] + l1d["accesses"]
    l1_hits = l1i["hits"] + l1d["hits"]
    l1_misses = l1i["misses"] + l1d["misses"]

    return {
        "l1i_accesses": l1i["accesses"],
        "l1i_hits": l1i["hits"],
        "l1i_misses": l1i["misses"],
        "l1i_miss_percent": percentage(l1i["misses"], l1i["accesses"]),
        "l1d_accesses": l1d["accesses"],
        "l1d_hits": l1d["hits"],
        "l1d_misses": l1d["misses"],
        "l1d_miss_percent": percentage(l1d["misses"], l1d["accesses"]),
        "l1_combined_accesses": l1_accesses,
        "l1_combined_hits": l1_hits,
        "l1_combined_misses": l1_misses,
        "l1_combined_miss_percent": percentage(l1_misses, l1_accesses),
        "l2_accesses": l2["accesses"],
        "l2_hits": l2["hits"],
        "l2_misses": l2["misses"],
        "l2_miss_percent": percentage(l2["misses"], l2["accesses"]),
    }


def llc_metrics(
    llc: dict[str, int],
    operations: dict[str, dict[str, int]],
) -> dict[str, object]:
    rfo = operations.get("RFO", {}).get("accesses", 0)
    writeback = operations.get("WRITEBACK", {}).get("accesses", 0)

    return {
        "llc_accesses": llc["accesses"],
        "llc_hits": llc["hits"],
        "llc_misses": llc["misses"],
        "llc_miss_percent": percentage(llc["misses"], llc["accesses"]),
        "llc_hit_rate_percent": percentage(llc["hits"], llc["accesses"]),
        "llc_rfo_accesses": rfo,
        "llc_writeback_accesses": writeback,
        "llc_total_write_requests": rfo + writeback,
    }


def weighted_percent(rows, miss_field: str, access_field: str) -> float:
    misses = sum(int(row[miss_field]) for row in rows)
    accesses = sum(int(row[access_field]) for row in rows)
    return percentage(misses, accesses)


def parse_eight_way_single():
    manifests = read_csv(EIGHT_SINGLE_MANIFEST)

    if len(manifests) != 4:
        fail(f"Expected four 8-way single-core runs, found {len(manifests)}")

    rows: list[dict[str, object]] = []

    for manifest in manifests:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])

        if not result_path.is_file():
            fail(f"Missing result file: {result_path}")

        text = result_path.read_text(encoding="utf-8", errors="replace")

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        ipc = parse_ipc(text, 1, result_path)
        private, shared = parse_cache_totals(text, 1, result_path)
        operations = parse_llc_operations(text)
        timing = parse_timing(timing_path)

        rows.append({
            "predictor": manifest["predictor"],
            "llc_size_mb": int(manifest["llc_size_mb"]),
            "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(manifest["llc_associativity"]),
            "block_size_bytes": int(manifest["block_size_bytes"]),
            "trace": manifest["trace"],
            "ipc": ipc[0],
            **private_metrics(private[0]),
            **llc_metrics(shared["LLC"], operations),
            "real_seconds": timing["real"],
            "user_seconds": timing["user"],
            "sys_seconds": timing["sys"],
            "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        })

    return rows


def summarize_single(rows):
    ipc_values = [float(row["ipc"]) for row in rows]
    real_values = [float(row["real_seconds"]) for row in rows]
    first = rows[0]

    return {
        "predictor": first["predictor"],
        "llc_size_mb": first["llc_size_mb"],
        "llc_sets": first["llc_sets"],
        "llc_associativity": first["llc_associativity"],
        "block_size_bytes": first["block_size_bytes"],
        "trace_count": len(rows),
        "average_ipc": mean(ipc_values),
        "geomean_ipc": geometric_mean(ipc_values),
        "weighted_l1i_miss_percent": weighted_percent(
            rows, "l1i_misses", "l1i_accesses"
        ),
        "weighted_l1d_miss_percent": weighted_percent(
            rows, "l1d_misses", "l1d_accesses"
        ),
        "weighted_l1_combined_miss_percent": weighted_percent(
            rows, "l1_combined_misses", "l1_combined_accesses"
        ),
        "weighted_l2_miss_percent": weighted_percent(
            rows, "l2_misses", "l2_accesses"
        ),
        "weighted_llc_miss_percent": weighted_percent(
            rows, "llc_misses", "llc_accesses"
        ),
        "weighted_llc_hit_rate_percent": percentage(
            sum(int(row["llc_hits"]) for row in rows),
            sum(int(row["llc_accesses"]) for row in rows),
        ),
        "total_llc_rfo_accesses": sum(
            int(row["llc_rfo_accesses"]) for row in rows
        ),
        "total_llc_writeback_accesses": sum(
            int(row["llc_writeback_accesses"]) for row in rows
        ),
        "total_llc_write_requests": sum(
            int(row["llc_total_write_requests"]) for row in rows
        ),
        "average_real_seconds": mean(real_values),
        "total_real_seconds": sum(real_values),
    }


def parse_eight_way_four():
    manifests = read_csv(EIGHT_FOUR_MANIFEST)

    if len(manifests) != 1:
        fail(f"Expected one 8-way four-core run, found {len(manifests)}")

    manifest = manifests[0]
    result_path = Path(manifest["result_file"])
    timing_path = Path(manifest["timing_file"])

    if not result_path.is_file():
        fail(f"Missing result file: {result_path}")

    text = result_path.read_text(encoding="utf-8", errors="replace")

    if "ChampSim completed all CPUs" not in text:
        fail(f"Completion marker missing from {result_path}")

    ipc = parse_ipc(text, 4, result_path)
    private, shared = parse_cache_totals(text, 4, result_path)
    operations = parse_llc_operations(text)
    timing = parse_timing(timing_path)

    traces = [
        manifest["core0_trace"],
        manifest["core1_trace"],
        manifest["core2_trace"],
        manifest["core3_trace"],
    ]

    per_core_rows = []

    for core in range(4):
        per_core_rows.append({
            "predictor": manifest["predictor"],
            "llc_size_mb": int(manifest["llc_size_mb"]),
            "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(manifest["llc_associativity"]),
            "block_size_bytes": int(manifest["block_size_bytes"]),
            "mix_number": int(manifest["mix_number"]),
            "core": core,
            "trace": traces[core],
            "ipc": ipc[core],
            **private_metrics(private[core]),
            "result_file": manifest["result_file"],
        })

    ipc_values = [ipc[core] for core in range(4)]
    llc = llc_metrics(shared["LLC"], operations)

    summary = {
        "predictor": manifest["predictor"],
        "llc_size_mb": int(manifest["llc_size_mb"]),
        "llc_sets": int(manifest["llc_sets"]),
        "llc_associativity": int(manifest["llc_associativity"]),
        "block_size_bytes": int(manifest["block_size_bytes"]),
        "mix_number": int(manifest["mix_number"]),
        "core_count": 4,
        "average_ipc": mean(ipc_values),
        "geomean_ipc": geometric_mean(ipc_values),
        "sum_ipc": sum(ipc_values),
        "weighted_l1i_miss_percent": weighted_percent(
            per_core_rows, "l1i_misses", "l1i_accesses"
        ),
        "weighted_l1d_miss_percent": weighted_percent(
            per_core_rows, "l1d_misses", "l1d_accesses"
        ),
        "weighted_l1_combined_miss_percent": weighted_percent(
            per_core_rows, "l1_combined_misses", "l1_combined_accesses"
        ),
        "weighted_l2_miss_percent": weighted_percent(
            per_core_rows, "l2_misses", "l2_accesses"
        ),
        **llc,
        "run_real_seconds": timing["real"],
        "run_user_seconds": timing["user"],
        "run_sys_seconds": timing["sys"],
        "result_file": manifest["result_file"],
        "timing_file": manifest["timing_file"],
    }

    return per_core_rows, summary


def make_comparison(old_row, new_row, metrics):
    rows = []

    for metric in metrics:
        old_value = float(old_row[metric])
        new_value = float(new_row[metric])

        rows.append({
            "metric": metric,
            "value_16way": old_value,
            "value_8way": new_value,
            "absolute_change_8way_minus_16way": new_value - old_value,
            "percent_change_from_16way": percent_change(
                new_value, old_value
            ),
        })

    return rows


def main() -> int:
    baseline_single_detail = [
        row
        for row in read_csv(BASE_SINGLE_DETAIL)
        if int(row["llc_size_mb"]) == 4
        and int(row["llc_associativity"]) == 16
    ]
    baseline_single_summary_rows = [
        row
        for row in read_csv(BASE_SINGLE_SUMMARY)
        if int(row["llc_size_mb"]) == 4
        and int(row["llc_associativity"]) == 16
    ]
    baseline_four_per_core = [
        row
        for row in read_csv(BASE_FOUR_PER_CORE)
        if int(row["llc_size_mb"]) == 4
        and int(row["llc_associativity"]) == 16
    ]
    baseline_four_summary_rows = [
        row
        for row in read_csv(BASE_FOUR_SUMMARY)
        if int(row["llc_size_mb"]) == 4
        and int(row["llc_associativity"]) == 16
    ]

    if len(baseline_single_detail) != 4:
        fail("Expected four 4 MB, 16-way single-core baseline rows")
    if len(baseline_single_summary_rows) != 1:
        fail("Expected one 4 MB, 16-way single-core summary row")
    if len(baseline_four_per_core) != 4:
        fail("Expected four 4 MB, 16-way four-core baseline rows")
    if len(baseline_four_summary_rows) != 1:
        fail("Expected one 4 MB, 16-way four-core summary row")

    eight_single_detail = parse_eight_way_single()
    eight_single_summary = summarize_single(eight_single_detail)
    eight_four_per_core, eight_four_summary = parse_eight_way_four()

    combined_single_detail = (
        [dict(row) for row in baseline_single_detail]
        + eight_single_detail
    )
    combined_single_summary = (
        [dict(baseline_single_summary_rows[0])]
        + [eight_single_summary]
    )
    combined_four_per_core = (
        [dict(row) for row in baseline_four_per_core]
        + eight_four_per_core
    )
    combined_four_summary = (
        [dict(baseline_four_summary_rows[0])]
        + [eight_four_summary]
    )

    combined_single_detail.sort(
        key=lambda row: (
            int(row["llc_associativity"]),
            str(row["trace"]),
        ),
        reverse=True,
    )
    combined_single_summary.sort(
        key=lambda row: int(row["llc_associativity"]),
        reverse=True,
    )
    combined_four_per_core.sort(
        key=lambda row: (
            -int(row["llc_associativity"]),
            int(row["core"]),
        )
    )
    combined_four_summary.sort(
        key=lambda row: int(row["llc_associativity"]),
        reverse=True,
    )

    write_csv(
        OUT_SINGLE_DETAIL,
        combined_single_detail,
        SINGLE_DETAIL_FIELDS,
    )
    write_csv(
        OUT_SINGLE_SUMMARY,
        combined_single_summary,
        SINGLE_SUMMARY_FIELDS,
    )
    write_csv(
        OUT_FOUR_PER_CORE,
        combined_four_per_core,
        FOUR_PER_CORE_FIELDS,
    )
    write_csv(
        OUT_FOUR_SUMMARY,
        combined_four_summary,
        FOUR_SUMMARY_FIELDS,
    )

    single_metrics = [
        "average_ipc",
        "geomean_ipc",
        "weighted_l1_combined_miss_percent",
        "weighted_l2_miss_percent",
        "weighted_llc_miss_percent",
        "weighted_llc_hit_rate_percent",
        "total_llc_write_requests",
        "average_real_seconds",
    ]
    four_metrics = [
        "sum_ipc",
        "geomean_ipc",
        "weighted_l1_combined_miss_percent",
        "weighted_l2_miss_percent",
        "llc_miss_percent",
        "llc_hit_rate_percent",
        "llc_total_write_requests",
        "run_real_seconds",
    ]

    single_comparison = make_comparison(
        baseline_single_summary_rows[0],
        eight_single_summary,
        single_metrics,
    )
    four_comparison = make_comparison(
        baseline_four_summary_rows[0],
        eight_four_summary,
        four_metrics,
    )

    write_csv(
        OUT_SINGLE_COMPARISON,
        single_comparison,
        COMPARISON_FIELDS,
    )
    write_csv(
        OUT_FOUR_COMPARISON,
        four_comparison,
        COMPARISON_FIELDS,
    )

    print("Task 2 LLC associativity results parsed successfully.")
    print(f"Single-core detail rows:   {len(combined_single_detail)}")
    print(f"Single-core summary rows:  {len(combined_single_summary)}")
    print(f"Four-core per-core rows:   {len(combined_four_per_core)}")
    print(f"Four-core summary rows:    {len(combined_four_summary)}")
    print()
    print("Single-core 16-way vs 8-way:")
    for row in single_comparison:
        print(
            f"  {row['metric']:<38}"
            f"{float(row['value_16way']):>12.5f} -> "
            f"{float(row['value_8way']):>12.5f} "
            f"({float(row['percent_change_from_16way']):>8.3f}%)"
        )
    print()
    print("Four-core 16-way vs 8-way:")
    for row in four_comparison:
        print(
            f"  {row['metric']:<38}"
            f"{float(row['value_16way']):>12.5f} -> "
            f"{float(row['value_8way']):>12.5f} "
            f"({float(row['percent_change_from_16way']):>8.3f}%)"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
