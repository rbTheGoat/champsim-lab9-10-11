#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10
PREDICTOR="hashed_perceptron"
LLC_SIZE_MB=4
LLC_ASSOCIATIVITY=8
LLC_SETS=8192
BLOCK_SIZE_BYTES=64
MIX_NUMBER=1

SINGLE_TRACES=(
    "401.bzip2-277B.champsimtrace.xz"
    "403.gcc-16B.champsimtrace.xz"
    "605.mcf_s-665B.champsimtrace.xz"
    "619.lbm_s-3766B.champsimtrace.xz"
)

SELECTION_FILE="random_trace_output/selected_4core_traces.txt"
CACHE_HEADER="inc/cache.h"

BASE_DIR="results/raw/task2/llc_associativity/8way"
SINGLE_DIR="$BASE_DIR/single"
FOUR_CORE_DIR="$BASE_DIR/four_core"
CONFIG_DIR="configs/task2/llc_associativity"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

get_define() {
    local macro="$1"

    awk -v macro="$macro" \
        '$1 == "#define" && $2 == macro { print $3; exit }' \
        "$CACHE_HEADER"
}

set_define() {
    local macro="$1"
    local value="$2"

    python3 - "$CACHE_HEADER" "$macro" "$value" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
macro = sys.argv[2]
value = sys.argv[3]

text = path.read_text(encoding="utf-8")
pattern = re.compile(
    rf"(?m)^(\s*#define\s+{re.escape(macro)}\s+)\S+(\s*(?://.*)?)$"
)

updated, count = pattern.subn(
    lambda match: f"{match.group(1)}{value}{match.group(2)}",
    text,
)

if count != 1:
    raise SystemExit(
        f"Expected exactly one definition of {macro} in {path}, found {count}"
    )

path.write_text(updated, encoding="utf-8")
PY
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

validate_result() {
    local file="$1"
    local expected_cpus="$2"

    grep -q "ChampSim completed all CPUs" "$file" \
        || fail "Completion marker missing from $file"

    [[ "$(grep -c "cumulative IPC" "$file")" -ge "$expected_cpus" ]] \
        || fail "Expected IPC output for $expected_cpus CPU(s) in $file"

    grep -q "LLC TOTAL" "$file" \
        || fail "LLC statistics missing from $file"
}

# ---------------------------------------------------------------------------
# Validate baseline configuration and inputs
# ---------------------------------------------------------------------------

[[ -f "$CACHE_HEADER" ]] \
    || fail "Cache header not found: $CACHE_HEADER"

[[ "$(get_define L1I_SET)" == "64" ]] \
    || fail "L1I_SET must be 64"

[[ "$(get_define L1I_WAY)" == "8" ]] \
    || fail "L1I_WAY must be 8"

[[ "$(get_define L1D_SET)" == "64" ]] \
    || fail "L1D_SET must be 64"

[[ "$(get_define L1D_WAY)" == "8" ]] \
    || fail "L1D_WAY must be 8"

[[ "$(get_define L2C_SET)" == "512" ]] \
    || fail "L2C_SET must be 512"

[[ "$(get_define L2C_WAY)" == "8" ]] \
    || fail "L2C_WAY must be 8"

[[ "$(get_define LLC_SET)" == "4096" ]] \
    || fail "Expected restored 4 MB, 16-way baseline LLC_SET=4096"

[[ "$(get_define LLC_WAY)" == "16" ]] \
    || fail "Expected restored baseline LLC_WAY=16"

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

for trace in "${FOUR_CORE_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing four-core trace: dpc3_traces/$trace"
done

# ---------------------------------------------------------------------------
# Preserve and restore cache.h
# ---------------------------------------------------------------------------

CACHE_BACKUP=$(mktemp)
cp "$CACHE_HEADER" "$CACHE_BACKUP"

cleanup() {
    if [[ -f "$CACHE_BACKUP" ]]; then
        cp "$CACHE_BACKUP" "$CACHE_HEADER"
        rm -f "$CACHE_BACKUP"
    fi
}

trap cleanup EXIT INT TERM

# 4 MB = 8192 sets × 8 ways × 64 B.
set_define LLC_SET "$LLC_SETS"
set_define LLC_WAY "$LLC_ASSOCIATIVITY"

[[ "$(get_define LLC_SET)" == "$LLC_SETS" ]] \
    || fail "Failed to set LLC_SET=$LLC_SETS"

[[ "$(get_define LLC_WAY)" == "$LLC_ASSOCIATIVITY" ]] \
    || fail "Failed to set LLC_WAY=$LLC_ASSOCIATIVITY"

mkdir -p \
    "$SINGLE_DIR/build_logs" \
    "$SINGLE_DIR/timing" \
    "$SINGLE_DIR/simulator_output" \
    "$FOUR_CORE_DIR/build_logs" \
    "$FOUR_CORE_DIR/timing" \
    "$FOUR_CORE_DIR/simulator_output" \
    "$CONFIG_DIR"

SINGLE_MANIFEST="$SINGLE_DIR/run_manifest.csv"
FOUR_CORE_MANIFEST="$FOUR_CORE_DIR/run_manifest.csv"

echo \
"predictor,llc_size_mb,llc_sets,llc_associativity,block_size_bytes,trace,binary,result_file,timing_file" \
    > "$SINGLE_MANIFEST"

echo \
"predictor,llc_size_mb,llc_sets,llc_associativity,block_size_bytes,mix_number,core0_trace,core1_trace,core2_trace,core3_trace,binary,result_file,timing_file" \
    > "$FOUR_CORE_MANIFEST"

cat > "$CONFIG_DIR/llc_4mb_8way_single.txt" <<EOF
experiment=Task 2 LLC associativity study
core_mode=single_core
branch_predictor=$PREDICTOR
l1i_size_kb=32
l1i_associativity=8
l1d_size_kb=32
l1d_associativity=8
l2_size_kb=256
l2_associativity=8
llc_size_mb=$LLC_SIZE_MB
llc_sets=$LLC_SETS
llc_associativity=$LLC_ASSOCIATIVITY
block_size_bytes=$BLOCK_SIZE_BYTES
l1_replacement_policy=lru
l2_replacement_policy=lru
llc_replacement_policy=lru
warmup_instructions_millions=$WARMUP_MILLIONS
simulation_instructions_millions=$SIMULATION_MILLIONS
EOF

cp \
    "$CONFIG_DIR/llc_4mb_8way_single.txt" \
    "$CONFIG_DIR/llc_4mb_8way_four_core.txt"

sed -i \
    's/core_mode=single_core/core_mode=four_core_shared_llc/' \
    "$CONFIG_DIR/llc_4mb_8way_four_core.txt"

echo
echo "============================================================"
echo "Task 2 LLC associativity experiment"
echo "LLC: 4 MB, 8192 sets, 8-way, 64-byte blocks"
echo "Predictor: hashed_perceptron"
echo "Replacement: LRU"
echo "============================================================"

# ---------------------------------------------------------------------------
# Single-core runs
# ---------------------------------------------------------------------------

SINGLE_BINARY="${PREDICTOR}-no-no-no-no-lru-1core"
SINGLE_BUILD_LOG="$SINGLE_DIR/build_logs/llc_4mb_8way_build.txt"

./build_champsim.sh "$PREDICTOR" no no no no lru 1 \
    |& tee "$SINGLE_BUILD_LOG"

[[ -x "bin/$SINGLE_BINARY" ]] \
    || fail "Single-core binary missing: bin/$SINGLE_BINARY"

for trace in "${SINGLE_TRACES[@]}"; do
    trace_tag="${trace%.champsimtrace.xz}"
    result_copy="$SINGLE_DIR/simulator_output/llc_4mb_8way__${trace_tag}.txt"
    timing_file="$SINGLE_DIR/timing/llc_4mb_8way__${trace_tag}.txt"

    marker=$(mktemp)
    touch "$marker"

    echo
    echo "------------------------------------------------------------"
    echo "Single core | LLC 4 MB, 8-way | $trace"
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

    validate_result "$result_copy" 1

    echo \
"$PREDICTOR,$LLC_SIZE_MB,$LLC_SETS,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$trace,$SINGLE_BINARY,$result_copy,$timing_file" \
        >> "$SINGLE_MANIFEST"

    echo "Saved result: $result_copy"
    echo "Saved timing: $timing_file"
done

# ---------------------------------------------------------------------------
# Four-core run
# ---------------------------------------------------------------------------

FOUR_BINARY="${PREDICTOR}-no-no-no-no-lru-4core"
FOUR_BUILD_LOG="$FOUR_CORE_DIR/build_logs/llc_4mb_8way_build.txt"
FOUR_RESULT="$FOUR_CORE_DIR/simulator_output/llc_4mb_8way__mix${MIX_NUMBER}.txt"
FOUR_TIMING="$FOUR_CORE_DIR/timing/llc_4mb_8way__mix${MIX_NUMBER}.txt"

./build_champsim.sh "$PREDICTOR" no no no no lru 4 \
    |& tee "$FOUR_BUILD_LOG"

[[ -x "bin/$FOUR_BINARY" ]] \
    || fail "Four-core binary missing: bin/$FOUR_BINARY"

marker=$(mktemp)
touch "$marker"

echo
echo "------------------------------------------------------------"
echo "Four core | Shared LLC 4 MB, 8-way | Mix $MIX_NUMBER"
echo "------------------------------------------------------------"

/usr/bin/time -p \
    -o "$FOUR_TIMING" \
    ./run_4core.sh \
    "$FOUR_BINARY" \
    "$WARMUP_MILLIONS" \
    "$SIMULATION_MILLIONS" \
    "$MIX_NUMBER" \
    "${FOUR_CORE_TRACES[0]}" \
    "${FOUR_CORE_TRACES[1]}" \
    "${FOUR_CORE_TRACES[2]}" \
    "${FOUR_CORE_TRACES[3]}"

generated_result=$(
    find_completed_result "$marker" "$FOUR_BINARY"
) || {
    rm -f "$marker"
    fail "Could not locate completed four-core result"
}

rm -f "$marker"
cp "$generated_result" "$FOUR_RESULT"

validate_result "$FOUR_RESULT" 4

echo \
"$PREDICTOR,$LLC_SIZE_MB,$LLC_SETS,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$MIX_NUMBER,${FOUR_CORE_TRACES[0]},${FOUR_CORE_TRACES[1]},${FOUR_CORE_TRACES[2]},${FOUR_CORE_TRACES[3]},$FOUR_BINARY,$FOUR_RESULT,$FOUR_TIMING" \
    >> "$FOUR_CORE_MANIFEST"

echo "Saved result: $FOUR_RESULT"
echo "Saved timing: $FOUR_TIMING"

echo
echo "============================================================"
echo "Task 2 8-way LLC associativity experiments completed successfully."
echo "Single-core runs: 4"
echo "Four-core runs:  1"
echo "Original 4 MB, 16-way cache configuration restored automatically."
echo "============================================================"
