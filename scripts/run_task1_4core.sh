#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10
MIX_NUMBER=1

PREDICTORS=(
    "bimodal"
    "gshare"
    "hashed_perceptron"
    "perceptron"
)

SELECTION_FILE="random_trace_output/selected_4core_traces.txt"
RAW_DIRECTORY="results/raw/task1/four_core"
BUILD_DIRECTORY="$RAW_DIRECTORY/build_logs"
TIME_DIRECTORY="$RAW_DIRECTORY/timing"
OUTPUT_DIRECTORY="$RAW_DIRECTORY/simulator_output"
MANIFEST="$RAW_DIRECTORY/run_manifest.csv"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ -f "$SELECTION_FILE" ]] \
    || fail "Missing trace-selection file: $SELECTION_FILE"

mapfile -t TRACES < <(
    awk -F': ' '/^Core [0-3]: / { print $2 }' "$SELECTION_FILE"
)

[[ "${#TRACES[@]}" -eq 4 ]] \
    || fail "Expected four selected traces, found ${#TRACES[@]}"

declare -A SEEN_TRACES=()

for trace in "${TRACES[@]}"; do
    [[ -n "$trace" ]] || fail "An empty trace name was found"
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing trace file: dpc3_traces/$trace"

    if [[ -n "${SEEN_TRACES[$trace]:-}" ]]; then
        fail "Duplicate selected trace: $trace"
    fi

    SEEN_TRACES["$trace"]=1
done

mkdir -p \
    "$BUILD_DIRECTORY" \
    "$TIME_DIRECTORY" \
    "$OUTPUT_DIRECTORY"

echo \
"predictor,mix_number,core0_trace,core1_trace,core2_trace,core3_trace,binary,result_file,timing_file" \
> "$MANIFEST"

echo "Selected four-core trace mix:"
for core in "${!TRACES[@]}"; do
    echo "  Core $core: ${TRACES[$core]}"
done

for predictor in "${PREDICTORS[@]}"; do
    binary="${predictor}-no-no-no-no-lru-4core"
    build_log="$BUILD_DIRECTORY/${predictor}_build.txt"
    output_file="$OUTPUT_DIRECTORY/${predictor}__mix${MIX_NUMBER}.txt"
    timing_file="$TIME_DIRECTORY/${predictor}__mix${MIX_NUMBER}.txt"

    echo
    echo "============================================================"
    echo "Building four-core predictor: $predictor"
    echo "============================================================"

    ./build_champsim.sh "$predictor" no no no no lru 4 \
        |& tee "$build_log"

    [[ -x "bin/$binary" ]] \
        || fail "Expected binary not found: bin/$binary"

    marker=$(mktemp)
    touch "$marker"

    echo
    echo "------------------------------------------------------------"
    echo "Running predictor: $predictor"
    echo "Mix number:       $MIX_NUMBER"
    echo "------------------------------------------------------------"

    /usr/bin/time -p \
        -o "$timing_file" \
        ./run_4core.sh \
        "$binary" \
        "$WARMUP_MILLIONS" \
        "$SIMULATION_MILLIONS" \
        "$MIX_NUMBER" \
        "${TRACES[0]}" \
        "${TRACES[1]}" \
        "${TRACES[2]}" \
        "${TRACES[3]}"

    generated_result=""

    while IFS= read -r candidate; do
        if grep -q "ChampSim completed all CPUs" "$candidate"; then
            generated_result="$candidate"
            break
        fi
    done < <(
        find . \
            -maxdepth 2 \
            -type f \
            -newer "$marker" \
            \( -path "./results_4core_*/*" -o -path "./results_*M/*" \) \
            -printf '%T@ %p\n' \
        | sort -nr \
        | cut -d' ' -f2-
    )

    rm -f "$marker"

    [[ -n "$generated_result" && -f "$generated_result" ]] \
        || fail "Could not locate the completed four-core result for $predictor"

    cp "$generated_result" "$output_file"

    [[ "$(grep -c "Branch Prediction Accuracy" "$output_file")" -eq 4 ]] \
        || fail "Expected four branch-accuracy lines in $output_file"

    [[ "$(grep -c "Average Predictor Lookup Latency" "$output_file")" -eq 4 ]] \
        || fail "Expected four lookup-latency lines in $output_file"

    [[ "$(grep -c "Predictor Lookup Samples" "$output_file")" -eq 4 ]] \
        || fail "Expected four lookup-sample lines in $output_file"

    echo \
"$predictor,$MIX_NUMBER,${TRACES[0]},${TRACES[1]},${TRACES[2]},${TRACES[3]},$binary,$output_file,$timing_file" \
    >> "$MANIFEST"

    echo "Saved result: $output_file"
    echo "Saved timing: $timing_file"
done

echo
echo "============================================================"
echo "Task 1 four-core experiments completed successfully."
echo "Manifest: $MANIFEST"
echo "============================================================"
