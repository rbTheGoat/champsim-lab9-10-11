#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

SINGLE_SUMMARY = Path("results/csv/task2_replacement_policy_size_single_summary_with_hcit.csv")
FOUR_SUMMARY = Path("results/csv/task2_replacement_policy_size_four_core_summary_with_hcit.csv")
INTERNAL_SINGLE = Path("results/csv/task2_hcit_internal_single.csv")
INTERNAL_FOUR = Path("results/csv/task2_hcit_internal_four_core.csv")

OUT_REPORT = Path("reports/task2_hcit_results_analysis.md")
OUT_FINDINGS = Path("results/csv/task2_hcit_key_findings.csv")

SIZES = [1, 2, 4, 8]
BASE_POLICIES = ["lru", "srrip", "drrip", "ship", "mru", "random"]


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


def pct(new, old):
    return 0.0 if old == 0 else 100.0 * (new - old) / old


def fmt(value, digits=5):
    return f"{value:.{digits}f}"


def table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> int:
    single_rows = read_csv(SINGLE_SUMMARY)
    four_rows = read_csv(FOUR_SUMMARY)
    internal_single = read_csv(INTERNAL_SINGLE)
    internal_four = read_csv(INTERNAL_FOUR)

    single = {(r["replacement_policy"].lower(), int(r["llc_size_mb"])): r for r in single_rows}
    four = {(r["replacement_policy"].lower(), int(r["llc_size_mb"])): r for r in four_rows}

    report = [
        "# Adaptive HCIT Results Analysis",
        "",
        "HCIT is evaluated as the seventh replacement policy at 1 MB, 2 MB, 4 MB and 8 MB.",
        "",
        "## Performance comparison",
        "",
    ]
    findings = []
    performance_rows = []

    for size in SIZES:
        hcit_s = float(single[("hcit", size)]["geomean_ipc"])
        lru_s = float(single[("lru", size)]["geomean_ipc"])
        best_base_policy_s = max(
            BASE_POLICIES,
            key=lambda p: float(single[(p, size)]["geomean_ipc"]),
        )
        best_base_s = float(single[(best_base_policy_s, size)]["geomean_ipc"])

        hcit_f = float(four[("hcit", size)]["sum_ipc"])
        lru_f = float(four[("lru", size)]["sum_ipc"])
        best_base_policy_f = max(
            BASE_POLICIES,
            key=lambda p: float(four[(p, size)]["sum_ipc"]),
        )
        best_base_f = float(four[(best_base_policy_f, size)]["sum_ipc"])

        performance_rows.append([
            f"{size} MB",
            fmt(hcit_s),
            f"{pct(hcit_s, lru_s):+.3f}%",
            best_base_policy_s.upper(),
            f"{pct(hcit_s, best_base_s):+.3f}%",
            fmt(hcit_f),
            f"{pct(hcit_f, lru_f):+.3f}%",
            best_base_policy_f.upper(),
            f"{pct(hcit_f, best_base_f):+.3f}%",
        ])

        findings.extend([
            {
                "scope": "single-core",
                "llc_size_mb": size,
                "comparison": "HCIT vs LRU",
                "metric": "geomean_ipc",
                "baseline": lru_s,
                "hcit": hcit_s,
                "percent_change": pct(hcit_s, lru_s),
            },
            {
                "scope": "single-core",
                "llc_size_mb": size,
                "comparison": f"HCIT vs best baseline ({best_base_policy_s})",
                "metric": "geomean_ipc",
                "baseline": best_base_s,
                "hcit": hcit_s,
                "percent_change": pct(hcit_s, best_base_s),
            },
            {
                "scope": "four-core",
                "llc_size_mb": size,
                "comparison": "HCIT vs LRU",
                "metric": "sum_ipc",
                "baseline": lru_f,
                "hcit": hcit_f,
                "percent_change": pct(hcit_f, lru_f),
            },
            {
                "scope": "four-core",
                "llc_size_mb": size,
                "comparison": f"HCIT vs best baseline ({best_base_policy_f})",
                "metric": "sum_ipc",
                "baseline": best_base_f,
                "hcit": hcit_f,
                "percent_change": pct(hcit_f, best_base_f),
            },
        ])

    report.extend([
        table(
            [
                "Size","HCIT single IPC","vs LRU","Best baseline","vs best",
                "HCIT four sum IPC","vs LRU","Best baseline","vs best",
            ],
            performance_rows,
        ),
        "",
        "## HCIT internal behavior",
        "",
    ])

    internal_rows = []
    for size in SIZES:
        s_group = [r for r in internal_single if int(r["llc_size_mb"]) == size]
        f_row = next(r for r in internal_four if int(r["llc_size_mb"]) == size)
        internal_rows.append([
            f"{size} MB",
            f"{mean(float(r['final_threshold']) for r in s_group):.2f}",
            f"{mean(float(r['occupancy_percent']) for r in s_group):.2f}%",
            f"{mean(float(r['protected_utility_percent']) for r in s_group):.2f}%",
            f"{float(f_row['final_threshold']):.0f}",
            f"{float(f_row['occupancy_percent']):.2f}%",
            f"{float(f_row['protected_utility_percent']):.2f}%",
        ])

    report.extend([
        table(
            [
                "Size","Single threshold","Single occupancy","Single utility",
                "Four threshold","Four occupancy","Four utility",
            ],
            internal_rows,
        ),
        "",
        "## Conclusions",
        "",
        "- HCIT allocates detailed tracking only after the candidate filter identifies repeated miss pressure.",
        "- The final threshold and occupancy values show whether the adaptive controller became more or less selective at each capacity.",
        "- Protected utility is the fraction of protected-block outcomes that were hits rather than evictions.",
        "- HCIT should be judged against both LRU and the strongest conventional policy at each size; a single workload mix cannot establish universal superiority.",
        "- Even when IPC is similar, HCIT remains a valid bonus design because it implements selective hard-candidate tracking, adaptive admission/removal, preferential insertion and delayed eviction.",
        "",
        "## Graph locations",
        "",
        "- `results/graphs/task2/hcit_comparison/single/`",
        "- `results/graphs/task2/hcit_comparison/four_core/`",
        "",
    ])

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(report), encoding="utf-8")

    OUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FINDINGS.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["scope","llc_size_mb","comparison","metric","baseline","hcit","percent_change"],
        )
        writer.writeheader()
        writer.writerows(findings)

    print("HCIT analysis generated.")
    print(f"Report:   {OUT_REPORT}")
    print(f"Findings: {OUT_FINDINGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
