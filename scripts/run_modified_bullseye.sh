#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10
PREDICTOR="modified_bullseye"
MIX_NUMBER=1

SINGLE_TRACES=(
    "401.bzip2-277B.champsimtrace.xz"
    "403.gcc-16B.champsimtrace.xz"
    "605.mcf_s-665B.champsimtrace.xz"
    "619.lbm_s-3766B.champsimtrace.xz"
)

SELECTION_FILE="random_trace_output/selected_4core_traces.txt"

BASE_DIR="results/raw/task1/modified_bullseye"
SINGLE_DIR="$BASE_DIR/single"
FOUR_CORE_DIR="$BASE_DIR/four_core"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

find_completed_result() {
    local marker="$1"
    local expected_binary="$2"
    local candidate=""

    while IFS= read -r candidate; do
        if grep -q "ChampSim completed all CPUs" "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done < <(
        find . \
            -maxdepth 2 \
            -type f \
            -newer "$marker" \
            \( -path "./results_*M/*" -o -path "./results_4core_*/*" \) \
            -name "*${expected_binary}*" \
            -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | cut -d' ' -f2-
    )

    return 1
}

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------

for trace in "${SINGLE_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing single-core trace: dpc3_traces/$trace"
done

[[ -f "$SELECTION_FILE" ]] \
    || fail "Missing four-core trace-selection file: $SELECTION_FILE"

mapfile -t FOUR_CORE_TRACES < <(
    awk -F': ' '/^Core [0-3]: / { print $2 }' "$SELECTION_FILE"
)

[[ "${#FOUR_CORE_TRACES[@]}" -eq 4 ]] \
    || fail "Expected four selected traces, found ${#FOUR_CORE_TRACES[@]}"

declare -A SEEN=()
for trace in "${FOUR_CORE_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing four-core trace: dpc3_traces/$trace"

    [[ -z "${SEEN[$trace]:-}" ]] \
        || fail "Duplicate four-core trace: $trace"

    SEEN["$trace"]=1
done

mkdir -p \
    "$SINGLE_DIR/build_logs" \
    "$SINGLE_DIR/timing" \
    "$SINGLE_DIR/simulator_output" \
    "$FOUR_CORE_DIR/build_logs" \
    "$FOUR_CORE_DIR/timing" \
    "$FOUR_CORE_DIR/simulator_output"

SINGLE_MANIFEST="$SINGLE_DIR/run_manifest.csv"
FOUR_CORE_MANIFEST="$FOUR_CORE_DIR/run_manifest.csv"

echo "predictor,trace,binary,result_file,timing_file" \
    > "$SINGLE_MANIFEST"

echo \
"predictor,mix_number,core0_trace,core1_trace,core2_trace,core3_trace,binary,result_file,timing_file" \
    > "$FOUR_CORE_MANIFEST"

# ---------------------------------------------------------------------------
# Single-core: build once and run four traces
# ---------------------------------------------------------------------------

SINGLE_BINARY="${PREDICTOR}-no-no-no-no-lru-1core"
SINGLE_BUILD_LOG="$SINGLE_DIR/build_logs/${PREDICTOR}_build.txt"

echo
echo "============================================================"
echo "Building Modified Bullseye: single core"
echo "============================================================"

./build_champsim.sh "$PREDICTOR" no no no no lru 1 \
    |& tee "$SINGLE_BUILD_LOG"

[[ -x "bin/$SINGLE_BINARY" ]] \
    || fail "Expected binary not found: bin/$SINGLE_BINARY"

for trace in "${SINGLE_TRACES[@]}"; do
    trace_tag="${trace%.champsimtrace.xz}"
    result_copy="$SINGLE_DIR/simulator_output/${PREDICTOR}__${trace_tag}.txt"
    timing_file="$SINGLE_DIR/timing/${PREDICTOR}__${trace_tag}.txt"

    marker=$(mktemp)
    touch "$marker"

    echo
    echo "------------------------------------------------------------"
    echo "Single-core trace: $trace"
    echo "------------------------------------------------------------"

    /usr/bin/time -p \
        -o "$timing_file" \
        ./run_champsim.sh \
        "$SINGLE_BINARY" \
        "$WARMUP_MILLIONS" \
        "$SIMULATION_MILLIONS" \
        "$trace"

    generated_result=$(
        find_completed_result "$marker" "$SINGLE_BINARY"
    ) || {
        rm -f "$marker"
        fail "Could not locate completed result for $trace"
    }

    rm -f "$marker"

    cp "$generated_result" "$result_copy"

    grep -q "Average Predictor Lookup Latency" "$result_copy" \
        || fail "Latency output missing from $result_copy"

    echo \
