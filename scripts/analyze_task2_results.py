#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

CSV_DIR = Path("results/csv")
REPORTS_DIR = Path("reports")

LLC_SINGLE = CSV_DIR / "task2_llc_size_single_summary.csv"
LLC_FOUR = CSV_DIR / "task2_llc_size_four_core_summary.csv"

ASSOC_SINGLE = CSV_DIR / "task2_llc_associativity_single_summary.csv"
ASSOC_FOUR = CSV_DIR / "task2_llc_associativity_four_core_summary.csv"
ASSOC_SINGLE_CHANGE = CSV_DIR / "task2_llc_associativity_single_comparison.csv"
ASSOC_FOUR_CHANGE = CSV_DIR / "task2_llc_associativity_four_core_comparison.csv"

REPL_SINGLE = CSV_DIR / "task2_replacement_policy_size_single_summary_all_policies.csv"
REPL_FOUR = CSV_DIR / "task2_replacement_policy_size_four_core_summary_all_policies.csv"
REPL_SINGLE_RANK = CSV_DIR / "task2_replacement_policy_size_single_ranking.csv"
REPL_FOUR_RANK = CSV_DIR / "task2_replacement_policy_size_four_core_ranking.csv"

OUT_REPORT = REPORTS_DIR / "task2_results_analysis.md"
OUT_FINDINGS = CSV_DIR / "task2_key_findings.csv"

SIZE_ORDER = [1, 2, 4, 8]
POLICY_ORDER = ["lru", "srrip", "drrip", "ship", "mru", "random"]
POLICY_LABELS = {
    "lru": "LRU",
    "srrip": "SRRIP",
    "drrip": "DRRIP",
    "ship": "SHIP",
    "mru": "MRU",
    "random": "Random",
}

