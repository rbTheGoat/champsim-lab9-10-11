#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path
from statistics import mean

SINGLE_MANIFEST = Path(
    "results/raw/task1/modified_bullseye/single/run_manifest.csv"
)
FOUR_MANIFEST = Path(
    "results/raw/task1/modified_bullseye/four_core/run_manifest.csv"
)

BASE_SINGLE_DETAIL = Path("results/csv/task1_single_results.csv")
BASE_SINGLE_SUMMARY = Path("results/csv/task1_single_summary.csv")
BASE_FOUR_DETAIL = Path("results/csv/task1_four_core_results.csv")
BASE_FOUR_SUMMARY = Path("results/csv/task1_four_core_summary.csv")

MB_SINGLE_DETAIL = Path(
    "results/csv/task1_modified_bullseye_single_results.csv"
)
MB_SINGLE_SUMMARY = Path(
    "results/csv/task1_modified_bullseye_single_summary.csv"
)
MB_FOUR_DETAIL = Path(
    "results/csv/task1_modified_bullseye_four_core_results.csv"
)
MB_FOUR_SUMMARY = Path(
    "results/csv/task1_modified_bullseye_four_core_summary.csv"
)

COMBINED_SINGLE_DETAIL = Path(
    "results/csv/task1_single_results_with_modified_bullseye.csv"
)
COMBINED_SINGLE_SUMMARY = Path(
    "results/csv/task1_single_summary_with_modified_bullseye.csv"
)
COMBINED_FOUR_DETAIL = Path(
    "results/csv/task1_four_core_results_with_modified_bullseye.csv"
)
COMBINED_FOUR_SUMMARY = Path(
    "results/csv/task1_four_core_summary_with_modified_bullseye.csv"
)

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

SINGLE_IPC_RE = re.compile(
    rf"CPU\s+0\s+cumulative IPC:\s*({FLOAT})",
    re.IGNORECASE,
)
SINGLE_ACCURACY_RE = re.compile(
    rf"CPU\s+0\s+Branch Prediction Accuracy:\s*({FLOAT})%",
    re.IGNORECASE,
)
SINGLE_MPKI_RE = re.compile(
    rf"\bMPKI:\s*({FLOAT})",
    re.IGNORECASE,
)
SINGLE_LATENCY_RE = re.compile(
    rf"CPU\s+0\s+Average Predictor Lookup Latency \(ns\):\s*({FLOAT})",
    re.IGNORECASE,
)
SINGLE_SAMPLES_RE = re.compile(
    r"CPU\s+0\s+Predictor Lookup Samples:\s*(\d+)",
    re.IGNORECASE,
)

FOUR_IPC_RE = re.compile(
    rf"CPU\s+([0-3])\s+cumulative IPC:\s*({FLOAT})",
    re.IGNORECASE,
)
FOUR_ACCURACY_RE = re.compile(
    rf"CPU\s+([0-3])\s+Branch Prediction Accuracy:\s*({FLOAT})%",
    re.IGNORECASE,
)
FOUR_MPKI_RE = re.compile(
    rf"CPU\s+([0-3])\s+Branch Prediction Accuracy:.*?\bMPKI:\s*({FLOAT})",
    re.IGNORECASE,
)
FOUR_LATENCY_RE = re.compile(
    rf"CPU\s+([0-3])\s+Average Predictor Lookup Latency \(ns\):\s*({FLOAT})",
    re.IGNORECASE,
)
FOUR_SAMPLES_RE = re.compile(
    r"CPU\s+([0-3])\s+Predictor Lookup Samples:\s*(\d+)",
    re.IGNORECASE,
)

SINGLE_DETAIL_FIELDS = [
    "predictor",
    "trace",
    "binary",
    "result_file",
    "timing_file",
    "ipc",
    "accuracy_percent",
    "mpki",
    "lookup_latency_ns",
    "lookup_samples",
    "real_seconds",
    "user_seconds",
    "sys_seconds",
]

