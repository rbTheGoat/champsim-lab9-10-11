#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

MANIFEST = Path("results/raw/task1/single/run_manifest.csv")
OUTPUT_CSV = Path("results/csv/task1_single_results.csv")
SUMMARY_CSV = Path("results/csv/task1_single_summary.csv")

FLOAT_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

PATTERNS = {
    "ipc": re.compile(
        rf"CPU\s+0\s+cumulative IPC:\s*({FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
    "accuracy": re.compile(
        rf"CPU\s+0\s+Branch Prediction Accuracy:\s*({FLOAT_PATTERN})%",
        re.IGNORECASE,
    ),
    "mpki": re.compile(
        rf"\bMPKI:\s*({FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
    "latency_ns": re.compile(
        rf"CPU\s+0\s+Average Predictor Lookup Latency \(ns\):\s*({FLOAT_PATTERN})",
        re.IGNORECASE,
    ),
    "samples": re.compile(
        r"CPU\s+0\s+Predictor Lookup Samples:\s*(\d+)",
        re.IGNORECASE,
    ),
}

RESULT_COLUMNS = [
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

SUMMARY_COLUMNS = [
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


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def extract_one(pattern: re.Pattern[str], text: str, field: str, path: Path) -> str:
    matches = pattern.findall(text)
    if not matches:
        fail(f"Could not find {field} in {path}")
    return matches[-1]


def parse_timing(path: Path) -> dict[str, float]:
    if not path.is_file():
        fail(f"Timing file does not exist: {path}")

    values: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"real", "user", "sys"}:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                fail(f"Invalid timing value in {path}: {line}")

    missing = {"real", "user", "sys"} - values.keys()
    if missing:
        fail(f"Missing timing fields {sorted(missing)} in {path}")

    return values


def parse_result(path: Path) -> dict[str, float | int]:
    if not path.is_file():
        fail(f"Result file does not exist: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")

    if "ChampSim completed all CPUs" not in text:
        fail(f"Simulation completion marker missing from {path}")

    return {
        "ipc": float(extract_one(PATTERNS["ipc"], text, "IPC", path)),
        "accuracy_percent": float(
            extract_one(PATTERNS["accuracy"], text, "prediction accuracy", path)
        ),
        "mpki": float(extract_one(PATTERNS["mpki"], text, "MPKI", path)),
        "lookup_latency_ns": float(
            extract_one(PATTERNS["latency_ns"], text, "lookup latency", path)
        ),
        "lookup_samples": int(
            extract_one(PATTERNS["samples"], text, "lookup samples", path)
        ),
    }


def geometric_mean(values: list[float]) -> float:
    if not values:
        fail("Cannot compute geometric mean of an empty list")
    if any(value <= 0 for value in values):
        fail("Geometric mean requires strictly positive IPC values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def main() -> int:
    if not MANIFEST.is_file():
        fail(f"Manifest not found: {MANIFEST}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    parsed_rows: list[dict[str, object]] = []

    with MANIFEST.open(newline="", encoding="utf-8") as manifest_file:
        reader = csv.DictReader(manifest_file)

        required_manifest_columns = {
            "predictor",
            "trace",
            "binary",
            "result_file",
            "timing_file",
        }

        if reader.fieldnames is None:
            fail("Manifest has no CSV header")

        missing_columns = required_manifest_columns - set(reader.fieldnames)
        if missing_columns:
            fail(f"Manifest is missing columns: {sorted(missing_columns)}")

        for manifest_row in reader:
            result_path = Path(manifest_row["result_file"])
            timing_path = Path(manifest_row["timing_file"])

            result_values = parse_result(result_path)
            timing_values = parse_timing(timing_path)

            parsed_rows.append(
                {
                    "predictor": manifest_row["predictor"],
                    "trace": manifest_row["trace"],
                    "binary": manifest_row["binary"],
                    "result_file": manifest_row["result_file"],
                    "timing_file": manifest_row["timing_file"],
                    **result_values,
                    "real_seconds": timing_values["real"],
                    "user_seconds": timing_values["user"],
                    "sys_seconds": timing_values["sys"],
                }
            )

    if len(parsed_rows) != 16:
        fail(f"Expected 16 single-core runs, found {len(parsed_rows)}")

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(parsed_rows)

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in parsed_rows:
        grouped[str(row["predictor"])].append(row)

    summary_rows: list[dict[str, object]] = []

    for predictor in sorted(grouped):
        rows = grouped[predictor]

        if len(rows) != 4:
            fail(f"Expected 4 traces for {predictor}, found {len(rows)}")

        ipc_values = [float(row["ipc"]) for row in rows]
        accuracy_values = [float(row["accuracy_percent"]) for row in rows]
        mpki_values = [float(row["mpki"]) for row in rows]
        latency_values = [float(row["lookup_latency_ns"]) for row in rows]
        real_values = [float(row["real_seconds"]) for row in rows]

        summary_rows.append(
            {
                "predictor": predictor,
                "trace_count": len(rows),
                "average_ipc": mean(ipc_values),
                "geomean_ipc": geometric_mean(ipc_values),
                "average_accuracy_percent": mean(accuracy_values),
                "average_mpki": mean(mpki_values),
                "average_lookup_latency_ns": mean(latency_values),
                "average_real_seconds": mean(real_values),
                "total_real_seconds": sum(real_values),
            }
        )

    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Parsed runs: {len(parsed_rows)}")
    print(f"Detailed CSV: {OUTPUT_CSV}")
    print(f"Summary CSV:  {SUMMARY_CSV}")
    print()
    print(
        f"{'Predictor':<20}"
        f"{'Avg IPC':>12}"
        f"{'Avg Accuracy':>16}"
        f"{'Avg MPKI':>12}"
        f"{'Avg Latency(ns)':>18}"
        f"{'Avg Time(s)':>14}"
    )

    for row in summary_rows:
        print(
            f"{str(row['predictor']):<20}"
            f"{float(row['average_ipc']):>12.5f}"
            f"{float(row['average_accuracy_percent']):>16.5f}"
            f"{float(row['average_mpki']):>12.5f}"
            f"{float(row['average_lookup_latency_ns']):>18.5f}"
            f"{float(row['average_real_seconds']):>14.3f}"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
