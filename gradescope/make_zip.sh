#!/usr/bin/env bash
# Usage: ./make_zip.sh <hwNN>
# Output: ../<hwNN>_autograder.zip
set -euo pipefail

HW=${1:?Usage: ./make_zip.sh <hwNN>}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${SCRIPT_DIR}/../${HW}_autograder.zip"

cd "$SCRIPT_DIR"

if [ ! -d "${HW}/rust_template" ]; then
    echo "ERROR: ${HW}/rust_template not found" >&2
    exit 1
fi

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

cp setup.sh run_autograder grader.py helpers.py questions.py results.py repo_checks.py lateness.py "$TMP/"
cp "${HW}/config.json" "$TMP/config.json"
cp -r "${HW}/rust_template" "$TMP/rust_template"
rm -rf "$TMP/rust_template/target"

# Optional: bundle a Classroom roster CSV so the autograder can map BU email → GitHub username
if [ -f "${HW}/roster.csv" ]; then
    cp "${HW}/roster.csv" "$TMP/roster.csv"
fi

cd "$TMP"
zip -r "$OUT" . --exclude "*/__pycache__/*" --exclude "*/Cargo.lock"

echo "Created: $OUT"
