#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

SINGLE_MANIFEST = Path(
    "results/raw/task2/llc_size/single/run_manifest.csv"
)
FOUR_MANIFEST = Path(
    "results/raw/task2/llc_size/four_core/run_manifest.csv"
)

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


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def to_int(value: str) -> int:
    return int(value.replace(",", ""))


def percentage(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return 100.0 * numerator / denominator


def geometric_mean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        fail("Geometric mean requires positive IPC values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Manifest not found: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No data rows in manifest: {path}")

    return rows


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> None:
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
        fail(f"Missing final IPC for cores {sorted(missing)} in {path}")

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

    # This ChampSim version prints private-cache totals without CPU
    # prefixes. The last expected_cores entries are the ROI values
    # corresponding to CPU 0 through CPU expected_cores - 1.
    for cache in ("L1I", "L1D", "L2C"):
        missing_cores = [
            cpu
            for cpu in range(expected_cores)
            if cache not in private[cpu]
        ]

        if missing_cores:
            candidates = unprefixed_private.get(cache, [])

            if len(candidates) < expected_cores:
                nearby = [
                    line
                    for line in text.splitlines()
                    if cache in line.upper() and "TOTAL" in line.upper()
                ][-12:]

                fail(
                    f"Expected at least {expected_cores} unprefixed "
                    f"{cache} TOTAL lines in {path}, found "
                    f"{len(candidates)}. Nearby lines: {nearby}"
                )

            roi_group = candidates[-expected_cores:]

            for cpu in range(expected_cores):
                private[cpu][cache] = roi_group[cpu]

    if not shared_candidates:
        nearby = [
            line
            for line in text.splitlines()
            if "LLC" in line.upper()
        ][-12:]

        fail(
            f"Missing LLC TOTAL in {path}. "
            f"Nearby LLC lines: {nearby}"
        )

    # The final LLC entry belongs to the region of interest.
    shared = {"LLC": shared_candidates[-1]}

    return private, shared

def parse_llc_operations(
    text: str,
) -> dict[str, dict[str, int]]:
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


def private_metrics(
    caches: dict[str, dict[str, int]],
) -> dict[str, object]:
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
        "l1i_miss_percent": percentage(
            l1i["misses"], l1i["accesses"]
        ),
        "l1d_accesses": l1d["accesses"],
        "l1d_hits": l1d["hits"],
        "l1d_misses": l1d["misses"],
        "l1d_miss_percent": percentage(
            l1d["misses"], l1d["accesses"]
        ),
        "l1_combined_accesses": l1_accesses,
        "l1_combined_hits": l1_hits,
        "l1_combined_misses": l1_misses,
        "l1_combined_miss_percent": percentage(
            l1_misses, l1_accesses
        ),
        "l2_accesses": l2["accesses"],
        "l2_hits": l2["hits"],
        "l2_misses": l2["misses"],
        "l2_miss_percent": percentage(
            l2["misses"], l2["accesses"]
        ),
    }


def llc_metrics(
    llc: dict[str, int],
    operations: dict[str, dict[str, int]],
) -> dict[str, object]:
    rfo_accesses = operations.get("RFO", {}).get("accesses", 0)
    writeback_accesses = operations.get(
        "WRITEBACK", {}
    ).get("accesses", 0)

    return {
        "llc_accesses": llc["accesses"],
        "llc_hits": llc["hits"],
        "llc_misses": llc["misses"],
        "llc_miss_percent": percentage(
            llc["misses"], llc["accesses"]
        ),
        "llc_hit_rate_percent": percentage(
            llc["hits"], llc["accesses"]
        ),
        "llc_rfo_accesses": rfo_accesses,
        "llc_writeback_accesses": writeback_accesses,
        "llc_total_write_requests": (
            rfo_accesses + writeback_accesses
        ),
    }


def weighted_percent(
    rows: list[dict[str, object]],
    miss_field: str,
    access_field: str,
) -> float:
    misses = sum(int(row[miss_field]) for row in rows)
    accesses = sum(int(row[access_field]) for row in rows)
    return percentage(misses, accesses)


def parse_single() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    manifest_rows = read_csv(SINGLE_MANIFEST)

    if len(manifest_rows) != 16:
        fail(
            "Expected 16 LLC-size single-core runs, "
            f"found {len(manifest_rows)}"
        )

    detail_rows: list[dict[str, object]] = []

    for manifest in manifest_rows:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])

        if not result_path.is_file():
            fail(f"Result file not found: {result_path}")

        text = result_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        ipc = parse_ipc(text, 1, result_path)
        private, shared = parse_cache_totals(
            text, 1, result_path
        )
        operations = parse_llc_operations(text)
        timing = parse_timing(timing_path)

        row: dict[str, object] = {
            "predictor": manifest["predictor"],
            "llc_size_mb": int(manifest["llc_size_mb"]),
            "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(
                manifest["llc_associativity"]
            ),
            "block_size_bytes": int(
                manifest["block_size_bytes"]
            ),
            "trace": manifest["trace"],
            "ipc": ipc[0],
            **private_metrics(private[0]),
            **llc_metrics(shared["LLC"], operations),
            "real_seconds": timing["real"],
            "user_seconds": timing["user"],
            "sys_seconds": timing["sys"],
            "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        }

        detail_rows.append(row)

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)

    for row in detail_rows:
        grouped[int(row["llc_size_mb"])].append(row)

    summary_rows: list[dict[str, object]] = []

    for size_mb in sorted(grouped):
        rows = grouped[size_mb]
        first = rows[0]
        ipc_values = [float(row["ipc"]) for row in rows]
        real_values = [
            float(row["real_seconds"]) for row in rows
        ]

        summary_rows.append({
            "predictor": first["predictor"],
            "llc_size_mb": size_mb,
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
                rows,
                "l1_combined_misses",
                "l1_combined_accesses",
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
                int(row["llc_writeback_accesses"])
                for row in rows
            ),
            "total_llc_write_requests": sum(
                int(row["llc_total_write_requests"])
                for row in rows
            ),
            "average_real_seconds": mean(real_values),
            "total_real_seconds": sum(real_values),
        })

    return detail_rows, summary_rows


