#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

ROOT = Path(".")
REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"

OUT_REPORT = REPORTS / "final_assignment_report.md"
OUT_INVENTORY = REPORTS / "final_graph_inventory.txt"

TASK1_SINGLE = RESULTS / "csv/task1_single_summary_all_predictors.csv"
TASK1_FOUR = RESULTS / "csv/task1_four_core_summary_all_predictors.csv"

DESIGN_FILES = [
    REPORTS / "modified_bullseye_design.md",
    REPORTS / "adaptive_bullseye_design.md",
    REPORTS / "mru_random_design.md",
    REPORTS / "adaptive_hcit_design.md",
]

TASK2_ANALYSES = [
    REPORTS / "task2_results_analysis.md",
    REPORTS / "task2_hcit_results_analysis.md",
]

PREFERRED_TASK1_COLUMNS = [
    "predictor",
    "average_mpki",
    "avg_mpki",
    "mpki",
    "average_accuracy_percent",
    "avg_accuracy_percent",
    "accuracy_percent",
    "accuracy",
    "average_prediction_latency_ns",
    "avg_prediction_latency_ns",
    "prediction_latency_ns",
    "latency_ns",
    "average_real_seconds",
    "avg_real_seconds",
    "execution_time_seconds",
    "total_real_seconds",
    "average_ipc",
    "avg_ipc",
    "geomean_ipc",
]

