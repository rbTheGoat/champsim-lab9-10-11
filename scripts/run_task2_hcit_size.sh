#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10

PREDICTOR="hashed_perceptron"
POLICY="hcit"
LLC_ASSOCIATIVITY=16
BLOCK_SIZE_BYTES=64
MIX_NUMBER=1

SIZES_MB=(1 2 4 8)

declare -A LLC_SETS_BY_SIZE=(
    [1]=1024
    [2]=2048
    [4]=4096
    [8]=8192
)

SINGLE_TRACES=(
    "401.bzip2-277B.champsimtrace.xz"
    "403.gcc-16B.champsimtrace.xz"
    "605.mcf_s-665B.champsimtrace.xz"
    "619.lbm_s-3766B.champsimtrace.xz"
)

SELECTION_FILE="random_trace_output/selected_4core_traces.txt"
CACHE_HEADER="inc/cache.h"

BASE_DIR="results/raw/task2/hcit_size"
SINGLE_DIR="$BASE_DIR/single"
FOUR_DIR="$BASE_DIR/four_core"
CONFIG_DIR="configs/task2/hcit_size"

SINGLE_MANIFEST="$SINGLE_DIR/run_manifest.csv"
FOUR_MANIFEST="$FOUR_DIR/run_manifest.csv"

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

result_is_complete() {
    local result_file="$1"
    local expected_cpus="$2"

    [[ -f "$result_file" ]] \
        || return 1

    grep -q "ChampSim completed all CPUs" "$result_file" \
        || return 1

    [[ "$(grep -c "cumulative IPC" "$result_file")" -ge "$expected_cpus" ]] \
        || return 1

    grep -q "LLC TOTAL" "$result_file" \
        || return 1

    grep -q "HCIT Replacement Statistics" "$result_file" \
        || return 1

    return 0
}

timing_is_complete() {
    local timing_file="$1"

    [[ -f "$timing_file" ]] \
        || return 1

    grep -q '^real ' "$timing_file" \
        && grep -q '^user ' "$timing_file" \
        && grep -q '^sys ' "$timing_file"
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

write_config() {
    local size_mb="$1"
    local sets="$2"
    local core_mode="$3"
    local config_file="$4"

    cat > "$config_file" <<EOF
experiment=Task 2 adaptive HCIT replacement policy
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
llc_replacement_policy=$POLICY
warmup_instructions_millions=$WARMUP_MILLIONS
simulation_instructions_millions=$SIMULATION_MILLIONS
hcit_entries=2048
hcit_candidate_filter_entries=4096
hcit_initial_threshold=6
hcit_threshold_min=3
hcit_threshold_max=12
hcit_epoch_llc_updates=16384
EOF
}

# ---------------------------------------------------------------------------
# Validate baseline and inputs
# ---------------------------------------------------------------------------

[[ -f "$CACHE_HEADER" ]] \
    || fail "Missing $CACHE_HEADER"

[[ -f "replacement/hcit.llc_repl" ]] \
    || fail "Missing replacement/hcit.llc_repl"

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
    || fail "Expected restored baseline LLC_SET=4096"

[[ "$(get_define LLC_WAY)" == "16" ]] \
    || fail "Expected restored baseline LLC_WAY=16"

for trace in "${SINGLE_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing dpc3_traces/$trace"
done

[[ -f "$SELECTION_FILE" ]] \
    || fail "Missing $SELECTION_FILE"

mapfile -t FOUR_TRACES < <(
    awk -F': ' '/^Core [0-3]: / { print $2 }' "$SELECTION_FILE"
)

[[ "${#FOUR_TRACES[@]}" -eq 4 ]] \
    || fail "Expected four selected traces, found ${#FOUR_TRACES[@]}"

for trace in "${FOUR_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing dpc3_traces/$trace"
done

# ---------------------------------------------------------------------------
# Preserve cache.h and prepare directories
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
    "$FOUR_DIR/build_logs" \
    "$FOUR_DIR/timing" \
    "$FOUR_DIR/simulator_output" \
    "$CONFIG_DIR"

echo \
"predictor,replacement_policy,llc_size_mb,llc_sets,llc_associativity,block_size_bytes,trace,binary,result_file,timing_file" \
    > "$SINGLE_MANIFEST"

echo \
"predictor,replacement_policy,llc_size_mb,llc_sets,llc_associativity,block_size_bytes,mix_number,core0_trace,core1_trace,core2_trace,core3_trace,binary,result_file,timing_file" \
    > "$FOUR_MANIFEST"

completed_single=0
skipped_single=0
completed_four=0
skipped_four=0

echo
echo "============================================================"
echo "Task 2 adaptive HCIT × LLC-size experiment"
echo "Sizes: 1 MB, 2 MB, 4 MB, 8 MB"
echo "New simulations: 16 single-core + 4 four-core"
echo "The script is resume-safe."
echo "============================================================"

for size_mb in "${SIZES_MB[@]}"; do
    sets="${LLC_SETS_BY_SIZE[$size_mb]}"

    set_define LLC_SET "$sets"
    set_define LLC_WAY "$LLC_ASSOCIATIVITY"

    [[ "$(get_define LLC_SET)" == "$sets" ]] \
        || fail "Failed to set LLC_SET=$sets"

    [[ "$(get_define LLC_WAY)" == "$LLC_ASSOCIATIVITY" ]] \
        || fail "Failed to set LLC_WAY=$LLC_ASSOCIATIVITY"

    single_config="$CONFIG_DIR/hcit__llc_${size_mb}mb__single.txt"
    four_config="$CONFIG_DIR/hcit__llc_${size_mb}mb__four_core.txt"

    write_config "$size_mb" "$sets" "single_core" "$single_config"
    write_config "$size_mb" "$sets" "four_core_shared_llc" "$four_config"

    # -----------------------------------------------------------------------
    # Single-core build and four traces
    # -----------------------------------------------------------------------

    single_binary="${PREDICTOR}-no-no-no-no-${POLICY}-1core"
    single_build_log="$SINGLE_DIR/build_logs/hcit__llc_${size_mb}mb.txt"

    echo
    echo "============================================================"
    echo "BUILD SINGLE | HCIT | LLC=${size_mb}MB"
    echo "============================================================"

    ./build_champsim.sh \
        "$PREDICTOR" no no no no "$POLICY" 1 \
        |& tee "$single_build_log"

    [[ -x "bin/$single_binary" ]] \
        || fail "Missing binary bin/$single_binary"

    for trace in "${SINGLE_TRACES[@]}"; do
        trace_tag="${trace%.champsimtrace.xz}"
        result_copy="$SINGLE_DIR/simulator_output/hcit__llc_${size_mb}mb__${trace_tag}.txt"
        timing_file="$SINGLE_DIR/timing/hcit__llc_${size_mb}mb__${trace_tag}.txt"

        if result_is_complete "$result_copy" 1 \
            && timing_is_complete "$timing_file"; then
            echo "SKIP complete single run: ${size_mb}MB | $trace"
            skipped_single=$((skipped_single + 1))
        else
            rm -f "$result_copy" "$timing_file"

            marker=$(mktemp)
            touch "$marker"

            echo
            echo "RUN SINGLE | HCIT | LLC=${size_mb}MB | $trace"

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
                fail "Could not locate result for HCIT ${size_mb}MB $trace"
            }

            rm -f "$marker"
            cp "$generated_result" "$result_copy"

            result_is_complete "$result_copy" 1 \
                || fail "Incomplete result: $result_copy"

            timing_is_complete "$timing_file" \
                || fail "Incomplete timing: $timing_file"

            completed_single=$((completed_single + 1))
        fi

        echo \