def parse_four_core() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    manifest_rows = read_csv(FOUR_MANIFEST)

    if len(manifest_rows) != 4:
        fail(
            "Expected four LLC-size four-core runs, "
            f"found {len(manifest_rows)}"
        )

    per_core_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for manifest in manifest_rows:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])

        if not result_path.is_file():
            fail(f"Result file not found: {result_path}")

        text = result_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        ipc = parse_ipc(text, 4, result_path)
        private, shared = parse_cache_totals(
            text, 4, result_path
        )
        operations = parse_llc_operations(text)
        timing = parse_timing(timing_path)

        traces = [
            manifest["core0_trace"],
            manifest["core1_trace"],
            manifest["core2_trace"],
            manifest["core3_trace"],
        ]

        current_rows: list[dict[str, object]] = []

        for core in range(4):
            row: dict[str, object] = {
                "predictor": manifest["predictor"],
                "llc_size_mb": int(manifest["llc_size_mb"]),
                "llc_sets": int(manifest["llc_sets"]),
                "llc_associativity": int(
                    manifest["llc_associativity"]
                ),
                "block_size_bytes": int(
                    manifest["block_size_bytes"]
                ),
                "mix_number": int(manifest["mix_number"]),
                "core": core,
                "trace": traces[core],
                "ipc": ipc[core],
                **private_metrics(private[core]),
                "result_file": manifest["result_file"],
            }

            current_rows.append(row)
            per_core_rows.append(row)

        ipc_values = [ipc[core] for core in range(4)]
        llc = llc_metrics(shared["LLC"], operations)
        first = current_rows[0]

        summary_rows.append({
            "predictor": manifest["predictor"],
            "llc_size_mb": int(manifest["llc_size_mb"]),
            "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(
                manifest["llc_associativity"]
            ),
            "block_size_bytes": int(
                manifest["block_size_bytes"]
            ),
            "mix_number": int(manifest["mix_number"]),
            "core_count": 4,
            "average_ipc": mean(ipc_values),
            "geomean_ipc": geometric_mean(ipc_values),
            "sum_ipc": sum(ipc_values),
            "weighted_l1i_miss_percent": weighted_percent(
                current_rows,
                "l1i_misses",
                "l1i_accesses",
            ),
            "weighted_l1d_miss_percent": weighted_percent(
                current_rows,
                "l1d_misses",
                "l1d_accesses",
            ),
            "weighted_l1_combined_miss_percent": weighted_percent(
                current_rows,
                "l1_combined_misses",
                "l1_combined_accesses",
            ),
            "weighted_l2_miss_percent": weighted_percent(
                current_rows,
                "l2_misses",
                "l2_accesses",
            ),
            **llc,
            "run_real_seconds": timing["real"],
            "run_user_seconds": timing["user"],
            "run_sys_seconds": timing["sys"],
            "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        })

    return per_core_rows, summary_rows


def main() -> int:
    single_detail, single_summary = parse_single()
    four_per_core, four_summary = parse_four_core()

    single_detail.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            str(row["trace"]),
        )
    )
    single_summary.sort(
        key=lambda row: int(row["llc_size_mb"])
    )
    four_per_core.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            int(row["core"]),
        )
    )
    four_summary.sort(
        key=lambda row: int(row["llc_size_mb"])
    )

    write_csv(
        SINGLE_DETAIL,
        single_detail,
        SINGLE_DETAIL_FIELDS,
    )
    write_csv(
        SINGLE_SUMMARY,
        single_summary,
        SINGLE_SUMMARY_FIELDS,
    )
    write_csv(
        FOUR_PER_CORE,
        four_per_core,
        FOUR_PER_CORE_FIELDS,
    )
    write_csv(
        FOUR_SUMMARY,
        four_summary,
        FOUR_SUMMARY_FIELDS,
    )

    print("Task 2 LLC size results parsed successfully.")
    print(f"Single-core detailed rows: {len(single_detail)}")
    print(f"Single-core summary rows:  {len(single_summary)}")
    print(f"Four-core per-core rows:   {len(four_per_core)}")
    print(f"Four-core summary rows:    {len(four_summary)}")
    print()
    print(
        f"{'LLC':>6}  {'Single Avg IPC':>14}  "
        f"{'Single LLC Miss%':>17}  "
        f"{'4C Sum IPC':>10}  "
        f"{'4C LLC Miss%':>12}  "
        f"{'4C Time(s)':>10}"
    )

    four_by_size = {
        int(row["llc_size_mb"]): row
        for row in four_summary
    }

    for single in single_summary:
        size = int(single["llc_size_mb"])
        four = four_by_size[size]

        print(
            f"{size:>4}MB  "
            f"{float(single['average_ipc']):>14.5f}  "
            f"{float(single['weighted_llc_miss_percent']):>17.5f}  "
            f"{float(four['sum_ipc']):>10.5f}  "
            f"{float(four['llc_miss_percent']):>12.5f}  "
            f"{float(four['run_real_seconds']):>10.3f}"
        )

    print()
    print(f"Detailed CSV: {SINGLE_DETAIL}")
    print(f"Summary CSV:  {SINGLE_SUMMARY}")
    print(f"Per-core CSV: {FOUR_PER_CORE}")
    print(f"4-core CSV:   {FOUR_SUMMARY}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
