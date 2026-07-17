#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path
from statistics import mean

MANIFEST = Path("results/raw/task1/four_core/run_manifest.csv")
DETAIL_CSV = Path("results/csv/task1_four_core_results.csv")
SUMMARY_CSV = Path("results/csv/task1_four_core_summary.csv")

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

IPC_RE = re.compile(
    rf"CPU\s+([0-3])\s+cumulative IPC:\s*({FLOAT})",
    re.IGNORECASE,
)
ACCURACY_RE = re.compile(
    rf"CPU\s+([0-3])\s+Branch Prediction Accuracy:\s*({FLOAT})%",
    re.IGNORECASE,
)
MPKI_RE = re.compile(
    rf"CPU\s+([0-3])\s+Branch Prediction Accuracy:.*?\bMPKI:\s*({FLOAT})",
    re.IGNORECASE,
)
LATENCY_RE = re.compile(
    rf"CPU\s+([0-3])\s+Average Predictor Lookup Latency \(ns\):\s*({FLOAT})",
    re.IGNORECASE,
)
SAMPLES_RE = re.compile(
    r"CPU\s+([0-3])\s+Predictor Lookup Samples:\s*(\d+)",
    re.IGNORECASE,
)

DETAIL_COLUMNS = [
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

SUMMARY_COLUMNS = [
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


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def parse_timing(path: Path) -> dict[str, float]:
    if not path.is_file():
        fail(f"Timing file not found: {path}")

    values: dict[str, float] = {}

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"real", "user", "sys"}:
            values[parts[0]] = float(parts[1])

    missing = {"real", "user", "sys"} - values.keys()
    if missing:
        fail(f"Missing timing fields {sorted(missing)} in {path}")

    return values


def last_float_by_core(pattern, text: str, field_name: str, path: Path) -> dict[int, float]:
    values: dict[int, float] = {}
    for core_text, value_text in pattern.findall(text):
        values[int(core_text)] = float(value_text)

    missing = set(range(4)) - values.keys()
    if missing:
        fail(f"Missing {field_name} for cores {sorted(missing)} in {path}")

    return values


def last_int_by_core(pattern, text: str, field_name: str, path: Path) -> dict[int, int]:
    values: dict[int, int] = {}
    for core_text, value_text in pattern.findall(text):
        values[int(core_text)] = int(value_text)

    missing = set(range(4)) - values.keys()
    if missing:
        fail(f"Missing {field_name} for cores {sorted(missing)} in {path}")

    return values


def geometric_mean(values: list[float]) -> float:
    if any(value <= 0 for value in values):
        fail("IPC values must be positive for geometric mean")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def main() -> int:
    if not MANIFEST.is_file():
        fail(f"Manifest not found: {MANIFEST}")

    DETAIL_CSV.parent.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open(newline="", encoding="utf-8") as manifest_file:
        reader = csv.DictReader(manifest_file)
        manifest_rows = list(reader)

    if len(manifest_rows) != 4:
        fail(f"Expected 4 predictor runs in manifest, found {len(manifest_rows)}")

    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for row in manifest_rows:
        predictor = row["predictor"]
        result_path = Path(row["result_file"])
        timing_path = Path(row["timing_file"])

        if not result_path.is_file():
            fail(f"Result file not found: {result_path}")

        text = result_path.read_text(encoding="utf-8", errors="replace")

        if "ChampSim completed all CPUs" not in text:
            fail(f"Completion marker missing from {result_path}")

        ipc = last_float_by_core(IPC_RE, text, "IPC", result_path)
        accuracy = last_float_by_core(ACCURACY_RE, text, "accuracy", result_path)
        mpki = last_float_by_core(MPKI_RE, text, "MPKI", result_path)
        latency = last_float_by_core(LATENCY_RE, text, "latency", result_path)
        samples = last_int_by_core(SAMPLES_RE, text, "samples", result_path)
        timing = parse_timing(timing_path)

        traces = [
            row["core0_trace"],
            row["core1_trace"],
            row["core2_trace"],
            row["core3_trace"],
        ]

        for core in range(4):
            detail_rows.append({
                "predictor": predictor,
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

        ipc_values = [ipc[i] for i in range(4)]
        accuracy_values = [accuracy[i] for i in range(4)]
        mpki_values = [mpki[i] for i in range(4)]
        latency_values = [latency[i] for i in range(4)]

        summary_rows.append({
            "predictor": predictor,
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
        })

    if len(detail_rows) != 16:
        fail(f"Expected 16 core-level rows, found {len(detail_rows)}")

    with DETAIL_CSV.open("w", newline="", encoding="utf-8") as detail_file:
        writer = csv.DictWriter(detail_file, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        writer.writerows(detail_rows)

    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Parsed predictor runs: {len(summary_rows)}")
    print(f"Parsed core rows:      {len(detail_rows)}")
    print(f"Detailed CSV: {DETAIL_CSV}")
    print(f"Summary CSV:  {SUMMARY_CSV}")
    print()
    print(
        f"{'Predictor':<20}"
        f"{'Avg IPC':>11}"
        f"{'Sum IPC':>11}"
        f"{'Avg Accuracy':>16}"
        f"{'Avg MPKI':>12}"
        f"{'Avg Latency(ns)':>18}"
        f"{'Run Time(s)':>14}"
    )

    for row in summary_rows:
        print(
            f"{str(row['predictor']):<20}"
            f"{float(row['average_ipc']):>11.5f}"
            f"{float(row['sum_ipc']):>11.5f}"
            f"{float(row['average_accuracy_percent']):>16.5f}"
            f"{float(row['average_mpki']):>12.5f}"
            f"{float(row['average_lookup_latency_ns']):>18.5f}"
            f"{float(row['run_real_seconds']):>14.3f}"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
