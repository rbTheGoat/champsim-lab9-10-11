#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

# ---------------------------------------------------------------------------
# Existing LRU data from the completed LLC-size study
# ---------------------------------------------------------------------------

LRU_SINGLE_DETAIL = Path(
    "results/csv/task2_llc_size_single_results.csv"
)
LRU_SINGLE_SUMMARY = Path(
    "results/csv/task2_llc_size_single_summary.csv"
)
LRU_FOUR_PER_CORE = Path(
    "results/csv/task2_llc_size_four_core_per_core_results.csv"
)
LRU_FOUR_SUMMARY = Path(
    "results/csv/task2_llc_size_four_core_summary.csv"
)

# ---------------------------------------------------------------------------
# New SRRIP/DRRIP/SHIP/MRU/Random experiment manifests
# ---------------------------------------------------------------------------

NEW_SINGLE_MANIFEST = Path(
    "results/raw/task2/replacement_policy_size/single/run_manifest.csv"
)
NEW_FOUR_MANIFEST = Path(
    "results/raw/task2/replacement_policy_size/four_core/run_manifest.csv"
)

# ---------------------------------------------------------------------------
# Final merged outputs
# ---------------------------------------------------------------------------

OUT_SINGLE_DETAIL = Path(
    "results/csv/task2_replacement_policy_size_single_results_all_policies.csv"
)
OUT_SINGLE_SUMMARY = Path(
    "results/csv/task2_replacement_policy_size_single_summary_all_policies.csv"
)
OUT_FOUR_PER_CORE = Path(
    "results/csv/task2_replacement_policy_size_four_core_per_core_all_policies.csv"
)
OUT_FOUR_SUMMARY = Path(
    "results/csv/task2_replacement_policy_size_four_core_summary_all_policies.csv"
)
OUT_SINGLE_RANKING = Path(
    "results/csv/task2_replacement_policy_size_single_ranking.csv"
)
OUT_FOUR_RANKING = Path(
    "results/csv/task2_replacement_policy_size_four_core_ranking.csv"
)

POLICY_ORDER = [
    "lru",
    "srrip",
    "drrip",
    "ship",
    "mru",
    "random",
]
SIZE_ORDER = [1, 2, 4, 8]
EXPECTED_SINGLE_TRACES = 4
EXPECTED_FOUR_CORES = 4

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
    "replacement_policy",
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
    "replacement_policy",
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
    "replacement_policy",
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
    "replacement_policy",
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

SINGLE_RANKING_FIELDS = [
    "llc_size_mb",
    "ipc_rank",
    "replacement_policy",
    "geomean_ipc",
    "average_ipc",
    "weighted_llc_miss_percent",
    "weighted_llc_hit_rate_percent",
    "total_llc_write_requests",
    "average_real_seconds",
]

