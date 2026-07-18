#!/usr/bin/env bash

set -euo pipefail

PREDICTOR="hashed_perceptron"
POLICY="hcit"
WARMUP_MILLIONS=1
SIMULATION_MILLIONS=1
TRACE="401.bzip2-277B.champsimtrace.xz"
SELECTION_FILE="random_trace_output/selected_4core_traces.txt"

OUT_DIR="results/raw/task2/hcit_smoke"
mkdir -p \
    "$OUT_DIR/build_logs" \
    "$OUT_DIR/timing" \
    "$OUT_DIR/simulator_output"

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

[[ -f "replacement/hcit.llc_repl" ]] \
    || fail "Missing replacement/hcit.llc_repl"

[[ -f "dpc3_traces/$TRACE" ]] \
    || fail "Missing dpc3_traces/$TRACE"

[[ -f "$SELECTION_FILE" ]] \
    || fail "Missing $SELECTION_FILE"

grep -q '^#define LLC_SET 4096' inc/cache.h \
    || fail "Expected baseline LLC_SET=4096"

grep -q '^#define LLC_WAY 16' inc/cache.h \
    || fail "Expected baseline LLC_WAY=16"

mapfile -t FOUR_TRACES < <(
    awk -F': ' '/^Core [0-3]: / { print $2 }' "$SELECTION_FILE"
)

[[ "${#FOUR_TRACES[@]}" -eq 4 ]] \
    || fail "Expected four selected traces"

for selected_trace in "${FOUR_TRACES[@]}"; do
    [[ -f "dpc3_traces/$selected_trace" ]] \
        || fail "Missing dpc3_traces/$selected_trace"
done

echo
echo "============================================================"
echo "Building and running HCIT single-core smoke test"
echo "============================================================"

./build_champsim.sh \
    "$PREDICTOR" no no no no "$POLICY" 1 \
    |& tee "$OUT_DIR/build_logs/hcit_1core_build.txt"

SINGLE_BINARY="${PREDICTOR}-no-no-no-no-${POLICY}-1core"

[[ -x "bin/$SINGLE_BINARY" ]] \
    || fail "Missing bin/$SINGLE_BINARY"

single_marker=$(mktemp)
touch "$single_marker"

/usr/bin/time -p \
    -o "$OUT_DIR/timing/hcit_1core_time.txt" \
    ./run_champsim.sh \
    "$SINGLE_BINARY" \
    "$WARMUP_MILLIONS" \
    "$SIMULATION_MILLIONS" \
    "$TRACE"

single_generated=$(
    find_completed_result "$single_marker" "$SINGLE_BINARY"
) || {
    rm -f "$single_marker"
    fail "Could not locate completed HCIT single-core result"
}

rm -f "$single_marker"

SINGLE_RESULT="$OUT_DIR/simulator_output/hcit_1core_result.txt"
cp "$single_generated" "$SINGLE_RESULT"

grep -q "ChampSim completed all CPUs" "$SINGLE_RESULT" \
    || fail "HCIT single-core completion marker missing"

grep -q "HCIT Replacement Statistics" "$SINGLE_RESULT" \
    || fail "HCIT single-core policy statistics missing"

grep -q "LLC TOTAL" "$SINGLE_RESULT" \
    || fail "HCIT single-core LLC statistics missing"

echo
echo "============================================================"
echo "Building and running HCIT four-core smoke test"
echo "============================================================"

./build_champsim.sh \
    "$PREDICTOR" no no no no "$POLICY" 4 \
    |& tee "$OUT_DIR/build_logs/hcit_4core_build.txt"

FOUR_BINARY="${PREDICTOR}-no-no-no-no-${POLICY}-4core"

[[ -x "bin/$FOUR_BINARY" ]] \
    || fail "Missing bin/$FOUR_BINARY"

four_marker=$(mktemp)
touch "$four_marker"

/usr/bin/time -p \
    -o "$OUT_DIR/timing/hcit_4core_time.txt" \
    ./run_4core.sh \
    "$FOUR_BINARY" \
    "$WARMUP_MILLIONS" \
    "$SIMULATION_MILLIONS" \
    1 \
    "${FOUR_TRACES[0]}" \
    "${FOUR_TRACES[1]}" \
    "${FOUR_TRACES[2]}" \
    "${FOUR_TRACES[3]}"

four_generated=$(
    find_completed_result "$four_marker" "$FOUR_BINARY"
) || {
    rm -f "$four_marker"
    fail "Could not locate completed HCIT four-core result"
}

rm -f "$four_marker"

FOUR_RESULT="$OUT_DIR/simulator_output/hcit_4core_result.txt"
cp "$four_generated" "$FOUR_RESULT"

grep -q "ChampSim completed all CPUs" "$FOUR_RESULT" \
    || fail "HCIT four-core completion marker missing"

grep -q "HCIT Replacement Statistics" "$FOUR_RESULT" \
    || fail "HCIT four-core policy statistics missing"

grep -q "LLC TOTAL" "$FOUR_RESULT" \
    || fail "HCIT four-core LLC statistics missing"

echo
echo "============================================================"
echo "Adaptive HCIT smoke tests completed successfully."
echo "Single result: $SINGLE_RESULT"
echo "Four result:   $FOUR_RESULT"
echo "============================================================"
