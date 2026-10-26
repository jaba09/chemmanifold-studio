#!/usr/bin/env bash
# Build and run the UDF checks outside Fluent (Linux/macOS/WSL with a C compiler):
#   fluent/tests/run_tests.sh data/08_fluent/resnet_film
# 1. cm_selftest: the C core against the PyTorch test vectors (and its speed per cell call);
# 2. mock_fluent: the Fluent hooks themselves, driven through a stand-in udf.h.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
model_dir="$(cd "${1:?usage: run_tests.sh <dir with chemmanifold_model.txt and chemmanifold_tests.txt>}" && pwd)"
CC="${CC:-cc}"
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT

$CC -O2 -o "$build/cm_selftest" "$here/cm_selftest.c" "$here/../udf/chemmanifold_core.c" -lm
"$build/cm_selftest" "$model_dir/chemmanifold_model.txt" "$model_dir/chemmanifold_tests.txt"

$CC -O2 -I"$here/mock" -I"$here/../udf" -o "$build/mock_fluent" "$here/mock_fluent.c" \
    "$here/../udf/chemmanifold_udf.c" "$here/../udf/chemmanifold_core.c" -lm
for v in RP_NODE RP_HOST; do   # the parallel builds must at least compile
    $CC -fsyntax-only -I"$here/mock" -I"$here/../udf" -D$v=1 "$here/../udf/chemmanifold_udf.c"
done
cp "$model_dir/chemmanifold_model.txt" "$model_dir/chemmanifold_tests.txt" "$build/"
(cd "$build" && ./mock_fluent && echo "--- chemmanifold_monitor.csv" && cat chemmanifold_monitor.csv)