SINGLE_SUMMARY_FIELDS = [
    "predictor",
    "trace_count",
    "average_ipc",
    "geomean_ipc",
    "average_accuracy_percent",
    "average_mpki",
    "average_lookup_latency_ns",
    "average_real_seconds",
    "total_real_seconds",
]

FOUR_DETAIL_FIELDS = [
    "predictor",
    "mix_number",
    "core",
    "trace",
    "binary",
    "result_file",
    "timing_file",
    "ipc",
    "accuracy_percent",
    "mpki",
    "lookup_latency_ns",
    "lookup_samples",
    "run_real_seconds",
    "run_user_seconds",
    "run_sys_seconds",
]

FOUR_SUMMARY_FIELDS = [
    "predictor",
    "mix_number",
    "core_count",
    "average_ipc",
    "geomean_ipc",
    "sum_ipc",
    "average_accuracy_percent",
    "average_mpki",
    "average_lookup_latency_ns",
    "total_lookup_samples",
    "run_real_seconds",
    "run_user_seconds",
    "run_sys_seconds",
]

PREDICTOR_ORDER = [
    "bimodal",
    "gshare",
    "hashed_perceptron",
    "perceptron",
    "modified_bullseye",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"Missing CSV file: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fields: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def extract_last(
    pattern: re.Pattern[str],
    text: str,
    label: str,
    path: Path,
) -> str:
    matches = pattern.findall(text)

    if not matches:
        fail(f"Could not find {label} in {path}")

    return matches[-1]


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
            values[parts[0]] = float(parts[1])

    missing = {"real", "user", "sys"} - values.keys()

    if missing:
        fail(f"Missing timing values {sorted(missing)} in {path}")

    return values


def geometric_mean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        fail("Geometric mean requires positive IPC values")

    return math.exp(
        sum(math.log(value) for value in values) / len(values)
    )


def parse_single() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    manifest_rows = read_csv(SINGLE_MANIFEST)

    if len(manifest_rows) != 4:
        fail(
            "Expected four Modified Bullseye single-core runs, "
            f"found {len(manifest_rows)}"
        )

    detail_rows: list[dict[str, object]] = []

    for row in manifest_rows:
        result_path = Path(row["result_file"])
        timing_path = Path(row["timing_file"])

        if not result_path.is_file():
            fail(f"Missing result file: {result_path}")

        text = result_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        timing = parse_timing(timing_path)

        detail_rows.append({
            "predictor": row["predictor"],
            "trace": row["trace"],
            "binary": row["binary"],
            "result_file": row["result_file"],
            "timing_file": row["timing_file"],
            "ipc": float(
                extract_last(
                    SINGLE_IPC_RE,
                    text,
                    "IPC",
                    result_path,
                )
            ),
            "accuracy_percent": float(
                extract_last(
                    SINGLE_ACCURACY_RE,
                    text,
                    "accuracy",
                    result_path,
                )
            ),
            "mpki": float(
                extract_last(
                    SINGLE_MPKI_RE,
                    text,
                    "MPKI",
                    result_path,
                )
            ),
            "lookup_latency_ns": float(
                extract_last(
                    SINGLE_LATENCY_RE,
                    text,
                    "latency",
                    result_path,
                )
            ),
            "lookup_samples": int(
                extract_last(
                    SINGLE_SAMPLES_RE,
                    text,
                    "lookup samples",
                    result_path,
                )
            ),
            "real_seconds": timing["real"],
            "user_seconds": timing["user"],
            "sys_seconds": timing["sys"],
        })

    ipc_values = [float(row["ipc"]) for row in detail_rows]
    accuracy_values = [
        float(row["accuracy_percent"]) for row in detail_rows
    ]
    mpki_values = [float(row["mpki"]) for row in detail_rows]
    latency_values = [
        float(row["lookup_latency_ns"]) for row in detail_rows
    ]
    real_values = [
        float(row["real_seconds"]) for row in detail_rows
    ]

    summary_rows: list[dict[str, object]] = [{
        "predictor": "modified_bullseye",
        "trace_count": 4,
        "average_ipc": mean(ipc_values),
        "geomean_ipc": geometric_mean(ipc_values),
        "average_accuracy_percent": mean(accuracy_values),
        "average_mpki": mean(mpki_values),
        "average_lookup_latency_ns": mean(latency_values),
        "average_real_seconds": mean(real_values),
        "total_real_seconds": sum(real_values),
    }]

    return detail_rows, summary_rows


