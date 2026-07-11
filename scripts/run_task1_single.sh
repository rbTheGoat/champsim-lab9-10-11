#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10

PREDICTORS=(
    "bimodal"
    "gshare"
    "hashed_perceptron"
    "perceptron"
)

TRACES=(
    "401.bzip2-277B.champsimtrace.xz"
    "403.gcc-16B.champsimtrace.xz"
    "605.mcf_s-665B.champsimtrace.xz"
    "619.lbm_s-3766B.champsimtrace.xz"
)

RAW_DIRECTORY="results/raw/task1/single"
BUILD_DIRECTORY="$RAW_DIRECTORY/build_logs"
TIME_DIRECTORY="$RAW_DIRECTORY/timing"
OUTPUT_DIRECTORY="$RAW_DIRECTORY/simulator_output"
MANIFEST="$RAW_DIRECTORY/run_manifest.csv"

mkdir -p \
    "$BUILD_DIRECTORY" \
    "$TIME_DIRECTORY" \
    "$OUTPUT_DIRECTORY"

echo "predictor,trace,binary,result_file,timing_file" > "$MANIFEST"

for predictor in "${PREDICTORS[@]}"; do
    binary="${predictor}-no-no-no-no-lru-1core"
    build_log="$BUILD_DIRECTORY/${predictor}_build.txt"

    echo
    echo "============================================================"
    echo "Building predictor: $predictor"
    echo "============================================================"

    ./build_champsim.sh "$predictor" no no no no lru 1 \
        |& tee "$build_log"

    if [[ ! -x "bin/$binary" ]]; then
        echo "ERROR: expected binary not found: bin/$binary" >&2
        exit 1
    fi

    for trace in "${TRACES[@]}"; do
        trace_tag="${trace%.champsimtrace.xz}"
        output_file="$OUTPUT_DIRECTORY/${predictor}__${trace_tag}.txt"
        timing_file="$TIME_DIRECTORY/${predictor}__${trace_tag}.txt"

        echo
        echo "------------------------------------------------------------"
        echo "Predictor: $predictor"
        echo "Trace:     $trace"
        echo "------------------------------------------------------------"

        /usr/bin/time -p \
            -o "$timing_file" \
            ./run_champsim.sh \
            "$binary" \
            "$WARMUP_MILLIONS" \
            "$SIMULATION_MILLIONS" \
            "$trace"

        generated_result=$(
            find "results_${SIMULATION_MILLIONS}M" \
                -maxdepth 1 \
                -type f \
                -printf '%T@ %p\n' \
                | sort -nr \
                | head -1 \
                | cut -d' ' -f2-
        )

        if [[ -z "$generated_result" || ! -f "$generated_result" ]]; then
            echo "ERROR: result file was not found." >&2
            exit 1
        fi

        cp "$generated_result" "$output_file"

        if ! grep -q "ChampSim completed all CPUs" "$output_file"; then
            echo "ERROR: simulation did not complete correctly." >&2
            exit 1
        fi

        if ! grep -q "Average Predictor Lookup Latency" "$output_file"; then
            echo "ERROR: latency output is missing." >&2
            exit 1
        fi

        echo \
            "$predictor,$trace,$binary,$output_file,$timing_file" \
            >> "$MANIFEST"

        echo "Saved result: $output_file"
        echo "Saved timing: $timing_file"
    done
done

echo
echo "============================================================"
echo "Task 1 single-core experiments completed successfully."
echo "Manifest: $MANIFEST"
echo "============================================================"
