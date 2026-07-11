from pathlib import Path
import re

header_path = Path("inc/ooo_cpu.h")
cpu_path = Path("src/ooo_cpu.cc")
main_path = Path("src/main.cc")

header = header_path.read_text(encoding="utf-8")
cpu_source = cpu_path.read_text(encoding="utf-8")
main = main_path.read_text(encoding="utf-8")

def require(condition, message):
    if not condition:
        raise SystemExit(f"PATCH ERROR: {message}")

header_anchor = "    uint64_t num_branch, branch_mispredictions;\n"
require(header.count(header_anchor) == 1,
        "Could not uniquely locate branch counters in inc/ooo_cpu.h")
header = header.replace(
    header_anchor,
    header_anchor
    + "    uint64_t branch_prediction_latency_ns,\n"
    + "             branch_prediction_latency_samples;\n",
    1,
)

constructor_anchor = (
    "        num_branch = 0;\n"
    "        branch_mispredictions = 0;\n"
)
require(header.count(constructor_anchor) == 1,
        "Could not uniquely locate constructor branch initialization")
header = header.replace(
    constructor_anchor,
    constructor_anchor
    + "        branch_prediction_latency_ns = 0;\n"
    + "        branch_prediction_latency_samples = 0;\n",
    1,
)

if "#include <chrono>" not in cpu_source:
    cpu_source = "#include <chrono>\n" + cpu_source

prediction_pattern = re.compile(
    r"(?m)^([ \t]*)uint8_t branch_prediction = "
    r"predict_branch\(IFETCH_BUFFER\.entry\[ifetch_buffer_index\]\.ip\);$"
)
matches = list(prediction_pattern.finditer(cpu_source))
require(len(matches) == 2,
        f"Expected exactly two predict_branch call sites, found {len(matches)}")

def replace_prediction_call(match):
    indent = match.group(1)
    return (
        f"{indent}auto branch_prediction_start = std::chrono::steady_clock::now();\n"
        f"{indent}uint8_t branch_prediction = "
        f"predict_branch(IFETCH_BUFFER.entry[ifetch_buffer_index].ip);\n"
        f"{indent}auto branch_prediction_end = std::chrono::steady_clock::now();\n"
        f"\n"
        f"{indent}if (warmup_complete[cpu]) {{\n"
        f"{indent}    branch_prediction_latency_ns += static_cast<uint64_t>(\n"
        f"{indent}        std::chrono::duration_cast<std::chrono::nanoseconds>(\n"
        f"{indent}            branch_prediction_end - branch_prediction_start\n"
        f"{indent}        ).count()\n"
        f"{indent}    );\n"
        f"{indent}    branch_prediction_latency_samples++;\n"
        f"{indent}}}"
    )

cpu_source = prediction_pattern.sub(replace_prediction_call, cpu_source)

reset_pattern = re.compile(
    r"(?m)^([ \t]*)ooo_cpu\[i\]\.branch_mispredictions = 0;[ \t]*$"
)
reset_matches = list(reset_pattern.finditer(main))
require(len(reset_matches) == 1,
        f"Expected one warm-up reset location, found {len(reset_matches)}")

def replace_reset(match):
    indent = match.group(1)
    return (
        f"{indent}ooo_cpu[i].branch_mispredictions = 0;\n"
        f"{indent}ooo_cpu[i].branch_prediction_latency_ns = 0;\n"
        f"{indent}ooo_cpu[i].branch_prediction_latency_samples = 0;"
    )

main = reset_pattern.sub(replace_reset, main, count=1)

print_pattern = re.compile(
    r'(?m)^([ \t]*)cout << "Branch types" << endl;$'
)
print_matches = list(print_pattern.finditer(main))
require(len(print_matches) == 1,
        f"Expected one Branch types output location, found {len(print_matches)}")

def insert_latency_output(match):
    indent = match.group(1)
    return (
        f"{indent}double average_predictor_lookup_latency_ns = 0.0;\n"
        f"{indent}if (ooo_cpu[i].branch_prediction_latency_samples != 0) {{\n"
        f"{indent}    average_predictor_lookup_latency_ns =\n"
        f"{indent}        static_cast<double>(ooo_cpu[i].branch_prediction_latency_ns) /\n"
        f"{indent}        static_cast<double>(ooo_cpu[i].branch_prediction_latency_samples);\n"
        f"{indent}}}\n"
        f"\n"
        f'{indent}cout << "CPU " << i\n'
        f'{indent}     << " Average Predictor Lookup Latency (ns): "\n'
        f"{indent}     << average_predictor_lookup_latency_ns\n"
        f"{indent}     << endl;\n"
        f"\n"
        f'{indent}cout << "CPU " << i\n'
        f'{indent}     << " Predictor Lookup Samples: "\n'
        f"{indent}     << ooo_cpu[i].branch_prediction_latency_samples\n"
        f"{indent}     << endl << endl;\n"
        f"\n"
        f'{indent}cout << "Branch types" << endl;'
    )

main = print_pattern.sub(insert_latency_output, main, count=1)
require(main.count("print_branch_stats") >= 2,
        "print_branch_stats() appears to be defined but not called")

header_path.write_text(header, encoding="utf-8")
cpu_path.write_text(cpu_source, encoding="utf-8")
main_path.write_text(main, encoding="utf-8")

print("Prediction-latency instrumentation applied successfully.")
