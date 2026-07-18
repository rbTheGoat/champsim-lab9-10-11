#!/usr/bin/env bash

set -u

REPORT="reports/final_submission_verification.txt"
mkdir -p reports

failures=0
warnings=0

pass() {
    echo "[PASS] $*"
}

warn() {
    echo "[WARN] $*"
    warnings=$((warnings + 1))
}

fail() {
    echo "[FAIL] $*"
    failures=$((failures + 1))
}

check_file() {
    local path="$1"

    if [[ -f "$path" ]]; then
        pass "$path"
    else
        fail "Missing file: $path"
    fi
}

check_directory() {
    local path="$1"

    if [[ -d "$path" ]]; then
        pass "$path"
    else
        fail "Missing directory: $path"
    fi
}

check_find_count() {
    local description="$1"
    local expected="$2"
    local directory="$3"
    local pattern="$4"

    local actual=0

    if [[ -d "$directory" ]]; then
        actual=$(find "$directory" -maxdepth 1 -type f -name "$pattern" | wc -l)
    fi

    if [[ "$actual" == "$expected" ]]; then
        pass "$description = $actual"
    else
        fail "$description expected $expected, found $actual"
    fi
}

{
    echo "============================================================"
    echo "FINAL SUBMISSION VERIFICATION"
    echo "Generated: $(date -Is)"
    echo "Repository: $(pwd)"
    echo "============================================================"
    echo

    echo "SECTION 1 — Core source files"
    check_file branch/modified_bullseye.bpred
    check_file branch/adaptive_bullseye.bpred

    for policy in lru srrip drrip ship mru random hcit; do
        check_file "replacement/${policy}.llc_repl"
    done
    echo

    echo "SECTION 2 — Design and report files"
    check_file reports/modified_bullseye_design.md
    check_file reports/adaptive_bullseye_design.md
    check_file reports/mru_random_design.md
    check_file reports/adaptive_hcit_design.md
    check_file reports/task2_results_analysis.md
    check_file reports/task2_hcit_results_analysis.md
    check_file reports/final_assignment_report.md
    check_file reports/submission_checklist.md
    echo

    echo "SECTION 3 — Random four-core trace evidence"
    check_directory random_trace_output
    check_file random_trace_output/selected_4core_traces.txt

    generator_count=$(find . -maxdepth 3 -type f \
        \( -iname "*random*trace*.py" \
        -o -iname "*random*trace*.cpp" \
        -o -iname "*random*trace*.sh" \) \
        | wc -l)

    if [[ "$generator_count" -ge 1 ]]; then
        pass "Random-trace generator source found"
    else
        fail "Random-trace generator source not found"
    fi
    echo

    echo "SECTION 4 — Required traces"
    trace_count=0
    if [[ -d dpc3_traces ]]; then
        trace_count=$(find dpc3_traces -maxdepth 1 -type f \
            -name "*.champsimtrace.xz" | wc -l)
    fi

    if [[ "$trace_count" -ge 15 ]]; then
        pass "Trace files available = $trace_count"
    else
        fail "Expected at least 15 trace files, found $trace_count"
    fi
    echo

    echo "SECTION 5 — Restored baseline cache configuration"
    llc_set=$(awk '$1=="#define" && $2=="LLC_SET" {print $3; exit}' inc/cache.h)
    llc_way=$(awk '$1=="#define" && $2=="LLC_WAY" {print $3; exit}' inc/cache.h)

    if [[ "$llc_set" == "4096" ]]; then
        pass "LLC_SET restored to 4096"
    else
        fail "LLC_SET should be 4096, found $llc_set"
    fi

    if [[ "$llc_way" == "16" ]]; then
        pass "LLC_WAY restored to 16"
    else
        fail "LLC_WAY should be 16, found $llc_way"
    fi
    echo

    echo "SECTION 6 — Task 1 outputs"
    check_file results/csv/task1_single_summary_all_predictors.csv
    check_file results/csv/task1_four_core_summary_all_predictors.csv

    task1_graph_count=0
    if [[ -d results/graphs/task1 ]]; then
        task1_graph_count=$(find results/graphs/task1 -type f \
            -name "*.png" | wc -l)
    fi

    if [[ "$task1_graph_count" -ge 20 ]]; then
        pass "Task 1 graphs = $task1_graph_count"
    else
        fail "Expected at least 20 Task 1 graphs, found $task1_graph_count"
    fi
    echo

    echo "SECTION 7 — LLC-size outputs"
    check_file results/csv/task2_llc_size_single_summary.csv
    check_file results/csv/task2_llc_size_four_core_summary.csv
    check_find_count \
        "LLC-size single raw results" \
        16 \
        results/raw/task2/llc_size/single/simulator_output \
        "*.txt"
    check_find_count \
        "LLC-size four-core raw results" \
        4 \
        results/raw/task2/llc_size/four_core/simulator_output \
        "*.txt"
    echo

    echo "SECTION 8 — Associativity outputs"
    check_file results/csv/task2_llc_associativity_single_summary.csv
    check_file results/csv/task2_llc_associativity_four_core_summary.csv
    check_find_count \
        "8-way single raw results" \
        4 \
        results/raw/task2/llc_associativity/8way/single/simulator_output \
        "*.txt"
    check_find_count \
        "8-way four-core raw results" \
        1 \
        results/raw/task2/llc_associativity/8way/four_core/simulator_output \
        "*.txt"
    echo

    echo "SECTION 9 — Six-policy replacement outputs"
    check_file results/csv/task2_replacement_policy_size_single_summary_all_policies.csv
    check_file results/csv/task2_replacement_policy_size_four_core_summary_all_policies.csv
    check_find_count \
        "Non-LRU single raw results" \
        80 \
        results/raw/task2/replacement_policy_size/single/simulator_output \
        "*.txt"
    check_find_count \
        "Non-LRU four-core raw results" \
        20 \
        results/raw/task2/replacement_policy_size/four_core/simulator_output \
        "*.txt"
    echo

    echo "SECTION 10 — HCIT outputs"
    check_file results/csv/task2_replacement_policy_size_single_summary_with_hcit.csv
    check_file results/csv/task2_replacement_policy_size_four_core_summary_with_hcit.csv
    check_file results/csv/task2_hcit_internal_single.csv
    check_file results/csv/task2_hcit_internal_four_core.csv
    check_find_count \
        "HCIT single raw results" \
        16 \
        results/raw/task2/hcit_size/single/simulator_output \
        "*.txt"
    check_find_count \
        "HCIT four-core raw results" \
        4 \
        results/raw/task2/hcit_size/four_core/simulator_output \
        "*.txt"

    hcit_missing=0
    if compgen -G \
        "results/raw/task2/hcit_size/single/simulator_output/*.txt" \
        >/dev/null \
        && compgen -G \
        "results/raw/task2/hcit_size/four_core/simulator_output/*.txt" \
        >/dev/null
    then
        hcit_missing=$(grep -L \
            "HCIT Replacement Statistics" \
            results/raw/task2/hcit_size/single/simulator_output/*.txt \
            results/raw/task2/hcit_size/four_core/simulator_output/*.txt \
            2>/dev/null | wc -l)
    else
        hcit_missing=20
    fi

    if [[ "$hcit_missing" == "0" ]]; then
        pass "All HCIT results contain policy statistics"
    else
        fail "$hcit_missing HCIT result files lack policy statistics or are missing"
    fi
    echo

    echo "SECTION 11 — Graph counts"
    for path in \
        results/graphs/task2/llc_size \
        results/graphs/task2/llc_associativity \
        results/graphs/task2/replacement_policy_size \
        results/graphs/task2/hcit_comparison
    do
        if [[ -d "$path" ]]; then
            count=$(find "$path" -type f -name "*.png" | wc -l)
            pass "$path graphs = $count"
        else
            fail "Missing graph directory: $path"
        fi
    done
    echo

    echo "SECTION 12 — Git status"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        branch=$(git branch --show-current)
        pass "Git branch: $branch"

        if [[ -z "$(git status --short)" ]]; then
            pass "Working tree clean"
        else
            warn "Working tree has uncommitted changes:"
            git status --short
        fi

        if git remote get-url origin >/dev/null 2>&1; then
            pass "Origin: $(git remote get-url origin)"
        else
            fail "Git origin is not configured"
        fi
    else
        fail "Current directory is not a Git repository"
    fi
    echo

    echo "============================================================"
    echo "SUMMARY"
    echo "Failures: $failures"
    echo "Warnings: $warnings"
    echo "============================================================"

} | tee "$REPORT"

echo
echo "Saved verification report: $REPORT"

if [[ "$failures" -ne 0 ]]; then
    exit 1
fi

exit 0
