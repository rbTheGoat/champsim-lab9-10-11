#!/usr/bin/env bash

set -euo pipefail

PREDICTOR="hashed_perceptron"
TRACE="401.bzip2-277B.champsimtrace.xz"
WARMUP_MILLIONS=1
SIMULATION_MILLIONS=1

OUT_DIR="results/raw/task2/replacement_policy_smoke"
mkdir -p "$OUT_DIR/build_logs" "$OUT_DIR/timing" "$OUT_DIR/simulator_output"

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
            -path "./results_*M/*" \
            -name "*${expected_binary}*" \
            -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | cut -d' ' -f2-
    )

    return 1
}

for policy in mru random; do
    [[ -f "replacement/${policy}.llc_repl" ]] \
        || fail "Missing replacement/${policy}.llc_repl"

    echo
    echo "============================================================"
    echo "Building $policy replacement: single core"
    echo "============================================================"

    ./build_champsim.sh \
        "$PREDICTOR" no no no no "$policy" 1 \
        |& tee "$OUT_DIR/build_logs/${policy}_1core_build.txt"

    binary="${PREDICTOR}-no-no-no-no-${policy}-1core"

    [[ -x "bin/$binary" ]] \
        || fail "Missing binary: bin/$binary"

    marker=$(mktemp)
    touch "$marker"

    /usr/bin/time -p \
        -o "$OUT_DIR/timing/${policy}_1core_time.txt" \
        ./run_champsim.sh \
        "$binary" \
        "$WARMUP_MILLIONS" \
        "$SIMULATION_MILLIONS" \
        "$TRACE"

    generated_result=$(
        find_completed_result "$marker" "$binary"
    ) || {
        rm -f "$marker"
        fail "Could not locate completed result for $policy"
    }

    rm -f "$marker"

    result_copy="$OUT_DIR/simulator_output/${policy}_1core_result.txt"
    cp "$generated_result" "$result_copy"

    grep -q "ChampSim completed all CPUs" "$result_copy" \
        || fail "Completion marker missing for $policy"

    grep -q "LLC TOTAL" "$result_copy" \
        || fail "LLC statistics missing for $policy"

    if [[ "$policy" == "mru" ]]; then
        grep -q "MRU Replacement Statistics" "$result_copy" \
            || fail "MRU final statistics missing"
    else
        grep -q "Random Replacement Statistics" "$result_copy" \
            || fail "Random final statistics missing"
    fi

    echo
    echo "============================================================"
    echo "Building $policy replacement: four cores"
    echo "============================================================"

    ./build_champsim.sh \
        "$PREDICTOR" no no no no "$policy" 4 \
        |& tee "$OUT_DIR/build_logs/${policy}_4core_build.txt"

    four_binary="${PREDICTOR}-no-no-no-no-${policy}-4core"

    [[ -x "bin/$four_binary" ]] \
        || fail "Missing binary: bin/$four_binary"

    echo "$policy smoke test passed."
done

echo
echo "============================================================"
echo "MRU and Random replacement smoke tests completed successfully."
echo "============================================================"