"$PREDICTOR,$POLICY,$size_mb,$sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$trace,$single_binary,$result_copy,$timing_file" \
            >> "$SINGLE_MANIFEST"
    done

    # -----------------------------------------------------------------------
    # Four-core build and selected mix
    # -----------------------------------------------------------------------

    four_binary="${PREDICTOR}-no-no-no-no-${POLICY}-4core"
    four_build_log="$FOUR_DIR/build_logs/hcit__llc_${size_mb}mb.txt"
    four_result="$FOUR_DIR/simulator_output/hcit__llc_${size_mb}mb__mix${MIX_NUMBER}.txt"
    four_timing="$FOUR_DIR/timing/hcit__llc_${size_mb}mb__mix${MIX_NUMBER}.txt"

    echo
    echo "============================================================"
    echo "BUILD FOUR | HCIT | LLC=${size_mb}MB"
    echo "============================================================"

    ./build_champsim.sh \
        "$PREDICTOR" no no no no "$POLICY" 4 \
        |& tee "$four_build_log"

    [[ -x "bin/$four_binary" ]] \
        || fail "Missing binary bin/$four_binary"

    if result_is_complete "$four_result" 4 \
        && timing_is_complete "$four_timing"; then
        echo "SKIP complete four-core run: ${size_mb}MB"
        skipped_four=$((skipped_four + 1))
    else
        rm -f "$four_result" "$four_timing"

        marker=$(mktemp)
        touch "$marker"

        echo
        echo "RUN FOUR | HCIT | LLC=${size_mb}MB | mix=$MIX_NUMBER"

        /usr/bin/time -p \
            -o "$four_timing" \
            ./run_4core.sh \
            "$four_binary" \
            "$WARMUP_MILLIONS" \
            "$SIMULATION_MILLIONS" \
            "$MIX_NUMBER" \
            "${FOUR_TRACES[0]}" \
            "${FOUR_TRACES[1]}" \
            "${FOUR_TRACES[2]}" \
            "${FOUR_TRACES[3]}"

        generated_result=$(
            find_completed_result "$marker" "$four_binary"
        ) || {
            rm -f "$marker"
            fail "Could not locate four-core HCIT result for ${size_mb}MB"
        }

        rm -f "$marker"
        cp "$generated_result" "$four_result"

        result_is_complete "$four_result" 4 \
            || fail "Incomplete result: $four_result"

        timing_is_complete "$four_timing" \
            || fail "Incomplete timing: $four_timing"

        completed_four=$((completed_four + 1))
    fi

    echo \
"$PREDICTOR,$POLICY,$size_mb,$sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$MIX_NUMBER,${FOUR_TRACES[0]},${FOUR_TRACES[1]},${FOUR_TRACES[2]},${FOUR_TRACES[3]},$four_binary,$four_result,$four_timing" \
        >> "$FOUR_MANIFEST"
done

echo
echo "============================================================"
echo "Adaptive HCIT × LLC-size experiments completed."
echo "New single-core runs:      $completed_single"
echo "Skipped single-core runs:  $skipped_single"
echo "New four-core runs:        $completed_four"
echo "Skipped four-core runs:    $skipped_four"
echo "Single manifest rows:      $(($(wc -l < "$SINGLE_MANIFEST") - 1))"
echo "Four-core manifest rows:   $(($(wc -l < "$FOUR_MANIFEST") - 1))"
echo "Original cache.h restored automatically."
echo "============================================================"