FOUR_RANKING_FIELDS = [
    "llc_size_mb",
    "ipc_rank",
    "replacement_policy",
    "sum_ipc",
    "geomean_ipc",
    "llc_miss_percent",
    "llc_hit_rate_percent",
    "llc_total_write_requests",
    "run_real_seconds",
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
    if not values:
        fail("Cannot calculate geometric mean of an empty list")

    if any(value <= 0 for value in values):
        fail(f"Geometric mean requires positive values: {values}")

    return math.exp(
        sum(math.log(value) for value in values) / len(values)
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV file: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No data rows found in {path}")

    return rows


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_timing(path: Path) -> dict[str, float]:
    if not path.is_file():
        fail(f"Missing timing file: {path}")

    values: dict[str, float] = {}

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        parts = line.split()

        if len(parts) == 2 and parts[0] in {"real", "user", "sys"}:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                fail(f"Invalid timing line in {path}: {line}")

    missing = {"real", "user", "sys"} - values.keys()

    if missing:
        fail(f"Missing timing values {sorted(missing)} in {path}")

    return values


def parse_ipc(
    text: str,
    expected_cores: int,
    path: Path,
) -> dict[int, float]:
    values: dict[int, float] = {}

    # Assignment overwrites earlier warm-up entries with final ROI entries.
    for core_text, ipc_text in IPC_RE.findall(text):
        core = int(core_text)

        if core < expected_cores:
            values[core] = float(ipc_text)

    missing = set(range(expected_cores)) - values.keys()

    if missing:
        nearby = [
            line
            for line in text.splitlines()
            if "cumulative IPC" in line
        ][-12:]

        fail(
            f"Missing cumulative IPC for CPU(s) {sorted(missing)} "
            f"in {path}. Nearby lines: {nearby}"
        )

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
    shared_llc_candidates: list[dict[str, int]] = []

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
            shared_llc_candidates.append(stats)
            continue

        if cpu_text:
            cpu = int(cpu_text)

            if cpu < expected_cores:
                # Last occurrence is the ROI value.
                private[cpu][cache] = stats
        else:
            unprefixed_private[cache].append(stats)

    # This old ChampSim version can print L1I/L1D/L2C totals without CPU
    # prefixes. The last expected_cores values are the ROI values for
    # cores 0 through expected_cores - 1.
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
                ][-16:]

                fail(
                    f"Expected at least {expected_cores} unprefixed "
                    f"{cache} TOTAL lines in {path}, found "
                    f"{len(candidates)}. Nearby lines: {nearby}"
                )

            roi_group = candidates[-expected_cores:]

            for cpu in range(expected_cores):
                private[cpu][cache] = roi_group[cpu]

    if not shared_llc_candidates:
        nearby = [
            line
            for line in text.splitlines()
            if "LLC" in line.upper()
        ][-16:]

        fail(
            f"Missing LLC TOTAL in {path}. Nearby lines: {nearby}"
        )

    # Final LLC TOTAL belongs to the ROI.
    shared = {"LLC": shared_llc_candidates[-1]}

    return private, shared


def parse_llc_operations(
    text: str,
) -> dict[str, dict[str, int]]:
    operations: dict[str, dict[str, int]] = {}

    # Last occurrence of each operation is the ROI value.
    for (
        _,
        cache_text,
        operation_text,
        access_text,
        hit_text,
        miss_text,
    ) in CACHE_OPERATION_RE.findall(text):
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
    for required in ("L1I", "L1D", "L2C"):
        if required not in caches:
            fail(f"Missing private-cache statistics for {required}")

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
        # Operational definition retained from the earlier parser.
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


def normalize_lru_single_detail() -> list[dict[str, object]]:
    rows = []

    for source in read_csv(LRU_SINGLE_DETAIL):
        row: dict[str, object] = dict(source)
        row["replacement_policy"] = "lru"
        rows.append(row)

    return rows


def normalize_lru_single_summary() -> list[dict[str, object]]:
    rows = []

    for source in read_csv(LRU_SINGLE_SUMMARY):
        row: dict[str, object] = dict(source)
        row["replacement_policy"] = "lru"
        rows.append(row)

    return rows


def normalize_lru_four_per_core() -> list[dict[str, object]]:
    rows = []

    for source in read_csv(LRU_FOUR_PER_CORE):
        row: dict[str, object] = dict(source)
        row["replacement_policy"] = "lru"
        rows.append(row)

    return rows


def normalize_lru_four_summary() -> list[dict[str, object]]:
    rows = []

    for source in read_csv(LRU_FOUR_SUMMARY):
        row: dict[str, object] = dict(source)
        row["replacement_policy"] = "lru"
        rows.append(row)

    return rows


def parse_new_single_detail() -> list[dict[str, object]]:
    manifests = read_csv(NEW_SINGLE_MANIFEST)

    if len(manifests) != 80:
        fail(
            f"Expected 80 non-LRU single-core manifest rows, "
            f"found {len(manifests)}"
        )

    rows: list[dict[str, object]] = []

    for manifest in manifests:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])

        if not result_path.is_file():
            fail(f"Missing simulator output: {result_path}")

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

        row = {
            "predictor": manifest["predictor"],
            "replacement_policy": manifest["replacement_policy"].lower(),
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

        rows.append(row)

    return rows


def summarize_single(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    if len(rows) != EXPECTED_SINGLE_TRACES:
        fail(
            f"Expected {EXPECTED_SINGLE_TRACES} traces in one "
            f"single-core configuration, found {len(rows)}"
        )

    first = rows[0]
    ipc_values = [float(row["ipc"]) for row in rows]
    real_values = [float(row["real_seconds"]) for row in rows]

    return {
        "predictor": first["predictor"],
        "replacement_policy": first["replacement_policy"],
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
            int(row["llc_writeback_accesses"]) for row in rows
        ),
        "total_llc_write_requests": sum(
            int(row["llc_total_write_requests"]) for row in rows
        ),
        "average_real_seconds": mean(real_values),
        "total_real_seconds": sum(real_values),
    }


def parse_new_four() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    manifests = read_csv(NEW_FOUR_MANIFEST)

    if len(manifests) != 20:
        fail(
            f"Expected 20 non-LRU four-core manifest rows, "
            f"found {len(manifests)}"
        )

    per_core_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for manifest in manifests:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])

        if not result_path.is_file():
            fail(f"Missing simulator output: {result_path}")

        text = result_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        ipc = parse_ipc(
            text, EXPECTED_FOUR_CORES, result_path
        )
        private, shared = parse_cache_totals(
            text, EXPECTED_FOUR_CORES, result_path
        )
        operations = parse_llc_operations(text)
        timing = parse_timing(timing_path)

        traces = [
            manifest["core0_trace"],
            manifest["core1_trace"],
            manifest["core2_trace"],
            manifest["core3_trace"],
        ]

        run_rows: list[dict[str, object]] = []

        for core in range(EXPECTED_FOUR_CORES):
            row = {
                "predictor": manifest["predictor"],
                "replacement_policy": (
                    manifest["replacement_policy"].lower()
                ),
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

            run_rows.append(row)
            per_core_rows.append(row)

        ipc_values = [
            float(row["ipc"])
            for row in run_rows
        ]

        summary_rows.append({
            "predictor": manifest["predictor"],
            "replacement_policy": (
                manifest["replacement_policy"].lower()
            ),
            "llc_size_mb": int(manifest["llc_size_mb"]),
            "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(
                manifest["llc_associativity"]
            ),
            "block_size_bytes": int(
                manifest["block_size_bytes"]
            ),
            "mix_number": int(manifest["mix_number"]),
            "core_count": EXPECTED_FOUR_CORES,
            "average_ipc": mean(ipc_values),
            "geomean_ipc": geometric_mean(ipc_values),
            "sum_ipc": sum(ipc_values),
            "weighted_l1i_miss_percent": weighted_percent(
                run_rows, "l1i_misses", "l1i_accesses"
            ),
            "weighted_l1d_miss_percent": weighted_percent(
                run_rows, "l1d_misses", "l1d_accesses"
            ),
            "weighted_l1_combined_miss_percent": weighted_percent(
                run_rows,
                "l1_combined_misses",
                "l1_combined_accesses",
            ),
            "weighted_l2_miss_percent": weighted_percent(
                run_rows, "l2_misses", "l2_accesses"
            ),
            **llc_metrics(shared["LLC"], operations),
            "run_real_seconds": timing["real"],
            "run_user_seconds": timing["user"],
            "run_sys_seconds": timing["sys"],
            "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        })

    return per_core_rows, summary_rows


def build_single_summary(
    detail_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[
        tuple[str, int],
        list[dict[str, object]],
    ] = defaultdict(list)

    for row in detail_rows:
        key = (
            str(row["replacement_policy"]),
            int(row["llc_size_mb"]),
        )
        grouped[key].append(row)

    summaries = []

    for policy in POLICY_ORDER:
        for size in SIZE_ORDER:
            key = (policy, size)

            if key not in grouped:
                fail(f"Missing single-core group: {policy}, {size} MB")

            summaries.append(summarize_single(grouped[key]))

    return summaries


def validate_combination_counts(
    single_detail: list[dict[str, object]],
    single_summary: list[dict[str, object]],
    four_per_core: list[dict[str, object]],
    four_summary: list[dict[str, object]],
) -> None:
    expected_single_detail = (
        len(POLICY_ORDER)
        * len(SIZE_ORDER)
        * EXPECTED_SINGLE_TRACES
    )
    expected_single_summary = (
        len(POLICY_ORDER) * len(SIZE_ORDER)
    )
    expected_four_per_core = (
        len(POLICY_ORDER)
        * len(SIZE_ORDER)
        * EXPECTED_FOUR_CORES
    )
    expected_four_summary = (
        len(POLICY_ORDER) * len(SIZE_ORDER)
    )

    counts = {
        "single detail": (
            len(single_detail),
            expected_single_detail,
        ),
        "single summary": (
            len(single_summary),
            expected_single_summary,
        ),
        "four-core per-core": (
            len(four_per_core),
            expected_four_per_core,
        ),
        "four-core summary": (
            len(four_summary),
            expected_four_summary,
        ),
    }

    for label, (actual, expected) in counts.items():
        if actual != expected:
            fail(
                f"Expected {expected} {label} rows, found {actual}"
            )

    for policy in POLICY_ORDER:
        for size in SIZE_ORDER:
            single_matches = [
                row
                for row in single_detail
                if str(row["replacement_policy"]) == policy
                and int(row["llc_size_mb"]) == size
            ]
            four_matches = [
                row
                for row in four_per_core
                if str(row["replacement_policy"]) == policy
                and int(row["llc_size_mb"]) == size
            ]

            if len(single_matches) != EXPECTED_SINGLE_TRACES:
                fail(
                    f"{policy} {size} MB has "
                    f"{len(single_matches)} single rows"
                )

            if len(four_matches) != EXPECTED_FOUR_CORES:
                fail(
                    f"{policy} {size} MB has "
                    f"{len(four_matches)} four-core rows"
                )


def build_single_ranking(
    summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []

    for size in SIZE_ORDER:
        candidates = [
            row
            for row in summaries
            if int(row["llc_size_mb"]) == size
        ]

        candidates.sort(
            key=lambda row: float(row["geomean_ipc"]),
            reverse=True,
        )

        for rank, row in enumerate(candidates, start=1):
            rows.append({
                "llc_size_mb": size,
                "ipc_rank": rank,
                "replacement_policy": row["replacement_policy"],
                "geomean_ipc": row["geomean_ipc"],
                "average_ipc": row["average_ipc"],
                "weighted_llc_miss_percent": (
                    row["weighted_llc_miss_percent"]
                ),
                "weighted_llc_hit_rate_percent": (
                    row["weighted_llc_hit_rate_percent"]
                ),
                "total_llc_write_requests": (
                    row["total_llc_write_requests"]
                ),
                "average_real_seconds": (
                    row["average_real_seconds"]
                ),
            })

    return rows


def build_four_ranking(
    summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []

    for size in SIZE_ORDER:
        candidates = [
            row
            for row in summaries
            if int(row["llc_size_mb"]) == size
        ]

        candidates.sort(
            key=lambda row: float(row["sum_ipc"]),
            reverse=True,
        )

        for rank, row in enumerate(candidates, start=1):
            rows.append({
                "llc_size_mb": size,
                "ipc_rank": rank,
                "replacement_policy": row["replacement_policy"],
                "sum_ipc": row["sum_ipc"],
                "geomean_ipc": row["geomean_ipc"],
                "llc_miss_percent": row["llc_miss_percent"],
                "llc_hit_rate_percent": (
                    row["llc_hit_rate_percent"]
                ),
                "llc_total_write_requests": (
                    row["llc_total_write_requests"]
                ),
                "run_real_seconds": row["run_real_seconds"],
            })

    return rows


def policy_sort_key(policy: object) -> int:
    try:
        return POLICY_ORDER.index(str(policy))
    except ValueError:
        return len(POLICY_ORDER)


def main() -> int:
    lru_single_detail = normalize_lru_single_detail()
    new_single_detail = parse_new_single_detail()
    single_detail = lru_single_detail + new_single_detail

    # Recalculate all summaries from the complete detailed table so every
    # policy uses the same aggregation method.
    single_summary = build_single_summary(single_detail)

    lru_four_per_core = normalize_lru_four_per_core()
    lru_four_summary = normalize_lru_four_summary()
    new_four_per_core, new_four_summary = parse_new_four()

    four_per_core = lru_four_per_core + new_four_per_core
    four_summary = lru_four_summary + new_four_summary

    validate_combination_counts(
        single_detail,
        single_summary,
        four_per_core,
        four_summary,
    )

    single_detail.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            policy_sort_key(row["replacement_policy"]),
            str(row["trace"]),
        )
    )
    single_summary.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            policy_sort_key(row["replacement_policy"]),
        )
    )
    four_per_core.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            policy_sort_key(row["replacement_policy"]),
            int(row["core"]),
        )
    )
    four_summary.sort(
        key=lambda row: (
            int(row["llc_size_mb"]),
            policy_sort_key(row["replacement_policy"]),
        )
    )

    single_ranking = build_single_ranking(single_summary)
    four_ranking = build_four_ranking(four_summary)

    write_csv(
        OUT_SINGLE_DETAIL,
        single_detail,
        SINGLE_DETAIL_FIELDS,
    )
    write_csv(
        OUT_SINGLE_SUMMARY,
        single_summary,
        SINGLE_SUMMARY_FIELDS,
    )
    write_csv(
        OUT_FOUR_PER_CORE,
        four_per_core,
        FOUR_PER_CORE_FIELDS,
    )
    write_csv(
        OUT_FOUR_SUMMARY,
        four_summary,
        FOUR_SUMMARY_FIELDS,
    )
    write_csv(
        OUT_SINGLE_RANKING,
        single_ranking,
        SINGLE_RANKING_FIELDS,
    )
    write_csv(
        OUT_FOUR_RANKING,
        four_ranking,
        FOUR_RANKING_FIELDS,
    )

    print(
        "Task 2 replacement-policy × LLC-size results "
        "parsed and merged successfully."
    )
    print(f"Policies:                  {len(POLICY_ORDER)}")
    print(f"LLC sizes:                 {len(SIZE_ORDER)}")
    print(f"Single-core detail rows:   {len(single_detail)}")
    print(f"Single-core summary rows:  {len(single_summary)}")
    print(f"Four-core per-core rows:   {len(four_per_core)}")
    print(f"Four-core summary rows:    {len(four_summary)}")
    print(f"Single-core ranking rows:  {len(single_ranking)}")
    print(f"Four-core ranking rows:    {len(four_ranking)}")
    print()
    print("Top single-core policy by LLC size:")
    for size in SIZE_ORDER:
        winner = next(
            row
            for row in single_ranking
            if int(row["llc_size_mb"]) == size
            and int(row["ipc_rank"]) == 1
        )
        print(
            f"  {size} MB: "
            f"{winner['replacement_policy']} "
            f"(geomean IPC {float(winner['geomean_ipc']):.6f})"
        )

    print()
    print("Top four-core policy by LLC size:")
    for size in SIZE_ORDER:
        winner = next(
            row
            for row in four_ranking
            if int(row["llc_size_mb"]) == size
            and int(row["ipc_rank"]) == 1
        )
        print(
            f"  {size} MB: "
            f"{winner['replacement_policy']} "
            f"(sum IPC {float(winner['sum_ipc']):.6f})"
        )

    print()
    print("Generated files:")
    for path in (
        OUT_SINGLE_DETAIL,
        OUT_SINGLE_SUMMARY,
        OUT_FOUR_PER_CORE,
        OUT_FOUR_SUMMARY,
        OUT_SINGLE_RANKING,
        OUT_FOUR_RANKING,
    ):
        print(f"  {path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
