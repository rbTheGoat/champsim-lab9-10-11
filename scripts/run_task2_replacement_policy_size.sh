#!/usr/bin/env bash

set -euo pipefail

WARMUP_MILLIONS=1
SIMULATION_MILLIONS=10
PREDICTOR="hashed_perceptron"
LLC_ASSOCIATIVITY=16
BLOCK_SIZE_BYTES=64
MIX_NUMBER=1

# LRU is not rerun here. Its 1/2/4/8 MB results already exist from the
# Task 2 LLC-size experiment and will be merged during parsing.
POLICIES=(
    "srrip"
    "drrip"
    "ship"
    "mru"
    "random"
)

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

BASE_DIR="results/raw/task2/replacement_policy_size"
SINGLE_DIR="$BASE_DIR/single"
FOUR_DIR="$BASE_DIR/four_core"
CONFIG_DIR="configs/task2/replacement_policy_size"

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
        f"Expected one definition of {macro} in {path}, found {count}"
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

validate_baseline() {
    [[ -f "$CACHE_HEADER" ]] \
        || fail "Missing $CACHE_HEADER"

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

    for policy in "${POLICIES[@]}"; do
        [[ -f "replacement/${policy}.llc_repl" ]] \
            || fail "Missing replacement/${policy}.llc_repl"
    done

    for trace in "${SINGLE_TRACES[@]}"; do
        [[ -f "dpc3_traces/$trace" ]] \
            || fail "Missing trace dpc3_traces/$trace"
    done

    [[ -f "$SELECTION_FILE" ]] \
        || fail "Missing $SELECTION_FILE"
}

write_config() {
    local policy="$1"
    local size_mb="$2"
    local sets="$3"
    local core_mode="$4"
    local config_file="$5"

    cat > "$config_file" <<EOF
experiment=Task 2 replacement-policy and LLC-size study
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
llc_replacement_policy=$policy
warmup_instructions_millions=$WARMUP_MILLIONS
simulation_instructions_millions=$SIMULATION_MILLIONS
EOF
}

validate_baseline

mapfile -t FOUR_TRACES < <(
    awk -F': ' '/^Core [0-3]: / { print $2 }' "$SELECTION_FILE"
)

[[ "${#FOUR_TRACES[@]}" -eq 4 ]] \
    || fail "Expected four selected traces, found ${#FOUR_TRACES[@]}"

for trace in "${FOUR_TRACES[@]}"; do
    [[ -f "dpc3_traces/$trace" ]] \
        || fail "Missing selected four-core trace dpc3_traces/$trace"
done

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
echo "================================================================"
echo "Task 2 replacement-policy × LLC-size experiment"
echo "Policies: SRRIP, DRRIP, SHIP, MRU, Random"
echo "Sizes:    1 MB, 2 MB, 4 MB, 8 MB"
echo "LRU will be reused from the completed LLC-size study."
echo "This script is resume-safe for completed result/timing pairs."
echo "================================================================"