COLUMN_LABELS = {
    "predictor": "Predictor",
    "average_mpki": "Average MPKI",
    "avg_mpki": "Average MPKI",
    "mpki": "MPKI",
    "average_accuracy_percent": "Accuracy (%)",
    "avg_accuracy_percent": "Accuracy (%)",
    "accuracy_percent": "Accuracy (%)",
    "accuracy": "Accuracy (%)",
    "average_prediction_latency_ns": "Prediction latency (ns)",
    "avg_prediction_latency_ns": "Prediction latency (ns)",
    "prediction_latency_ns": "Prediction latency (ns)",
    "latency_ns": "Prediction latency (ns)",
    "average_real_seconds": "Average execution time (s)",
    "avg_real_seconds": "Average execution time (s)",
    "execution_time_seconds": "Execution time (s)",
    "total_real_seconds": "Total execution time (s)",
    "average_ipc": "Average IPC",
    "avg_ipc": "Average IPC",
    "geomean_ipc": "Geomean IPC",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []

    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        headers = list(reader.fieldnames or [])

    return headers, rows


def clean_cell(value: str) -> str:
    value = str(value).replace("|", r"\|").strip()

    try:
        number = float(value)

        if number.is_integer() and abs(number) < 1e15:
            return str(int(number))

        if abs(number) >= 1_000_000:
            return f"{number:,.0f}"

        return f"{number:.6f}".rstrip("0").rstrip(".")
    except ValueError:
        return value


def markdown_table(
    headers: list[str],
    rows: Iterable[Iterable[str]],
) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for row in rows:
        lines.append(
            "| " + " | ".join(clean_cell(cell) for cell in row) + " |"
        )

    return "\n".join(lines)


def task1_table(path: Path) -> str:
    headers, rows = read_csv(path)

    if not rows:
        return f"> Missing summary table: `{path}`"

    selected = [
        column
        for column in PREFERRED_TASK1_COLUMNS
        if column in headers
    ]

    # Avoid duplicate aliases that represent the same metric.
    metric_groups = [
        ["predictor"],
        ["average_mpki", "avg_mpki", "mpki"],
        [
            "average_accuracy_percent",
            "avg_accuracy_percent",
            "accuracy_percent",
            "accuracy",
        ],
        [
            "average_prediction_latency_ns",
            "avg_prediction_latency_ns",
            "prediction_latency_ns",
            "latency_ns",
        ],
        [
            "average_real_seconds",
            "avg_real_seconds",
            "execution_time_seconds",
            "total_real_seconds",
        ],
        ["average_ipc", "avg_ipc"],
        ["geomean_ipc"],
    ]

    chosen: list[str] = []

    for group in metric_groups:
        match = next(
            (column for column in group if column in selected),
            None,
        )
        if match:
            chosen.append(match)

    if not chosen:
        chosen = headers[:10]

    display_headers = [
        COLUMN_LABELS.get(column, column.replace("_", " ").title())
        for column in chosen
    ]

    table_rows = [
        [row.get(column, "") for column in chosen]
        for row in rows
    ]

    return markdown_table(display_headers, table_rows)


def strip_first_title(text: str) -> str:
    lines = text.splitlines()

    if lines and lines[0].startswith("# "):
        lines = lines[1:]

        while lines and not lines[0].strip():
            lines = lines[1:]

    return "\n".join(lines).strip()


def include_markdown(path: Path) -> str:
    if not path.is_file():
        return f"> Missing document: `{path}`"

    return strip_first_title(
        path.read_text(encoding="utf-8", errors="replace")
    )


def relative_from_reports(path: Path) -> str:
    return "../" + path.as_posix()


def discover_graphs() -> list[Path]:
    graph_root = RESULTS / "graphs"

    if not graph_root.is_dir():
        return []

    return sorted(graph_root.rglob("*.png"))


def task1_graphs(graphs: list[Path]) -> list[Path]:
    task1 = [
        path
        for path in graphs
        if "/task1/" in f"/{path.as_posix()}/"
    ]

    metric_order = [
        "mpki",
        "accuracy",
        "latency",
        "execution",
        "time",
        "ipc",
        "threshold",
        "occupancy",
        "override",
    ]

    chosen: list[Path] = []
    seen_names: set[str] = set()

    for metric in metric_order:
        for path in task1:
            lower = path.name.lower()

            if metric in lower and lower not in seen_names:
                chosen.append(path)
                seen_names.add(lower)

            if len(chosen) >= 12:
                return chosen

    for path in task1:
        if path.name.lower() not in seen_names:
            chosen.append(path)
            seen_names.add(path.name.lower())

        if len(chosen) >= 12:
            break

    return chosen


def existing(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.is_file()]


def graph_block(
    title: str,
    paths: list[Path],
) -> list[str]:
    lines = [f"### {title}", ""]

    if not paths:
        lines.extend([
            "> No matching graph files were found when this report was generated.",
            "",
        ])
        return lines

    for path in paths:
        caption = path.stem.replace("_", " ").replace("-", " ").title()
        lines.extend([
            f"**{caption}**",
            "",
            f"![{caption}]({relative_from_reports(path)})",
            "",
        ])

    return lines


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)

    graphs = discover_graphs()

    llc_size_graphs = existing([
        RESULTS / "graphs/task2/llc_size/single/geomean_ipc.png",
        RESULTS / "graphs/task2/llc_size/single/llc_miss_percent.png",
        RESULTS / "graphs/task2/llc_size/four_core/sum_ipc.png",
        RESULTS / "graphs/task2/llc_size/four_core/llc_miss_percent.png",
    ])

    associativity_graphs = existing([
        RESULTS / "graphs/task2/llc_associativity/single/geomean_ipc.png",
        RESULTS / "graphs/task2/llc_associativity/single/percent_change_overview.png",
        RESULTS / "graphs/task2/llc_associativity/four_core/sum_ipc.png",
        RESULTS / "graphs/task2/llc_associativity/four_core/percent_change_overview.png",
    ])

    replacement_graphs = existing([
        RESULTS / "graphs/task2/replacement_policy_size/single/02_geomean_ipc_vs_size.png",
        RESULTS / "graphs/task2/replacement_policy_size/single/05_llc_miss_percent_vs_size.png",
        RESULTS / "graphs/task2/replacement_policy_size/four_core/01_sum_ipc_vs_size.png",
        RESULTS / "graphs/task2/replacement_policy_size/four_core/05_llc_miss_percent_vs_size.png",
    ])

    hcit_graphs = existing([
        RESULTS / "graphs/task2/hcit_comparison/single/01_geomean_ipc.png",
        RESULTS / "graphs/task2/hcit_comparison/single/12_hcit_final_threshold.png",
        RESULTS / "graphs/task2/hcit_comparison/single/14_hcit_utility.png",
        RESULTS / "graphs/task2/hcit_comparison/four_core/01_sum_ipc.png",
        RESULTS / "graphs/task2/hcit_comparison/four_core/12_hcit_final_threshold.png",
        RESULTS / "graphs/task2/hcit_comparison/four_core/14_hcit_utility.png",
    ])

    lines: list[str] = [
        "# Computer Architecture Assignment — Labs 9, 10 and 11",
        "",
        "**Student name:** [ENTER NAME]  ",
        "**Student ID:** [ENTER ID]  ",
        "**Course:** Computer Architecture  ",
        "**Simulator:** ChampSim",
        "",
        "---",
        "",
        "## Abstract",
        "",
        (
            "This report evaluates branch predictors and last-level-cache configurations "
            "using ChampSim. Task 1 compares the existing bimodal, gshare, perceptron and "
            "hashed-perceptron predictors, a Modified Bullseye predictor and an adaptive-"
            "threshold Bullseye predictor. Task 2 evaluates LLC capacity, associativity and "
            "replacement policies, including implemented MRU, deterministic Random and "
            "adaptive Hard-to-Cache Identification Table (HCIT) policies."
        ),
        "",
        "## Experimental methodology",
        "",
        "- Single-core and four-core ChampSim configurations were evaluated.",
        "- L1-I: 32 KB, 8-way, LRU.",
        "- L1-D: 32 KB, 8-way, LRU.",
        "- L2: 256 KB, 8-way, LRU.",
        "- Default LLC: 4 MB, 16-way, LRU.",
        "- Cache block size: 64 bytes.",
        "- Four traces were used for every single-core configuration.",
        "- The four-core mix was produced by the submitted seeded random trace generator.",
        "- Warm-up: 1 million instructions; measured simulation: 10 million instructions.",
        "- Predictor lookup latency is host-side average lookup time in nanoseconds and includes timer overhead.",
        "- LLC writes are reported as LLC RFO accesses plus LLC writeback accesses; both are retained separately in detailed CSV files.",
        "",
        "### Block-size assumption",
        "",
        (
            "The assignment states that the 64-byte block size has an exception for Task 2(d), "
            "but no alternative block sizes are specified. The experiments therefore retain "
            "64-byte blocks rather than inventing an unsupported configuration."
        ),
        "",
        "---",
        "",
        "# Task 1 — Branch Prediction",
        "",
        "## Existing and proposed predictors",
        "",
        (
            "The evaluated predictors are bimodal, gshare, perceptron, hashed perceptron, "
            "Modified Bullseye and adaptive-threshold Modified Bullseye."
        ),
        "",
        "## Single-core predictor summary",
        "",
        task1_table(TASK1_SINGLE),
        "",
        "## Four-core predictor summary",
        "",
        task1_table(TASK1_FOUR),
        "",
        "## Modified Bullseye design",
        "",
        include_markdown(REPORTS / "modified_bullseye_design.md"),
        "",
        "## Adaptive-threshold Bullseye design",
        "",
        include_markdown(REPORTS / "adaptive_bullseye_design.md"),
        "",
        "## Task 1 graph results",
        "",
    ]

    lines.extend(graph_block(
        "Selected branch-prediction graphs",
        task1_graphs(graphs),
    ))

    lines.extend([
        "## Task 1 conclusions",
        "",
        (
            "Prediction quality and predictor complexity must be considered together. "
            "A lower MPKI and higher accuracy can improve IPC, but a larger predictor may "
            "increase lookup latency and simulation overhead. The Modified Bullseye design "
            "concentrates additional resources on difficult branches, while the adaptive "
            "version changes its threshold according to observed usefulness and occupancy."
        ),
        "",
        "---",
        "",
        "# Task 2 — Last-Level Cache",
        "",
        "## LLC size, associativity and replacement-policy analysis",
        "",
        include_markdown(REPORTS / "task2_results_analysis.md"),
        "",
        "## MRU and Random implementations",
        "",
        include_markdown(REPORTS / "mru_random_design.md"),
        "",
        "## Adaptive HCIT design",
        "",
        include_markdown(REPORTS / "adaptive_hcit_design.md"),
        "",
        "## Adaptive HCIT experimental analysis",
        "",
        include_markdown(REPORTS / "task2_hcit_results_analysis.md"),
        "",
        "## Task 2 graph results",
        "",
    ])

    lines.extend(graph_block("LLC-size graphs", llc_size_graphs))
    lines.extend(graph_block("Associativity graphs", associativity_graphs))
    lines.extend(graph_block(
        "Replacement-policy and size graphs",
        replacement_graphs,
    ))
    lines.extend(graph_block("HCIT graphs", hcit_graphs))

    lines.extend([
        "## Overall conclusions",
        "",
        (
            "LLC capacity, associativity and replacement policy interact with workload "
            "locality. Larger capacity generally reduces capacity misses, while lower "
            "associativity can alter conflict behaviour and address mapping. LRU remains "
            "a strong baseline; RRIP-family and PC-correlated policies can improve results "
            "when they identify low-reuse lines. MRU and Random demonstrate the cost or "
            "occasional benefit of discarding locality information."
        ),
        "",
        (
            "HCIT selectively allocates detailed tracking to candidates showing persistent "
            "miss pressure. It combines adaptive admission and removal with preferential "
            "RRIP insertion and delayed eviction. Its internal threshold, occupancy and "
            "protection-utility statistics demonstrate that the policy changes selectivity "
            "according to observed behaviour."
        ),
        "",
        "---",
        "",
        "# Reproducibility and submitted material",
        "",
        "- Predictor source files are stored in `branch/`.",
        "- Replacement-policy source files are stored in `replacement/`.",
        "- Experiment runners, parsers, plotting and analysis scripts are stored in `scripts/`.",
        "- Raw outputs and timing files are stored in `results/raw/`.",
        "- Parsed tables are stored in `results/csv/`.",
        "- Graphs are stored in `results/graphs/`.",
        "- Configuration records are stored in `configs/`.",
        "- Random-trace generator evidence is stored in `random_trace_output/`.",
        "- Supporting design documents and the submission checklist are stored in `reports/`.",
        "",
        "# Appendix — Important result files",
        "",
        "- `results/csv/task1_single_summary_all_predictors.csv`",
        "- `results/csv/task1_four_core_summary_all_predictors.csv`",
        "- `results/csv/task2_llc_size_single_summary.csv`",
        "- `results/csv/task2_llc_size_four_core_summary.csv`",
        "- `results/csv/task2_llc_associativity_single_summary.csv`",
        "- `results/csv/task2_llc_associativity_four_core_summary.csv`",
        "- `results/csv/task2_replacement_policy_size_single_summary_with_hcit.csv`",
        "- `results/csv/task2_replacement_policy_size_four_core_summary_with_hcit.csv`",
        "- `results/csv/task2_hcit_internal_single.csv`",
        "- `results/csv/task2_hcit_internal_four_core.csv`",
        "",
    ])

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    inventory_lines = [
        f"{index + 1:03d} {path.as_posix()}"
        for index, path in enumerate(graphs)
    ]
    OUT_INVENTORY.write_text(
        "\n".join(inventory_lines) + ("\n" if inventory_lines else ""),
        encoding="utf-8",
    )

    print("Final Markdown report assembled.")
    print(f"Report:          {OUT_REPORT}")
    print(f"Graph inventory: {OUT_INVENTORY}")
    print(f"Graphs found:    {len(graphs)}")
    print()
    print("Before submission, replace [ENTER NAME] and [ENTER ID].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
