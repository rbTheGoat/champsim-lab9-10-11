#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

BASE_SINGLE_DETAIL = Path("results/csv/task2_replacement_policy_size_single_results_all_policies.csv")
BASE_SINGLE_SUMMARY = Path("results/csv/task2_replacement_policy_size_single_summary_all_policies.csv")
BASE_FOUR_PER_CORE = Path("results/csv/task2_replacement_policy_size_four_core_per_core_all_policies.csv")
BASE_FOUR_SUMMARY = Path("results/csv/task2_replacement_policy_size_four_core_summary_all_policies.csv")

HCIT_SINGLE_MANIFEST = Path("results/raw/task2/hcit_size/single/run_manifest.csv")
HCIT_FOUR_MANIFEST = Path("results/raw/task2/hcit_size/four_core/run_manifest.csv")

OUT_SINGLE_DETAIL = Path("results/csv/task2_replacement_policy_size_single_results_with_hcit.csv")
OUT_SINGLE_SUMMARY = Path("results/csv/task2_replacement_policy_size_single_summary_with_hcit.csv")
OUT_FOUR_PER_CORE = Path("results/csv/task2_replacement_policy_size_four_core_per_core_with_hcit.csv")
OUT_FOUR_SUMMARY = Path("results/csv/task2_replacement_policy_size_four_core_summary_with_hcit.csv")
OUT_SINGLE_RANKING = Path("results/csv/task2_replacement_policy_size_single_ranking_with_hcit.csv")
OUT_FOUR_RANKING = Path("results/csv/task2_replacement_policy_size_four_core_ranking_with_hcit.csv")
OUT_HCIT_SINGLE_INTERNAL = Path("results/csv/task2_hcit_internal_single.csv")
OUT_HCIT_FOUR_INTERNAL = Path("results/csv/task2_hcit_internal_four_core.csv")

POLICIES = ["lru", "srrip", "drrip", "ship", "mru", "random", "hcit"]
SIZES = [1, 2, 4, 8]

NUMBER = r"[0-9][0-9,]*"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

IPC_RE = re.compile(rf"CPU\s+(\d+)\s+cumulative IPC:\s*({FLOAT})", re.I)
CACHE_TOTAL_RE = re.compile(
    rf"^\s*(?:CPU\s+(\d+)\s+)?(L1I|L1D|L2C|LLC)\s+TOTAL\s+"
    rf"ACCESS:\s*({NUMBER})\s+HIT:\s*({NUMBER})\s+MISS:\s*({NUMBER})",
    re.I | re.M,
)
CACHE_OPERATION_RE = re.compile(
    rf"^\s*(?:CPU\s+(\d+)\s+)?(L1I|L1D|L2C|LLC)\s+"
    rf"(LOAD|RFO|PREFETCH|WRITEBACK)\s+ACCESS:\s*({NUMBER})\s+"
    rf"HIT:\s*({NUMBER})\s+MISS:\s*({NUMBER})",
    re.I | re.M,
)

HCIT_PATTERNS = {
    "total_llc_updates": re.compile(r"^HCIT total LLC updates:\s*(\d+)", re.M),
    "final_threshold": re.compile(r"^HCIT final admission threshold:\s*(\d+)", re.M),
    "threshold_increases": re.compile(r"^HCIT threshold increases:\s*(\d+)", re.M),
    "threshold_decreases": re.compile(r"^HCIT threshold decreases:\s*(\d+)", re.M),
    "final_occupancy": re.compile(r"^HCIT final occupancy:\s*(\d+)\s*/\s*(\d+)", re.M),
    "admissions": re.compile(r"^HCIT admissions:\s*(\d+)", re.M),
    "rejected_admissions": re.compile(r"^HCIT rejected admissions:\s*(\d+)", re.M),
    "entry_replacements": re.compile(r"^HCIT entry replacements:\s*(\d+)", re.M),
    "stale_entry_removals": re.compile(r"^HCIT stale entry removals:\s*(\d+)", re.M),
    "protected_fills": re.compile(r"^HCIT protected fills:\s*(\d+)", re.M),
    "normal_fills": re.compile(r"^HCIT normal fills:\s*(\d+)", re.M),
    "protected_hits": re.compile(r"^HCIT protected hits:\s*(\d+)", re.M),
    "protected_evictions": re.compile(r"^HCIT protected evictions:\s*(\d+)", re.M),
    "protected_utility_percent": re.compile(rf"^HCIT protected utility percent:\s*({FLOAT})", re.M),
    "unprotected_victims": re.compile(r"^HCIT unprotected victim selections:\s*(\d+)", re.M),
    "forced_protected_victims": re.compile(r"^HCIT forced protected victim selections:\s*(\d+)", re.M),
}

