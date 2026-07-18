#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10
PREDICTOR="hashed_perceptron"
LLC_ASSOCIATIVITY=16
BLOCK_SIZE_BYTES=64
MIX_NUMBER=1

SINGLE_TRACES=(
    "401.bzip2-277B.champsimtrace.xz"
    "403.gcc-16B.champsimtrace.xz"
    "605.mcf_s-665B.champsimtrace.xz"
    "619.lbm_s-3766B.champsimtrace.xz"
)

LLC_SIZES_MB=(1 2 4 8)

SELECTION_FILE="random_trace_output/selected_4core_traces.txt"
CACHE_HEADER="inc/cache.h"

BASE_DIR="results/raw/task2/llc_size"
SINGLE_DIR="$BASE_DIR/single"
FOUR_CORE_DIR="$BASE_DIR/four_core"
CONFIG_DIR="configs/task2/llc_size"

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

set_cache_define() {
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

new_text, count = pattern.subn(
    lambda match: f"{match.group(1)}{value}{match.group(2)}",
    text,
)

if count != 1:
    raise SystemExit(
        f"Expected exactly one definition of {macro} in {path}, found {count}"
    )

path.write_text(new_text, encoding="utf-8")
PY
}

get_cache_define() {
    local macro="$1"

    awk -v macro="$macro" \
        '$1 == "#define" && $2 == macro { print $3; exit }' \
        "$CACHE_HEADER"
}

write_configuration_record() {
    local size_mb="$1"
    local sets="$2"
    local core_mode="$3"
    local output_file="$4"

    cat > "$output_file" <<EOF
experiment=Task 2 LLC size study
core_mode=$core_mode
branch_predictor=$PREDICTOR
l1i_size_kb=32
l1i_associativity=8
l1d_size_kb=32
l1d_associativity=8
l2_size_kb=256
l2_associativity=8
llc_size_mb=$size_mb
llc_sets=$sets
llc_associativity=$LLC_ASSOCIATIVITY
block_size_bytes=$BLOCK_SIZE_BYTES
l1_replacement_policy=lru
l2_replacement_policy=lru
llc_replacement_policy=lru
warmup_instructions_millions=$WARMUP_MILLIONS
simulation_instructions_millions=$SIMULATION_MILLIONS
EOF
}

validate_fixed_configuration() {
    [[ "$(get_cache_define L1I_SET)" == "64" ]] \
        || fail "L1I_SET must be 64"

    [[ "$(get_cache_define L1I_WAY)" == "8" ]] \
        || fail "L1I_WAY must be 8"

    [[ "$(get_cache_define L1D_SET)" == "64" ]] \
        || fail "L1D_SET must be 64"

    [[ "$(get_cache_define L1D_WAY)" == "8" ]] \
        || fail "L1D_WAY must be 8"

    [[ "$(get_cache_define L2C_SET)" == "512" ]] \
        || fail "L2C_SET must be 512"

    [[ "$(get_cache_define L2C_WAY)" == "8" ]] \
        || fail "L2C_WAY must be 8"

    # BLOCK_SIZE macros are defined outside inc/cache.h in this
    # ChampSim version. Search all headers for LOG2_BLOCK_SIZE.
    local log2_block_size

    log2_block_size=$(
        grep -RhsE             '^[[:space:]]*#define[[:space:]]+LOG2_BLOCK_SIZE[[:space:]]+'             inc 2>/dev/null         | awk '{gsub(/[()]/, "", $3); print $3; exit}'
    )

    [[ -n "$log2_block_size" ]] \
        || fail "Could not locate LOG2_BLOCK_SIZE in inc/"

    [[ "$log2_block_size" == "6" ]] \
        || fail "LOG2_BLOCK_SIZE is $log2_block_size, expected 6 for 64-byte blocks"
}

