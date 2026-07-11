from pathlib import Path
import random
import sys

MANIFEST = Path("required_traces.txt")
TRACE_DIRECTORY = Path("dpc3_traces")
OUTPUT_FILE = Path("random_trace_output/selected_4core_traces.txt")
SEED = 2026
NUMBER_OF_CORES = 4


def main() -> int:
    if not MANIFEST.is_file():
        print(f"Error: manifest not found: {MANIFEST}", file=sys.stderr)
        return 1

    traces = [
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if len(traces) < NUMBER_OF_CORES:
        print(
            f"Error: at least {NUMBER_OF_CORES} traces are required.",
            file=sys.stderr,
        )
        return 1

    missing = [
        trace
        for trace in traces
        if not (TRACE_DIRECTORY / trace).is_file()
    ]

    if missing:
        print("Error: these trace files are missing:", file=sys.stderr)
        for trace in missing:
            print(f" - {trace}", file=sys.stderr)
        return 1

    generator = random.Random(SEED)
    selected = generator.sample(traces, NUMBER_OF_CORES)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output_lines = [
        f"Random seed: {SEED}",
        f"Trace pool size: {len(traces)}",
        "Selected traces for the 4-core configuration:",
    ]

    for core, trace in enumerate(selected):
        output_lines.append(f"Core {core}: {trace}")

    output_text = "\n".join(output_lines) + "\n"
    OUTPUT_FILE.write_text(output_text, encoding="utf-8")

    print(output_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