SINGLE_DETAIL_FIELDS = [
    "predictor","replacement_policy","llc_size_mb","llc_sets","llc_associativity",
    "block_size_bytes","trace","ipc","l1i_accesses","l1i_hits","l1i_misses",
    "l1i_miss_percent","l1d_accesses","l1d_hits","l1d_misses","l1d_miss_percent",
    "l1_combined_accesses","l1_combined_hits","l1_combined_misses",
    "l1_combined_miss_percent","l2_accesses","l2_hits","l2_misses","l2_miss_percent",
    "llc_accesses","llc_hits","llc_misses","llc_miss_percent","llc_hit_rate_percent",
    "llc_rfo_accesses","llc_writeback_accesses","llc_total_write_requests",
    "real_seconds","user_seconds","sys_seconds","result_file","timing_file",
]

SINGLE_SUMMARY_FIELDS = [
    "predictor","replacement_policy","llc_size_mb","llc_sets","llc_associativity",
    "block_size_bytes","trace_count","average_ipc","geomean_ipc",
    "weighted_l1i_miss_percent","weighted_l1d_miss_percent",
    "weighted_l1_combined_miss_percent","weighted_l2_miss_percent",
    "weighted_llc_miss_percent","weighted_llc_hit_rate_percent",
    "total_llc_rfo_accesses","total_llc_writeback_accesses",
    "total_llc_write_requests","average_real_seconds","total_real_seconds",
]

FOUR_PER_CORE_FIELDS = [
    "predictor","replacement_policy","llc_size_mb","llc_sets","llc_associativity",
    "block_size_bytes","mix_number","core","trace","ipc","l1i_accesses","l1i_hits",
    "l1i_misses","l1i_miss_percent","l1d_accesses","l1d_hits","l1d_misses",
    "l1d_miss_percent","l1_combined_accesses","l1_combined_hits",
    "l1_combined_misses","l1_combined_miss_percent","l2_accesses","l2_hits",
    "l2_misses","l2_miss_percent","result_file",
]

FOUR_SUMMARY_FIELDS = [
    "predictor","replacement_policy","llc_size_mb","llc_sets","llc_associativity",
    "block_size_bytes","mix_number","core_count","average_ipc","geomean_ipc",
    "sum_ipc","weighted_l1i_miss_percent","weighted_l1d_miss_percent",
    "weighted_l1_combined_miss_percent","weighted_l2_miss_percent",
    "llc_accesses","llc_hits","llc_misses","llc_miss_percent",
    "llc_hit_rate_percent","llc_rfo_accesses","llc_writeback_accesses",
    "llc_total_write_requests","run_real_seconds","run_user_seconds",
    "run_sys_seconds","result_file","timing_file",
]

