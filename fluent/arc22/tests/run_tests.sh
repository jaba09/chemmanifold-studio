#!/usr/bin/env bash
# Checks of the Fluent ARC22 UDF outside Fluent (Linux/macOS/WSL with a C compiler; check_0d.py needs Cantera):
#   fluent/arc22/tests/run_tests.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
udf="$here/../udf"
CC="${CC:-cc}"
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT
flags="-std=c99 -O2 -Wall"
$CC $flags -I"$here/../../tests/mock" -I"$udf" -o "$build/mock_fluent" "$here/mock_fluent.c" \
    "$udf/arc22_udf.c" "$udf/arc22_core.c" "$udf/arc22_kernel.c" -lm
for v in RP_NODE RP_HOST; do   # the parallel builds must at least compile
    $CC $flags -fsyntax-only -I"$here/../../tests/mock" -I"$udf" -D$v=1 "$udf/arc22_udf.c"
done
(cd "$build" && ./mock_fluent && echo "--- arc22_monitor.csv" && cat arc22_monitor.csv)
if python3 -c "import cantera" 2>/dev/null; then python3 "$here/check_0d.py"; else echo "(Cantera not installed: check_0d.py skipped)"; fi
