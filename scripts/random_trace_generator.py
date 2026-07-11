from pathlib import Path
import random
import sys

MANIFEST = Path("required_traces.txt")
TRACE_DIRECTORY = Path("dpc3_traces")
OUTPUT_FILE = Path("random_trace_output/selected_4core_traces.txt")

SEED = 2026
CORE_COUNT = 4


def main() -> int:
    if not MANIFEST.is_file():
        print(f"Error: missing {MANIFEST}", file=sys.stderr)
        return 1

    traces = [
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if len(traces) < CORE_COUNT:
        print("Error: fewer than four traces in manifest.", file=sys.stderr)
        return 1

    missing = [
        trace for trace in traces
        if not (TRACE_DIRECTORY / trace).is_file()
    ]

    if missing:
        print("Error: missing trace files:", file=sys.stderr)
        for trace in missing:
            print(f"  {trace}", file=sys.stderr)
        return 1

    generator = random.Random(SEED)
    selected = generator.sample(traces, CORE_COUNT)

    lines = [
        f"Random seed: {SEED}",
        f"Trace pool size: {len(traces)}",
        "Selected traces for the 4-core configuration:",
    ]

    for core, trace in enumerate(selected):
        lines.append(f"Core {core}: {trace}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