INTERNAL_FIELDS = [
    "llc_size_mb","scope","trace_or_mix","total_llc_updates","final_threshold",
    "threshold_increases","threshold_decreases","final_occupancy",
    "hcit_capacity","occupancy_percent","admissions","rejected_admissions",
    "entry_replacements","stale_entry_removals","protected_fills","normal_fills",
    "protected_hits","protected_evictions","protected_utility_percent",
    "unprotected_victims","forced_protected_victims","result_file",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        fail(f"No rows in {path}")
    return rows


def write_csv(path: Path, rows, fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def to_int(value: str) -> int:
    return int(value.replace(",", ""))


def percentage(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else 100.0 * numerator / denominator


def geometric_mean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        fail(f"Invalid values for geometric mean: {values}")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def parse_timing(path: Path) -> dict[str, float]:
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"real", "user", "sys"}:
            values[parts[0]] = float(parts[1])
    missing = {"real", "user", "sys"} - values.keys()
    if missing:
        fail(f"Missing timing values {missing} in {path}")
    return values


def parse_ipc(text: str, cores: int, path: Path) -> dict[int, float]:
    values = {}
    for core_text, ipc_text in IPC_RE.findall(text):
        core = int(core_text)
        if core < cores:
            values[core] = float(ipc_text)
    missing = set(range(cores)) - values.keys()
    if missing:
        fail(f"Missing IPC for cores {sorted(missing)} in {path}")
    return values


def parse_cache_totals(text: str, cores: int, path: Path):
    private = defaultdict(dict)
    unprefixed = defaultdict(list)
    llc_candidates = []

    for cpu_text, cache_text, accesses, hits, misses in CACHE_TOTAL_RE.findall(text):
        cache = cache_text.upper()
        stats = {"accesses": to_int(accesses), "hits": to_int(hits), "misses": to_int(misses)}
        if cache == "LLC":
            llc_candidates.append(stats)
        elif cpu_text:
            cpu = int(cpu_text)
            if cpu < cores:
                private[cpu][cache] = stats
        else:
            unprefixed[cache].append(stats)

    for cache in ("L1I", "L1D", "L2C"):
        if any(cache not in private[cpu] for cpu in range(cores)):
            candidates = unprefixed.get(cache, [])
            if len(candidates) < cores:
                fail(f"Not enough {cache} TOTAL lines in {path}")
            roi = candidates[-cores:]
            for cpu in range(cores):
                private[cpu][cache] = roi[cpu]

    if not llc_candidates:
        fail(f"Missing LLC TOTAL in {path}")

    return private, llc_candidates[-1]


def parse_operations(text: str):
    operations = {}
    for _, cache, op, accesses, hits, misses in CACHE_OPERATION_RE.findall(text):
        if cache.upper() == "LLC":
            operations[op.upper()] = {
                "accesses": to_int(accesses),
                "hits": to_int(hits),
                "misses": to_int(misses),
            }
    return operations


def private_metrics(caches):
    l1i, l1d, l2 = caches["L1I"], caches["L1D"], caches["L2C"]
    l1_accesses = l1i["accesses"] + l1d["accesses"]
    l1_hits = l1i["hits"] + l1d["hits"]
    l1_misses = l1i["misses"] + l1d["misses"]
    return {
        "l1i_accesses": l1i["accesses"], "l1i_hits": l1i["hits"], "l1i_misses": l1i["misses"],
        "l1i_miss_percent": percentage(l1i["misses"], l1i["accesses"]),
        "l1d_accesses": l1d["accesses"], "l1d_hits": l1d["hits"], "l1d_misses": l1d["misses"],
        "l1d_miss_percent": percentage(l1d["misses"], l1d["accesses"]),
        "l1_combined_accesses": l1_accesses, "l1_combined_hits": l1_hits,
        "l1_combined_misses": l1_misses,
        "l1_combined_miss_percent": percentage(l1_misses, l1_accesses),
        "l2_accesses": l2["accesses"], "l2_hits": l2["hits"], "l2_misses": l2["misses"],
        "l2_miss_percent": percentage(l2["misses"], l2["accesses"]),
    }


def llc_metrics(llc, operations):
    rfo = operations.get("RFO", {}).get("accesses", 0)
    wb = operations.get("WRITEBACK", {}).get("accesses", 0)
    return {
        "llc_accesses": llc["accesses"], "llc_hits": llc["hits"], "llc_misses": llc["misses"],
        "llc_miss_percent": percentage(llc["misses"], llc["accesses"]),
        "llc_hit_rate_percent": percentage(llc["hits"], llc["accesses"]),
        "llc_rfo_accesses": rfo, "llc_writeback_accesses": wb,
        "llc_total_write_requests": rfo + wb,
    }


def parse_hcit_internal(text: str, size: int, scope: str, label: str, result_file: str):
    values = {}
    for key, pattern in HCIT_PATTERNS.items():
        matches = list(pattern.finditer(text))
        if not matches:
            fail(f"Missing HCIT statistic '{key}' in {result_file}")
        match = matches[-1]
        if key == "final_occupancy":
            values["final_occupancy"] = int(match.group(1))
            values["hcit_capacity"] = int(match.group(2))
        elif key == "protected_utility_percent":
            values[key] = float(match.group(1))
        else:
            values[key] = int(match.group(1))

    values.update({
        "llc_size_mb": size,
        "scope": scope,
        "trace_or_mix": label,
        "occupancy_percent": percentage(values["final_occupancy"], values["hcit_capacity"]),
        "result_file": result_file,
    })
    return values


def weighted(rows, miss_field, access_field):
    return percentage(
        sum(int(row[miss_field]) for row in rows),
        sum(int(row[access_field]) for row in rows),
    )


def summarize_single(rows):
    first = rows[0]
    ipc_values = [float(row["ipc"]) for row in rows]
    real_values = [float(row["real_seconds"]) for row in rows]
    return {
        "predictor": first["predictor"], "replacement_policy": "hcit",
        "llc_size_mb": first["llc_size_mb"], "llc_sets": first["llc_sets"],
        "llc_associativity": first["llc_associativity"],
        "block_size_bytes": first["block_size_bytes"], "trace_count": len(rows),
        "average_ipc": mean(ipc_values), "geomean_ipc": geometric_mean(ipc_values),
        "weighted_l1i_miss_percent": weighted(rows, "l1i_misses", "l1i_accesses"),
        "weighted_l1d_miss_percent": weighted(rows, "l1d_misses", "l1d_accesses"),
        "weighted_l1_combined_miss_percent": weighted(rows, "l1_combined_misses", "l1_combined_accesses"),
        "weighted_l2_miss_percent": weighted(rows, "l2_misses", "l2_accesses"),
        "weighted_llc_miss_percent": weighted(rows, "llc_misses", "llc_accesses"),
        "weighted_llc_hit_rate_percent": percentage(
            sum(int(row["llc_hits"]) for row in rows),
            sum(int(row["llc_accesses"]) for row in rows),
        ),
        "total_llc_rfo_accesses": sum(int(row["llc_rfo_accesses"]) for row in rows),
        "total_llc_writeback_accesses": sum(int(row["llc_writeback_accesses"]) for row in rows),
        "total_llc_write_requests": sum(int(row["llc_total_write_requests"]) for row in rows),
        "average_real_seconds": mean(real_values), "total_real_seconds": sum(real_values),
    }


def parse_single():
    manifests = read_csv(HCIT_SINGLE_MANIFEST)
    if len(manifests) != 16:
        fail(f"Expected 16 HCIT single manifest rows, found {len(manifests)}")
    rows, internal = [], []

    for manifest in manifests:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])
        text = result_path.read_text(encoding="utf-8", errors="replace")
        if "ChampSim completed all CPUs" not in text:
            fail(f"Incomplete result: {result_path}")

        ipc = parse_ipc(text, 1, result_path)
        private, llc = parse_cache_totals(text, 1, result_path)
        timing = parse_timing(timing_path)
        size = int(manifest["llc_size_mb"])

        rows.append({
            "predictor": manifest["predictor"], "replacement_policy": "hcit",
            "llc_size_mb": size, "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(manifest["llc_associativity"]),
            "block_size_bytes": int(manifest["block_size_bytes"]),
            "trace": manifest["trace"], "ipc": ipc[0],
            **private_metrics(private[0]), **llc_metrics(llc, parse_operations(text)),
            "real_seconds": timing["real"], "user_seconds": timing["user"],
            "sys_seconds": timing["sys"], "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        })
        internal.append(parse_hcit_internal(
            text, size, "single-core", manifest["trace"], manifest["result_file"]
        ))

    summaries = []
    for size in SIZES:
        group = [row for row in rows if int(row["llc_size_mb"]) == size]
        if len(group) != 4:
            fail(f"Expected four HCIT single rows at {size} MB")
        summaries.append(summarize_single(group))
    return rows, summaries, internal


def parse_four():
    manifests = read_csv(HCIT_FOUR_MANIFEST)
    if len(manifests) != 4:
        fail(f"Expected four HCIT four-core manifest rows, found {len(manifests)}")

    per_core, summaries, internal = [], [], []

    for manifest in manifests:
        result_path = Path(manifest["result_file"])
        timing_path = Path(manifest["timing_file"])
        text = result_path.read_text(encoding="utf-8", errors="replace")
        if "ChampSim completed all CPUs" not in text:
            fail(f"Incomplete result: {result_path}")

        ipc = parse_ipc(text, 4, result_path)
        private, llc = parse_cache_totals(text, 4, result_path)
        timing = parse_timing(timing_path)
        size = int(manifest["llc_size_mb"])
        traces = [manifest[f"core{core}_trace"] for core in range(4)]
        run_rows = []

        for core in range(4):
            row = {
                "predictor": manifest["predictor"], "replacement_policy": "hcit",
                "llc_size_mb": size, "llc_sets": int(manifest["llc_sets"]),
                "llc_associativity": int(manifest["llc_associativity"]),
                "block_size_bytes": int(manifest["block_size_bytes"]),
                "mix_number": int(manifest["mix_number"]), "core": core,
                "trace": traces[core], "ipc": ipc[core],
                **private_metrics(private[core]), "result_file": manifest["result_file"],
            }
            run_rows.append(row)
            per_core.append(row)

        ipc_values = [float(row["ipc"]) for row in run_rows]
        summaries.append({
            "predictor": manifest["predictor"], "replacement_policy": "hcit",
            "llc_size_mb": size, "llc_sets": int(manifest["llc_sets"]),
            "llc_associativity": int(manifest["llc_associativity"]),
            "block_size_bytes": int(manifest["block_size_bytes"]),
            "mix_number": int(manifest["mix_number"]), "core_count": 4,
            "average_ipc": mean(ipc_values), "geomean_ipc": geometric_mean(ipc_values),
            "sum_ipc": sum(ipc_values),
            "weighted_l1i_miss_percent": weighted(run_rows, "l1i_misses", "l1i_accesses"),
            "weighted_l1d_miss_percent": weighted(run_rows, "l1d_misses", "l1d_accesses"),
            "weighted_l1_combined_miss_percent": weighted(
                run_rows, "l1_combined_misses", "l1_combined_accesses"
            ),
            "weighted_l2_miss_percent": weighted(run_rows, "l2_misses", "l2_accesses"),
            **llc_metrics(llc, parse_operations(text)),
            "run_real_seconds": timing["real"], "run_user_seconds": timing["user"],
            "run_sys_seconds": timing["sys"], "result_file": manifest["result_file"],
            "timing_file": manifest["timing_file"],
        })
        internal.append(parse_hcit_internal(
            text, size, "four-core", f"mix{manifest['mix_number']}", manifest["result_file"]
        ))

    return per_core, summaries, internal


def rankings(single_summary, four_summary):
    single_rank, four_rank = [], []
    for size in SIZES:
        candidates = [row for row in single_summary if int(row["llc_size_mb"]) == size]
        candidates.sort(key=lambda row: float(row["geomean_ipc"]), reverse=True)
        for rank, row in enumerate(candidates, 1):
            single_rank.append({
                "llc_size_mb": size, "ipc_rank": rank,
                "replacement_policy": row["replacement_policy"],
                "geomean_ipc": row["geomean_ipc"], "average_ipc": row["average_ipc"],
                "weighted_llc_miss_percent": row["weighted_llc_miss_percent"],
                "weighted_llc_hit_rate_percent": row["weighted_llc_hit_rate_percent"],
                "total_llc_write_requests": row["total_llc_write_requests"],
                "average_real_seconds": row["average_real_seconds"],
            })

        candidates = [row for row in four_summary if int(row["llc_size_mb"]) == size]
        candidates.sort(key=lambda row: float(row["sum_ipc"]), reverse=True)
        for rank, row in enumerate(candidates, 1):
            four_rank.append({
                "llc_size_mb": size, "ipc_rank": rank,
                "replacement_policy": row["replacement_policy"],
                "sum_ipc": row["sum_ipc"], "geomean_ipc": row["geomean_ipc"],
                "llc_miss_percent": row["llc_miss_percent"],
                "llc_hit_rate_percent": row["llc_hit_rate_percent"],
                "llc_total_write_requests": row["llc_total_write_requests"],
                "run_real_seconds": row["run_real_seconds"],
            })
    return single_rank, four_rank


def main() -> int:
    base_single_detail = read_csv(BASE_SINGLE_DETAIL)
    base_single_summary = read_csv(BASE_SINGLE_SUMMARY)
    base_four_per_core = read_csv(BASE_FOUR_PER_CORE)
    base_four_summary = read_csv(BASE_FOUR_SUMMARY)

    hcit_single_detail, hcit_single_summary, internal_single = parse_single()
    hcit_four_per_core, hcit_four_summary, internal_four = parse_four()

    single_detail = base_single_detail + hcit_single_detail
    single_summary = base_single_summary + hcit_single_summary
    four_per_core = base_four_per_core + hcit_four_per_core
    four_summary = base_four_summary + hcit_four_summary

    policy_index = {policy: index for index, policy in enumerate(POLICIES)}
    single_detail.sort(key=lambda row: (
        int(row["llc_size_mb"]), policy_index[row["replacement_policy"].lower()], row["trace"]
    ))
    single_summary.sort(key=lambda row: (
        int(row["llc_size_mb"]), policy_index[row["replacement_policy"].lower()]
    ))
    four_per_core.sort(key=lambda row: (
        int(row["llc_size_mb"]), policy_index[row["replacement_policy"].lower()], int(row["core"])
    ))
    four_summary.sort(key=lambda row: (
        int(row["llc_size_mb"]), policy_index[row["replacement_policy"].lower()]
    ))

    if len(single_detail) != 112 or len(single_summary) != 28:
        fail("Unexpected merged single-core row count")
    if len(four_per_core) != 112 or len(four_summary) != 28:
        fail("Unexpected merged four-core row count")

    single_rank, four_rank = rankings(single_summary, four_summary)

    write_csv(OUT_SINGLE_DETAIL, single_detail, SINGLE_DETAIL_FIELDS)
    write_csv(OUT_SINGLE_SUMMARY, single_summary, SINGLE_SUMMARY_FIELDS)
    write_csv(OUT_FOUR_PER_CORE, four_per_core, FOUR_PER_CORE_FIELDS)
    write_csv(OUT_FOUR_SUMMARY, four_summary, FOUR_SUMMARY_FIELDS)
    write_csv(OUT_SINGLE_RANKING, single_rank, [
        "llc_size_mb","ipc_rank","replacement_policy","geomean_ipc","average_ipc",
        "weighted_llc_miss_percent","weighted_llc_hit_rate_percent",
        "total_llc_write_requests","average_real_seconds",
    ])
    write_csv(OUT_FOUR_RANKING, four_rank, [
        "llc_size_mb","ipc_rank","replacement_policy","sum_ipc","geomean_ipc",
        "llc_miss_percent","llc_hit_rate_percent","llc_total_write_requests",
        "run_real_seconds",
    ])
    write_csv(OUT_HCIT_SINGLE_INTERNAL, internal_single, INTERNAL_FIELDS)
    write_csv(OUT_HCIT_FOUR_INTERNAL, internal_four, INTERNAL_FIELDS)

    print("HCIT parsed and merged as the seventh replacement policy.")
    print(f"Single detail rows:    {len(single_detail)}")
    print(f"Single summary rows:   {len(single_summary)}")
    print(f"Four per-core rows:    {len(four_per_core)}")
    print(f"Four summary rows:     {len(four_summary)}")
    print(f"HCIT internal single:  {len(internal_single)}")
    print(f"HCIT internal four:    {len(internal_four)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