for size_mb in "${SIZES_MB[@]}"; do
    sets="${LLC_SETS_BY_SIZE[$size_mb]}"

    set_define LLC_SET "$sets"
    set_define LLC_WAY "$LLC_ASSOCIATIVITY"

    [[ "$(get_define LLC_SET)" == "$sets" ]] \
        || fail "Failed to set LLC_SET=$sets"
    [[ "$(get_define LLC_WAY)" == "$LLC_ASSOCIATIVITY" ]] \
        || fail "Failed to set LLC_WAY=$LLC_ASSOCIATIVITY"

    for policy in "${POLICIES[@]}"; do
        single_config="$CONFIG_DIR/${policy}__llc_${size_mb}mb__single.txt"
        four_config="$CONFIG_DIR/${policy}__llc_${size_mb}mb__four_core.txt"

        write_config \
            "$policy" "$size_mb" "$sets" \
            "single_core" "$single_config"

        write_config \
            "$policy" "$size_mb" "$sets" \
            "four_core_shared_llc" "$four_config"

        # ---------------------------------------------------------------
        # Single-core build and runs
        # ---------------------------------------------------------------

        single_binary="${PREDICTOR}-no-no-no-no-${policy}-1core"
        single_build_log="$SINGLE_DIR/build_logs/${policy}__llc_${size_mb}mb.txt"

        echo
        echo "================================================================"
        echo "BUILD SINGLE | policy=$policy | LLC=${size_mb}MB"
        echo "================================================================"

        ./build_champsim.sh \
            "$PREDICTOR" no no no no "$policy" 1 \
            |& tee "$single_build_log"

        [[ -x "bin/$single_binary" ]] \
            || fail "Missing binary bin/$single_binary"

        for trace in "${SINGLE_TRACES[@]}"; do
            trace_tag="${trace%.champsimtrace.xz}"
            result_copy="$SINGLE_DIR/simulator_output/${policy}__llc_${size_mb}mb__${trace_tag}.txt"
            timing_file="$SINGLE_DIR/timing/${policy}__llc_${size_mb}mb__${trace_tag}.txt"

            if result_is_complete "$result_copy" 1 \
                && timing_is_complete "$timing_file"; then
                echo "SKIP complete single run: $policy | ${size_mb}MB | $trace"
                skipped_single=$((skipped_single + 1))
            else
                rm -f "$result_copy" "$timing_file"

                marker=$(mktemp)
                touch "$marker"

                echo
                echo "RUN SINGLE | policy=$policy | LLC=${size_mb}MB | $trace"

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
                    fail "Could not locate result for $policy ${size_mb}MB $trace"
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
"$PREDICTOR,$policy,$size_mb,$sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$trace,$single_binary,$result_copy,$timing_file" \
                >> "$SINGLE_MANIFEST"
        done

        # ---------------------------------------------------------------
        # Four-core build and run
        # ---------------------------------------------------------------

        four_binary="${PREDICTOR}-no-no-no-no-${policy}-4core"
        four_build_log="$FOUR_DIR/build_logs/${policy}__llc_${size_mb}mb.txt"
        four_result="$FOUR_DIR/simulator_output/${policy}__llc_${size_mb}mb__mix${MIX_NUMBER}.txt"
        four_timing="$FOUR_DIR/timing/${policy}__llc_${size_mb}mb__mix${MIX_NUMBER}.txt"

        echo
        echo "================================================================"
        echo "BUILD FOUR | policy=$policy | LLC=${size_mb}MB"
        echo "================================================================"

        ./build_champsim.sh \
            "$PREDICTOR" no no no no "$policy" 4 \
            |& tee "$four_build_log"

        [[ -x "bin/$four_binary" ]] \
            || fail "Missing binary bin/$four_binary"

        if result_is_complete "$four_result" 4 \
            && timing_is_complete "$four_timing"; then
            echo "SKIP complete four-core run: $policy | ${size_mb}MB"
            skipped_four=$((skipped_four + 1))
        else
            rm -f "$four_result" "$four_timing"

            marker=$(mktemp)
            touch "$marker"

            echo
            echo "RUN FOUR | policy=$policy | LLC=${size_mb}MB | mix=$MIX_NUMBER"

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
                fail "Could not locate four-core result for $policy ${size_mb}MB"
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
"$PREDICTOR,$policy,$size_mb,$sets,$LLC_ASSOCIATIVITY,$BLOCK_SIZE_BYTES,$MIX_NUMBER,${FOUR_TRACES[0]},${FOUR_TRACES[1]},${FOUR_TRACES[2]},${FOUR_TRACES[3]},$four_binary,$four_result,$four_timing" \
            >> "$FOUR_MANIFEST"
    done
done

echo
echo "================================================================"
echo "Replacement-policy × LLC-size experiments completed."
echo "New single-core runs:      $completed_single"
echo "Skipped single-core runs:  $skipped_single"
echo "New four-core runs:        $completed_four"
echo "Skipped four-core runs:    $skipped_four"
echo "Single manifest rows:      $(($(wc -l < "$SINGLE_MANIFEST") - 1))"
echo "Four-core manifest rows:   $(($(wc -l < "$FOUR_MANIFEST") - 1))"
echo "Original cache.h restored automatically."
echo "================================================================"