"$PREDICTOR,$trace,$SINGLE_BINARY,$result_copy,$timing_file" \
        >> "$SINGLE_MANIFEST"

    echo "Saved result: $result_copy"
    echo "Saved timing: $timing_file"
done

# ---------------------------------------------------------------------------
# Four-core: build once and run selected trace mix
# ---------------------------------------------------------------------------

FOUR_CORE_BINARY="${PREDICTOR}-no-no-no-no-lru-4core"
FOUR_CORE_BUILD_LOG="$FOUR_CORE_DIR/build_logs/${PREDICTOR}_build.txt"
FOUR_CORE_RESULT="$FOUR_CORE_DIR/simulator_output/${PREDICTOR}__mix${MIX_NUMBER}.txt"
FOUR_CORE_TIMING="$FOUR_CORE_DIR/timing/${PREDICTOR}__mix${MIX_NUMBER}.txt"

echo
echo "============================================================"
echo "Building Modified Bullseye: four cores"
echo "============================================================"

./build_champsim.sh "$PREDICTOR" no no no no lru 4 \
    |& tee "$FOUR_CORE_BUILD_LOG"

[[ -x "bin/$FOUR_CORE_BINARY" ]] \
    || fail "Expected binary not found: bin/$FOUR_CORE_BINARY"

echo
echo "Selected four-core trace mix:"
for core in "${!FOUR_CORE_TRACES[@]}"; do
    echo "  Core $core: ${FOUR_CORE_TRACES[$core]}"
done

marker=$(mktemp)
touch "$marker"

echo
echo "------------------------------------------------------------"
echo "Running Modified Bullseye four-core mix $MIX_NUMBER"
echo "------------------------------------------------------------"

/usr/bin/time -p \
    -o "$FOUR_CORE_TIMING" \
    ./run_4core.sh \
    "$FOUR_CORE_BINARY" \
    "$WARMUP_MILLIONS" \
    "$SIMULATION_MILLIONS" \
    "$MIX_NUMBER" \
    "${FOUR_CORE_TRACES[0]}" \
    "${FOUR_CORE_TRACES[1]}" \
    "${FOUR_CORE_TRACES[2]}" \
    "${FOUR_CORE_TRACES[3]}"

generated_result=$(
    find_completed_result "$marker" "$FOUR_CORE_BINARY"
) || {
    rm -f "$marker"
    fail "Could not locate completed four-core result"
}

rm -f "$marker"

cp "$generated_result" "$FOUR_CORE_RESULT"

[[ "$(grep -c "Branch Prediction Accuracy" "$FOUR_CORE_RESULT")" -eq 4 ]] \
    || fail "Expected four branch-accuracy lines in $FOUR_CORE_RESULT"

[[ "$(grep -c "Average Predictor Lookup Latency" "$FOUR_CORE_RESULT")" -eq 4 ]] \
    || fail "Expected four latency lines in $FOUR_CORE_RESULT"

echo \
"$PREDICTOR,$MIX_NUMBER,${FOUR_CORE_TRACES[0]},${FOUR_CORE_TRACES[1]},${FOUR_CORE_TRACES[2]},${FOUR_CORE_TRACES[3]},$FOUR_CORE_BINARY,$FOUR_CORE_RESULT,$FOUR_CORE_TIMING" \
    >> "$FOUR_CORE_MANIFEST"

echo "Saved result: $FOUR_CORE_RESULT"
echo "Saved timing: $FOUR_CORE_TIMING"

echo
echo "============================================================"
echo "Modified Bullseye experiments completed successfully."
echo "Single-core manifest: $SINGLE_MANIFEST"
echo "Four-core manifest:   $FOUR_CORE_MANIFEST"
echo "============================================================"