def last_float_by_core(
    pattern: re.Pattern[str],
    text: str,
    label: str,
    path: Path,
) -> dict[int, float]:
    values: dict[int, float] = {}

    for core_text, value_text in pattern.findall(text):
        values[int(core_text)] = float(value_text)

    missing = set(range(4)) - values.keys()

    if missing:
        fail(
            f"Missing {label} for cores {sorted(missing)} in {path}"
        )

    return values


def last_int_by_core(
    pattern: re.Pattern[str],
    text: str,
    label: str,
    path: Path,
) -> dict[int, int]:
    values: dict[int, int] = {}

    for core_text, value_text in pattern.findall(text):
        values[int(core_text)] = int(value_text)

    missing = set(range(4)) - values.keys()

    if missing:
        fail(
            f"Missing {label} for cores {sorted(missing)} in {path}"
        )

    return values


def parse_four_core() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    manifest_rows = read_csv(FOUR_MANIFEST)

    if len(manifest_rows) != 1:
        fail(
            "Expected one Modified Bullseye four-core run, "
            f"found {len(manifest_rows)}"
        )

    row = manifest_rows[0]
    result_path = Path(row["result_file"])
    timing_path = Path(row["timing_file"])

    if not result_path.is_file():
        fail(f"Missing result file: {result_path}")

    text = result_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if "ChampSim completed all CPUs" not in text:
        fail(f"Completion marker missing from {result_path}")

    timing = parse_timing(timing_path)

    ipc = last_float_by_core(
        FOUR_IPC_RE, text, "IPC", result_path
    )
    accuracy = last_float_by_core(
        FOUR_ACCURACY_RE, text, "accuracy", result_path
    )
    mpki = last_float_by_core(
        FOUR_MPKI_RE, text, "MPKI", result_path
    )
    latency = last_float_by_core(
        FOUR_LATENCY_RE, text, "latency", result_path
    )
    samples = last_int_by_core(
        FOUR_SAMPLES_RE, text, "samples", result_path
    )

    traces = [
        row["core0_trace"],
        row["core1_trace"],
        row["core2_trace"],
        row["core3_trace"],
    ]

    detail_rows: list[dict[str, object]] = []

    for core in range(4):
        detail_rows.append({
            "predictor": row["predictor"],
            "mix_number": row["mix_number"],
            "core": core,
            "trace": traces[core],
            "binary": row["binary"],
            "result_file": row["result_file"],
            "timing_file": row["timing_file"],
            "ipc": ipc[core],
            "accuracy_percent": accuracy[core],
            "mpki": mpki[core],
            "lookup_latency_ns": latency[core],
            "lookup_samples": samples[core],
            "run_real_seconds": timing["real"],
            "run_user_seconds": timing["user"],
            "run_sys_seconds": timing["sys"],
        })

    ipc_values = [ipc[core] for core in range(4)]
    accuracy_values = [accuracy[core] for core in range(4)]
    mpki_values = [mpki[core] for core in range(4)]
    latency_values = [latency[core] for core in range(4)]

    summary_rows: list[dict[str, object]] = [{
        "predictor": row["predictor"],
        "mix_number": row["mix_number"],
        "core_count": 4,
        "average_ipc": mean(ipc_values),
        "geomean_ipc": geometric_mean(ipc_values),
        "sum_ipc": sum(ipc_values),
        "average_accuracy_percent": mean(accuracy_values),
        "average_mpki": mean(mpki_values),
        "average_lookup_latency_ns": mean(latency_values),
        "total_lookup_samples": sum(samples.values()),
        "run_real_seconds": timing["real"],
        "run_user_seconds": timing["user"],
        "run_sys_seconds": timing["sys"],
    }]

    return detail_rows, summary_rows