validate_result_file() {
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
# Validate project inputs
# ---------------------------------------------------------------------------

[[ -f "$CACHE_HEADER" ]] \
    || fail "Cache header not found: $CACHE_HEADER"

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

validate_fixed_configuration

# ---------------------------------------------------------------------------
# Preserve the exact original configuration and restore it on every exit
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

echo "Task 2 LLC size study"
echo "Predictor held constant: $PREDICTOR"
echo "LLC replacement held constant: LRU"
echo "LLC associativity held constant: ${LLC_ASSOCIATIVITY}-way"
echo

# ---------------------------------------------------------------------------
# Run each LLC size
#
# LLC sets = size_bytes / (block_size * associativity)
# 1 MB -> 1024 sets
# 2 MB -> 2048 sets
# 4 MB -> 4096 sets
# 8 MB -> 8192 sets
# ---------------------------------------------------------------------------

for size_mb in "${LLC_SIZES_MB[@]}"; do
    llc_sets=$((size_mb * 1024 * 1024 / BLOCK_SIZE_BYTES / LLC_ASSOCIATIVITY))

    set_cache_define LLC_SET "$llc_sets"
    set_cache_define LLC_WAY "$LLC_ASSOCIATIVITY"

    [[ "$(get_cache_define LLC_SET)" == "$llc_sets" ]] \
        || fail "Failed to set LLC_SET=$llc_sets"

    [[ "$(get_cache_define LLC_WAY)" == "$LLC_ASSOCIATIVITY" ]] \
        || fail "Failed to set LLC_WAY=$LLC_ASSOCIATIVITY"

    write_configuration_record \
        "$size_mb" \
        "$llc_sets" \
        "single_core" \
        "$CONFIG_DIR/llc_${size_mb}mb_16way_single.txt"

    write_configuration_record \
        "$size_mb" \
        "$llc_sets" \
        "four_core_shared_llc" \
        "$CONFIG_DIR/llc_${size_mb}mb_16way_four_core.txt"

    echo
    echo "============================================================"
    echo "LLC size: ${size_mb} MB (${llc_sets} sets, 16-way)"
    echo "Building single-core binary"
    echo "============================================================"

    single_binary="${PREDICTOR}-no-no-no-no-lru-1core"
    single_build_log="$SINGLE_DIR/build_logs/llc_${size_mb}mb_build.txt"

    ./build_champsim.sh "$PREDICTOR" no no no no lru 1 \
        |& tee "$single_build_log"

    [[ -x "bin/$single_binary" ]] \
        || fail "Single-core binary missing: bin/$single_binary"

    for trace in "${SINGLE_TRACES[@]}"; do
        trace_tag="${trace%.champsimtrace.xz}"

        result_copy="$SINGLE_DIR/simulator_output/llc_${size_mb}mb__${trace_tag}.txt"
        timing_file="$SINGLE_DIR/timing/llc_${size_mb}mb__${trace_tag}.txt"

        marker=$(mktemp)
        touch "$marker"

        echo
        echo "------------------------------------------------------------"
        echo "Single core | LLC ${size_mb} MB | $trace"
        echo "------------------------------------------------------------"

        /usr/bin/time -p \
            -o "$timing_file" \
            ./run_champsim.sh \
            "$single_binary" \
            "$WARMUP_MILLIONS" \
            "$SIMULATION_MILLIONS" \
            "$trace"

        generated_result=$(
            find_completed_result "$marker" "$single_binary"
        ) || {
            rm -f "$marker"
            fail "Could not locate completed result for LLC ${size_mb} MB and $trace"
        }

        rm -f "$marker"
        cp "$generated_result" "$result_copy"

        validate_result_file "$result_copy" 1

        echo \
"$PREDICTOR,$size_mb,$llc_sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$trace,$single_binary,$result_copy,$timing_file" \
            >> "$SINGLE_MANIFEST"

        echo "Saved result: $result_copy"
        echo "Saved timing: $timing_file"
    done

    echo
    echo "============================================================"
    echo "LLC size: ${size_mb} MB (${llc_sets} sets, 16-way)"
    echo "Building four-core binary"
    echo "============================================================"

    four_binary="${PREDICTOR}-no-no-no-no-lru-4core"
    four_build_log="$FOUR_CORE_DIR/build_logs/llc_${size_mb}mb_build.txt"
    four_result="$FOUR_CORE_DIR/simulator_output/llc_${size_mb}mb__mix${MIX_NUMBER}.txt"
    four_timing="$FOUR_CORE_DIR/timing/llc_${size_mb}mb__mix${MIX_NUMBER}.txt"

    ./build_champsim.sh "$PREDICTOR" no no no no lru 4 \
        |& tee "$four_build_log"

    [[ -x "bin/$four_binary" ]] \
        || fail "Four-core binary missing: bin/$four_binary"

    marker=$(mktemp)
    touch "$marker"

    echo
    echo "------------------------------------------------------------"
    echo "Four core | Shared LLC ${size_mb} MB | Mix $MIX_NUMBER"
    echo "------------------------------------------------------------"

    /usr/bin/time -p \
        -o "$four_timing" \
        ./run_4core.sh \
        "$four_binary" \
        "$WARMUP_MILLIONS" \
        "$SIMULATION_MILLIONS" \
        "$MIX_NUMBER" \
        "${FOUR_CORE_TRACES[0]}" \
        "${FOUR_CORE_TRACES[1]}" \
        "${FOUR_CORE_TRACES[2]}" \
        "${FOUR_CORE_TRACES[3]}"

    generated_result=$(
        find_completed_result "$marker" "$four_binary"
    ) || {
        rm -f "$marker"
        fail "Could not locate completed four-core result for LLC ${size_mb} MB"
    }

    rm -f "$marker"
    cp "$generated_result" "$four_result"

    validate_result_file "$four_result" 4

    echo \
"$PREDICTOR,$size_mb,$llc_sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$MIX_NUMBER,${FOUR_CORE_TRACES[0]},${FOUR_CORE_TRACES[1]},${FOUR_CORE_TRACES[2]},${FOUR_CORE_TRACES[3]},$four_binary,$four_result,$four_timing" \
        >> "$FOUR_CORE_MANIFEST"

    echo "Saved result: $four_result"
    echo "Saved timing: $four_timing"
done

echo
echo "============================================================"
echo "Task 2 LLC size experiments completed successfully."
echo "Single-core runs: 16"
echo "Four-core runs:  4"
echo "Original cache configuration restored automatically."
echo "Single-core manifest: $SINGLE_MANIFEST"
echo "Four-core manifest:   $FOUR_CORE_MANIFEST"
echo "============================================================"
