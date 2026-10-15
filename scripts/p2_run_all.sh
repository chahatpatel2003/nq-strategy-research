#!/bin/bash
# Phase 2 full pipeline AFTER the freeze.  Stops on first error.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python

echo "=== development 2021-2023 ==="
$PY scripts/p2_03_run.py --split dev
$PY scripts/p2_04_report.py --tag dev --title "Impulse Exhaustion — DEVELOPMENT 2021-2023"

echo "=== validation 2024 (ONCE) ==="
$PY scripts/p2_03_run.py --split val
$PY scripts/p2_04_report.py --tag val --title "Impulse Exhaustion — VALIDATION 2024"

echo "=== diagnostics ==="
$PY scripts/p2_05_charts.py --tag dev
$PY scripts/p2_05_charts.py --tag val
$PY scripts/p2_07_controls.py --tag dev
$PY scripts/p2_07_controls.py --tag val
$PY scripts/p2_10_ablation.py dev

echo "=== audits and verdict ==="
$PY scripts/p2_11_leakage_audit.py
$PY scripts/p2_08_verdict.py
$PY scripts/p2_09_integrity.py
echo "=== DONE ==="