def sort_by_predictor(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    order = {
        predictor: index
        for index, predictor in enumerate(PREDICTOR_ORDER)
    }

    return sorted(
        rows,
        key=lambda row: (
            order.get(str(row["predictor"]), 999),
            str(row.get("trace", "")),
            int(row.get("core", 0)),
        ),
    )


def main() -> int:
    single_detail, single_summary = parse_single()
    four_detail, four_summary = parse_four_core()

    write_csv(
        MB_SINGLE_DETAIL,
        single_detail,
        SINGLE_DETAIL_FIELDS,
    )
    write_csv(
        MB_SINGLE_SUMMARY,
        single_summary,
        SINGLE_SUMMARY_FIELDS,
    )
    write_csv(
        MB_FOUR_DETAIL,
        four_detail,
        FOUR_DETAIL_FIELDS,
    )
    write_csv(
        MB_FOUR_SUMMARY,
        four_summary,
        FOUR_SUMMARY_FIELDS,
    )

    combined_single_detail = [
        row
        for row in read_csv(BASE_SINGLE_DETAIL)
        if row["predictor"] != "modified_bullseye"
    ] + single_detail

    combined_single_summary = [
        row
        for row in read_csv(BASE_SINGLE_SUMMARY)
        if row["predictor"] != "modified_bullseye"
    ] + single_summary

    combined_four_detail = [
        row
        for row in read_csv(BASE_FOUR_DETAIL)
        if row["predictor"] != "modified_bullseye"
    ] + four_detail

    combined_four_summary = [
        row
        for row in read_csv(BASE_FOUR_SUMMARY)
        if row["predictor"] != "modified_bullseye"
    ] + four_summary

    write_csv(
        COMBINED_SINGLE_DETAIL,
        sort_by_predictor(combined_single_detail),
        SINGLE_DETAIL_FIELDS,
    )
    write_csv(
        COMBINED_SINGLE_SUMMARY,
        sort_by_predictor(combined_single_summary),
        SINGLE_SUMMARY_FIELDS,
    )
    write_csv(
        COMBINED_FOUR_DETAIL,
        sort_by_predictor(combined_four_detail),
        FOUR_DETAIL_FIELDS,
    )
    write_csv(
        COMBINED_FOUR_SUMMARY,
        sort_by_predictor(combined_four_summary),
        FOUR_SUMMARY_FIELDS,
    )

    single = single_summary[0]
    four = four_summary[0]

    print("Modified Bullseye results integrated successfully.")
    print()
    print("Single-core averages:")
    print(f"  IPC:          {float(single['average_ipc']):.5f}")
    print(
        "  Accuracy:     "
        f"{float(single['average_accuracy_percent']):.5f}%"
    )
    print(f"  MPKI:         {float(single['average_mpki']):.5f}")
    print(
        "  Latency:      "
        f"{float(single['average_lookup_latency_ns']):.5f} ns"
    )
    print(
        "  Avg run time: "
        f"{float(single['average_real_seconds']):.3f} s"
    )
    print()
    print("Four-core averages:")
    print(f"  Average IPC:  {float(four['average_ipc']):.5f}")
    print(f"  Sum IPC:      {float(four['sum_ipc']):.5f}")
    print(
        "  Accuracy:     "
        f"{float(four['average_accuracy_percent']):.5f}%"
    )
    print(f"  MPKI:         {float(four['average_mpki']):.5f}")
    print(
        "  Latency:      "
        f"{float(four['average_lookup_latency_ns']):.5f} ns"
    )
    print(
        "  Run time:     "
        f"{float(four['run_real_seconds']):.3f} s"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