FINDING_FIELDS = [
    "section",
    "scope",
    "comparison",
    "metric",
    "baseline_value",
    "candidate_value",
    "absolute_change",
    "percent_change",
    "interpretation",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing required CSV: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        fail(f"No data rows found in {path}")

    return rows


def number(row: dict[str, str], field: str) -> float:
    try:
        return float(row[field])
    except KeyError:
        fail(f"Missing column '{field}'")
    except ValueError:
        fail(f"Invalid numeric value for '{field}': {row.get(field)!r}")


def pct_change(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return 100.0 * (new - old) / old


def fmt(value: float, digits: int = 4) -> str:
    if abs(value) >= 1_000_000:
        return f"{value:,.0f}"
    if abs(value) >= 1_000:
        return f"{value:,.2f}"
    return f"{value:.{digits}f}"


def fmt_pct(value: float, digits: int = 3) -> str:
    return f"{value:+.{digits}f}%"


def change_strength(value: float) -> str:
    magnitude = abs(value)
    if magnitude < 0.5:
        return "negligible"
    if magnitude < 2.0:
        return "small"
    if magnitude < 5.0:
        return "moderate"
    return "large"


def direction_word(value: float) -> str:
    if value > 0:
        return "increased"
    if value < 0:
        return "decreased"
    return "did not change"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def index_by_size(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    indexed = {int(row["llc_size_mb"]): row for row in rows}
    missing = [size for size in SIZE_ORDER if size not in indexed]
    if missing:
        fail(f"Missing LLC sizes: {missing}")
    return indexed


def index_policy_size(
    rows: list[dict[str, str]],
) -> dict[tuple[str, int], dict[str, str]]:
    indexed = {
        (row["replacement_policy"].lower(), int(row["llc_size_mb"])): row
        for row in rows
    }
    missing = [
        (policy, size)
        for policy in POLICY_ORDER
        for size in SIZE_ORDER
        if (policy, size) not in indexed
    ]
    if missing:
        fail(f"Missing policy/size rows: {missing}")
    return indexed


def add_finding(
    findings: list[dict[str, object]],
    section: str,
    scope: str,
    comparison: str,
    metric: str,
    old: float,
    new: float,
    interpretation: str,
) -> None:
    findings.append({
        "section": section,
        "scope": scope,
        "comparison": comparison,
        "metric": metric,
        "baseline_value": old,
        "candidate_value": new,
        "absolute_change": new - old,
        "percent_change": pct_change(new, old),
        "interpretation": interpretation,
    })


def analyze_llc_size(
    single_rows: list[dict[str, str]],
    four_rows: list[dict[str, str]],
    findings: list[dict[str, object]],
) -> list[str]:
    single = index_by_size(single_rows)
    four = index_by_size(four_rows)

    lines = [
        "## 1. LLC Size Study: 1 MB, 2 MB, 4 MB and 8 MB",
        "",
        "All configurations use a 16-way LLC, LRU replacement and the hashed-perceptron branch predictor.",
        "",
    ]

    single_table = []
    four_table = []

    for size in SIZE_ORDER:
        row = single[size]
        single_table.append([
            f"{size} MB",
            fmt(number(row, "geomean_ipc"), 6),
            fmt(number(row, "weighted_l1_combined_miss_percent")),
            fmt(number(row, "weighted_l2_miss_percent")),
            fmt(number(row, "weighted_llc_miss_percent")),
            fmt(number(row, "weighted_llc_hit_rate_percent")),
            fmt(number(row, "total_llc_write_requests"), 0),
            fmt(number(row, "average_real_seconds"), 3),
        ])

        row = four[size]
        four_table.append([
            f"{size} MB",
            fmt(number(row, "sum_ipc"), 6),
            fmt(number(row, "geomean_ipc"), 6),
            fmt(number(row, "weighted_l1_combined_miss_percent")),
            fmt(number(row, "weighted_l2_miss_percent")),
            fmt(number(row, "llc_miss_percent")),
            fmt(number(row, "llc_hit_rate_percent")),
            fmt(number(row, "llc_total_write_requests"), 0),
            fmt(number(row, "run_real_seconds"), 3),
        ])

    lines.extend([
        "### Single-core summary",
        "",
        markdown_table(
            [
                "LLC size",
                "Geomean IPC",
                "L1 miss %",
                "L2 miss %",
                "LLC miss %",
                "LLC hit %",
                "LLC writes",
                "Time (s)",
            ],
            single_table,
        ),
        "",
        "### Four-core summary",
        "",
        markdown_table(
            [
                "LLC size",
                "Sum IPC",
                "Geomean IPC",
                "L1 miss %",
                "L2 miss %",
                "LLC miss %",
                "LLC hit %",
                "LLC writes",
                "Time (s)",
            ],
            four_table,
        ),
        "",
    ])

    def best_size(indexed, field, maximize=True):
        return (
            max(SIZE_ORDER, key=lambda size: number(indexed[size], field))
            if maximize
            else min(SIZE_ORDER, key=lambda size: number(indexed[size], field))
        )

    single_best_ipc = best_size(single, "geomean_ipc", True)
    single_best_miss = best_size(single, "weighted_llc_miss_percent", False)
    four_best_ipc = best_size(four, "sum_ipc", True)
    four_best_miss = best_size(four, "llc_miss_percent", False)

    s1 = single[1]
    s8 = single[8]
    f1 = four[1]
    f8 = four[8]

    single_ipc_change = pct_change(
        number(s8, "geomean_ipc"),
        number(s1, "geomean_ipc"),
    )
    single_miss_change = pct_change(
        number(s8, "weighted_llc_miss_percent"),
        number(s1, "weighted_llc_miss_percent"),
    )
    four_ipc_change = pct_change(
        number(f8, "sum_ipc"),
        number(f1, "sum_ipc"),
    )
    four_miss_change = pct_change(
        number(f8, "llc_miss_percent"),
        number(f1, "llc_miss_percent"),
    )

    lines.extend([
        "### Main observations",
        "",
        (
            f"- The best single-core geometric-mean IPC occurs at **{single_best_ipc} MB**, "
            f"while the lowest weighted single-core LLC miss percentage occurs at **{single_best_miss} MB**."
        ),
        (
            f"- Moving from 1 MB to 8 MB changes single-core geometric-mean IPC by "
            f"**{fmt_pct(single_ipc_change)}** and LLC miss percentage by "
            f"**{fmt_pct(single_miss_change)}**."
        ),
        (
            f"- The best four-core aggregate IPC occurs at **{four_best_ipc} MB**, "
            f"while the lowest shared-LLC miss percentage occurs at **{four_best_miss} MB**."
        ),
        (
            f"- Moving from 1 MB to 8 MB changes four-core aggregate IPC by "
            f"**{fmt_pct(four_ipc_change)}** and shared-LLC miss percentage by "
            f"**{fmt_pct(four_miss_change)}**."
        ),
        (
            "- L1 and L2 miss percentages are included for completeness, but LLC capacity changes "
            "primarily affect the shared last-level cache. Any L1/L2 variation is indirect, caused by "
            "timing, replacement interactions and the set of requests reaching the LLC."
        ),
        "",
    ])

    add_finding(
        findings,
        "LLC size",
        "single-core",
        "1 MB to 8 MB",
        "geomean_ipc",
        number(s1, "geomean_ipc"),
        number(s8, "geomean_ipc"),
        f"{change_strength(single_ipc_change)} IPC change",
    )
    add_finding(
        findings,
        "LLC size",
        "single-core",
        "1 MB to 8 MB",
        "weighted_llc_miss_percent",
        number(s1, "weighted_llc_miss_percent"),
        number(s8, "weighted_llc_miss_percent"),
        f"{change_strength(single_miss_change)} LLC-miss change",
    )
    add_finding(
        findings,
        "LLC size",
        "four-core",
        "1 MB to 8 MB",
        "sum_ipc",
        number(f1, "sum_ipc"),
        number(f8, "sum_ipc"),
        f"{change_strength(four_ipc_change)} aggregate-IPC change",
    )
    add_finding(
        findings,
        "LLC size",
        "four-core",
        "1 MB to 8 MB",
        "llc_miss_percent",
        number(f1, "llc_miss_percent"),
        number(f8, "llc_miss_percent"),
        f"{change_strength(four_miss_change)} shared-LLC-miss change",
    )

    return lines


def analyze_associativity(
    single_summary: list[dict[str, str]],
    four_summary: list[dict[str, str]],
    single_change_rows: list[dict[str, str]],
    four_change_rows: list[dict[str, str]],
    findings: list[dict[str, object]],
) -> list[str]:
    single = {
        int(row["llc_associativity"]): row
        for row in single_summary
    }
    four = {
        int(row["llc_associativity"]): row
        for row in four_summary
    }

    for required in (16, 8):
        if required not in single or required not in four:
            fail(f"Missing {required}-way associativity summary")

    lines = [
        "## 2. LLC Associativity Study: 16-way vs 8-way",
        "",
        "The LLC capacity is held at 4 MB. Therefore, the 16-way configuration uses 4096 sets and the 8-way configuration uses 8192 sets, both with 64-byte blocks.",
        "",
    ]

    s16, s8 = single[16], single[8]
    f16, f8 = four[16], four[8]

    single_table = [
        [
            "16-way",
            fmt(number(s16, "geomean_ipc"), 6),
            fmt(number(s16, "weighted_llc_miss_percent")),
            fmt(number(s16, "weighted_llc_hit_rate_percent")),
            fmt(number(s16, "total_llc_write_requests"), 0),
            fmt(number(s16, "average_real_seconds"), 3),
        ],
        [
            "8-way",
            fmt(number(s8, "geomean_ipc"), 6),
            fmt(number(s8, "weighted_llc_miss_percent")),
            fmt(number(s8, "weighted_llc_hit_rate_percent")),
            fmt(number(s8, "total_llc_write_requests"), 0),
            fmt(number(s8, "average_real_seconds"), 3),
        ],
    ]

    four_table = [
        [
            "16-way",
            fmt(number(f16, "sum_ipc"), 6),
            fmt(number(f16, "llc_miss_percent")),
            fmt(number(f16, "llc_hit_rate_percent")),
            fmt(number(f16, "llc_total_write_requests"), 0),
            fmt(number(f16, "run_real_seconds"), 3),
        ],
        [
            "8-way",
            fmt(number(f8, "sum_ipc"), 6),
            fmt(number(f8, "llc_miss_percent")),
            fmt(number(f8, "llc_hit_rate_percent")),
            fmt(number(f8, "llc_total_write_requests"), 0),
            fmt(number(f8, "run_real_seconds"), 3),
        ],
    ]

    lines.extend([
        "### Single-core comparison",
        "",
        markdown_table(
            ["Associativity", "Geomean IPC", "LLC miss %", "LLC hit %", "LLC writes", "Time (s)"],
            single_table,
        ),
        "",
        "### Four-core comparison",
        "",
        markdown_table(
            ["Associativity", "Sum IPC", "LLC miss %", "LLC hit %", "LLC writes", "Time (s)"],
            four_table,
        ),
        "",
    ])

    single_changes = {
        row["metric"]: number(row, "percent_change_from_16way")
        for row in single_change_rows
    }
    four_changes = {
        row["metric"]: number(row, "percent_change_from_16way")
        for row in four_change_rows
    }

    s_ipc = single_changes["geomean_ipc"]
    s_miss = single_changes["weighted_llc_miss_percent"]
    f_ipc = four_changes["sum_ipc"]
    f_miss = four_changes["llc_miss_percent"]

    lines.extend([
        "### Main observations",
        "",
        (
            f"- Reducing associativity from 16-way to 8-way produces a "
            f"**{change_strength(s_ipc)}** single-core geometric-mean IPC change of "
            f"**{fmt_pct(s_ipc)}**."
        ),
        (
            f"- The weighted single-core LLC miss percentage {direction_word(s_miss)} by "
            f"**{fmt_pct(s_miss)}**."
        ),
        (
            f"- Four-core aggregate IPC changes by **{fmt_pct(f_ipc)}**, while shared-LLC "
            f"miss percentage changes by **{fmt_pct(f_miss)}**."
        ),
        (
            "- At fixed capacity, lower associativity reduces the number of candidate locations "
            "available to each address and can increase conflict misses. However, doubling the "
            "number of sets changes address mapping, so particular workloads may show little loss "
            "or even a small improvement. The measured workload results, rather than associativity "
            "alone, determine the final conclusion."
        ),
        "",
    ])

    add_finding(
        findings,
        "Associativity",
        "single-core",
        "16-way to 8-way at 4 MB",
        "geomean_ipc",
        number(s16, "geomean_ipc"),
        number(s8, "geomean_ipc"),
        f"{change_strength(s_ipc)} IPC effect",
    )
    add_finding(
        findings,
        "Associativity",
        "single-core",
        "16-way to 8-way at 4 MB",
        "weighted_llc_miss_percent",
        number(s16, "weighted_llc_miss_percent"),
        number(s8, "weighted_llc_miss_percent"),
        f"{change_strength(s_miss)} conflict/locality effect",
    )
    add_finding(
        findings,
        "Associativity",
        "four-core",
        "16-way to 8-way at 4 MB",
        "sum_ipc",
        number(f16, "sum_ipc"),
        number(f8, "sum_ipc"),
        f"{change_strength(f_ipc)} aggregate-IPC effect",
    )
    add_finding(
        findings,
        "Associativity",
        "four-core",
        "16-way to 8-way at 4 MB",
        "llc_miss_percent",
        number(f16, "llc_miss_percent"),
        number(f8, "llc_miss_percent"),
        f"{change_strength(f_miss)} shared-cache effect",
    )

    return lines


def analyze_replacement(
    single_rows: list[dict[str, str]],
    four_rows: list[dict[str, str]],
    single_rank: list[dict[str, str]],
    four_rank: list[dict[str, str]],
    findings: list[dict[str, object]],
) -> list[str]:
    single = index_policy_size(single_rows)
    four = index_policy_size(four_rows)

    lines = [
        "## 3. Replacement-Policy × LLC-Size Study",
        "",
        "The comparison includes LRU, SRRIP, DRRIP, SHIP, the implemented MRU policy and the implemented deterministic Random policy.",
        "",
    ]

    winners_table = []

    for size in SIZE_ORDER:
        single_candidates = [
            (policy, number(single[(policy, size)], "geomean_ipc"))
            for policy in POLICY_ORDER
        ]
        four_candidates = [
            (policy, number(four[(policy, size)], "sum_ipc"))
            for policy in POLICY_ORDER
        ]
        single_winner = max(single_candidates, key=lambda item: item[1])
        four_winner = max(four_candidates, key=lambda item: item[1])

        winners_table.append([
            f"{size} MB",
            POLICY_LABELS[single_winner[0]],
            fmt(single_winner[1], 6),
            POLICY_LABELS[four_winner[0]],
            fmt(four_winner[1], 6),
        ])

    lines.extend([
        "### IPC winners by LLC size",
        "",
        markdown_table(
            ["LLC size", "Single-core winner", "Geomean IPC", "Four-core winner", "Sum IPC"],
            winners_table,
        ),
        "",
    ])

    average_single_rank: dict[str, float] = {}
    average_four_rank: dict[str, float] = {}

    for policy in POLICY_ORDER:
        average_single_rank[policy] = mean(
            int(row["ipc_rank"])
            for row in single_rank
            if row["replacement_policy"].lower() == policy
        )
        average_four_rank[policy] = mean(
            int(row["ipc_rank"])
            for row in four_rank
            if row["replacement_policy"].lower() == policy
        )

    rank_table = [
        [
            POLICY_LABELS[policy],
            fmt(average_single_rank[policy], 2),
            fmt(average_four_rank[policy], 2),
            fmt(mean(
                number(single[(policy, size)], "geomean_ipc")
                for size in SIZE_ORDER
            ), 6),
            fmt(mean(
                number(four[(policy, size)], "sum_ipc")
                for size in SIZE_ORDER
            ), 6),
        ]
        for policy in sorted(
            POLICY_ORDER,
            key=lambda p: (
                average_single_rank[p] + average_four_rank[p],
                average_single_rank[p],
            ),
        )
    ]

    lines.extend([
        "### Cross-size policy consistency",
        "",
        markdown_table(
            [
                "Policy",
                "Avg single rank",
                "Avg four-core rank",
                "Mean single geomean IPC",
                "Mean four-core sum IPC",
            ],
            rank_table,
        ),
        "",
    ])

    best_single_consistency = min(
        POLICY_ORDER,
        key=lambda policy: average_single_rank[policy],
    )
    best_four_consistency = min(
        POLICY_ORDER,
        key=lambda policy: average_four_rank[policy],
    )

    lines.extend([
        "### Main observations",
        "",
        (
            f"- **{POLICY_LABELS[best_single_consistency]}** has the best average single-core "
            f"IPC rank across the four LLC sizes."
        ),
        (
            f"- **{POLICY_LABELS[best_four_consistency]}** has the best average four-core "
            f"aggregate-IPC rank across the four LLC sizes."
        ),
    ])

    for size in SIZE_ORDER:
        lru_s = single[("lru", size)]
        mru_s = single[("mru", size)]
        random_s = single[("random", size)]
        lru_f = four[("lru", size)]
        mru_f = four[("mru", size)]
        random_f = four[("random", size)]

        mru_s_change = pct_change(
            number(mru_s, "geomean_ipc"),
            number(lru_s, "geomean_ipc"),
        )
        random_s_change = pct_change(
            number(random_s, "geomean_ipc"),
            number(lru_s, "geomean_ipc"),
        )
        mru_f_change = pct_change(
            number(mru_f, "sum_ipc"),
            number(lru_f, "sum_ipc"),
        )
        random_f_change = pct_change(
            number(random_f, "sum_ipc"),
            number(lru_f, "sum_ipc"),
        )

        lines.append(
            f"- At {size} MB, MRU changes IPC relative to LRU by "
            f"**{fmt_pct(mru_s_change)}** in single-core and **{fmt_pct(mru_f_change)}** "
            f"in four-core; Random changes it by **{fmt_pct(random_s_change)}** and "
            f"**{fmt_pct(random_f_change)}**, respectively."
        )

        add_finding(
            findings,
            "Replacement policy",
            "single-core",
            f"MRU vs LRU at {size} MB",
            "geomean_ipc",
            number(lru_s, "geomean_ipc"),
            number(mru_s, "geomean_ipc"),
            "effect of evicting the most recently used block",
        )
        add_finding(
            findings,
            "Replacement policy",
            "single-core",
            f"Random vs LRU at {size} MB",
            "geomean_ipc",
            number(lru_s, "geomean_ipc"),
            number(random_s, "geomean_ipc"),
            "effect of replacement without locality state",
        )
        add_finding(
            findings,
            "Replacement policy",
            "four-core",
            f"MRU vs LRU at {size} MB",
            "sum_ipc",
            number(lru_f, "sum_ipc"),
            number(mru_f, "sum_ipc"),
            "shared-cache effect of MRU",
        )
        add_finding(
            findings,
            "Replacement policy",
            "four-core",
            f"Random vs LRU at {size} MB",
            "sum_ipc",
            number(lru_f, "sum_ipc"),
            number(random_f, "sum_ipc"),
            "shared-cache effect of Random replacement",
        )

    lines.extend([
        (
            "- LRU exploits temporal locality, SRRIP/DRRIP estimate re-reference distance, "
            "and SHIP uses PC-based reuse prediction. MRU intentionally discards the newest "
            "line, while Random maintains no locality state. Differences between policies are "
            "therefore expected to be workload- and capacity-dependent."
        ),
        (
            "- A policy should not be declared universally best from IPC alone. LLC miss rate, "
            "hit rate, writes and execution time must be checked for the same configuration, "
            "especially when policies have similar IPC."
        ),
        "",
    ])

    return lines


def write_findings(rows: list[dict[str, object]]) -> None:
    OUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FINDINGS.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FINDING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    llc_single = load_csv(LLC_SINGLE)
    llc_four = load_csv(LLC_FOUR)

    assoc_single = load_csv(ASSOC_SINGLE)
    assoc_four = load_csv(ASSOC_FOUR)
    assoc_single_change = load_csv(ASSOC_SINGLE_CHANGE)
    assoc_four_change = load_csv(ASSOC_FOUR_CHANGE)

    repl_single = load_csv(REPL_SINGLE)
    repl_four = load_csv(REPL_FOUR)
    repl_single_rank = load_csv(REPL_SINGLE_RANK)
    repl_four_rank = load_csv(REPL_FOUR_RANK)

    findings: list[dict[str, object]] = []

    report_lines = [
        "# Task 2 Results Analysis",
        "",
        "## Experimental basis",
        "",
        "- L1-I: 32 KB, 8-way, LRU",
        "- L1-D: 32 KB, 8-way, LRU",
        "- L2: 256 KB, 8-way, LRU",
        "- Default LLC: 4 MB, 16-way",
        "- Block size: 64 bytes",
        "- Branch predictor held constant: hashed perceptron",
        "- Four single-core traces per configuration",
        "- One seeded four-program mix for four-core experiments",
        "",
        (
            "**LLC-write definition used in the tables:** "
            "`LLC RFO accesses + LLC WRITEBACK accesses`. These fields are also "
            "retained separately in the detailed CSV files."
        ),
        "",
    ]

    report_lines.extend(analyze_llc_size(llc_single, llc_four, findings))
    report_lines.extend(
        analyze_associativity(
            assoc_single,
            assoc_four,
            assoc_single_change,
            assoc_four_change,
            findings,
        )
    )
    report_lines.extend(
        analyze_replacement(
            repl_single,
            repl_four,
            repl_single_rank,
            repl_four_rank,
            findings,
        )
    )

    report_lines.extend([
        "## 4. Report-ready overall conclusion",
        "",
        (
            "Increasing LLC capacity generally provides more opportunity to retain reusable blocks, "
            "but the measured IPC benefit depends on whether the selected workloads are capacity- or "
            "conflict-sensitive. The LLC miss and hit-rate trends should therefore be interpreted "
            "together with IPC rather than in isolation."
        ),
        "",
        (
            "Reducing associativity from 16-way to 8-way at fixed 4 MB capacity changes both the "
            "number of ways and the number of sets. The measured result captures the combined effect "
            "of reduced placement flexibility and changed address mapping."
        ),
        "",
        (
            "The replacement-policy study demonstrates that no policy is automatically optimal at "
            "every capacity and workload mix. Re-reference-prediction policies can outperform simple "
            "recency when they identify low-reuse lines, while LRU remains a strong baseline. MRU and "
            "Random provide useful contrast because they intentionally remove or ignore temporal-locality "
            "information."
        ),
        "",
        "## 5. Graph locations",
        "",
        "- LLC size: `results/graphs/task2/llc_size/`",
        "- Associativity: `results/graphs/task2/llc_associativity/`",
        "- Replacement policy × size: `results/graphs/task2/replacement_policy_size/`",
        "",
        "## 6. Methodology note",
        "",
        (
            "The assignment states that the 64-byte block size has an exception for Task 2(d), "
            "but it does not provide alternative block sizes. Therefore, the experiments retain "
            "the specified 64-byte block size and document this assumption rather than inventing "
            "an unsupported configuration."
        ),
        "",
    ])

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    write_findings(findings)

    print("Task 2 report-ready analysis generated successfully.")
    print(f"Markdown report: {OUT_REPORT}")
    print(f"Key-findings CSV: {OUT_FINDINGS}")
    print(f"Findings rows:    {len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
