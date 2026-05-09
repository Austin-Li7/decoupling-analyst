#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="${OBSIDIAN_MGT470_CASES_DIR:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/AustinObsidianVault/MGT470/mgt470-analyst-cases}"

sync_case() {
  local slug="$1"
  local display="$2"
  local case_dir="$ROOT_DIR/cases/_archive/$slug"
  local target_dir="$VAULT_ROOT/$display"

  mkdir -p "$target_dir"
  cp "$case_dir/run/final_report.md" "$target_dir/final_report.md"
  cp "$case_dir/run/final_report_zh.md" "$target_dir/final_report_zh.md"
  cp "$case_dir/review.md" "$target_dir/review.md"
}

sync_case "notion-grounded-20260509" "Notion"
sync_case "liquid-death-grounded-20260509" "Liquid Death"
sync_case "nubank-grounded-20260509" "Nubank"

echo "Synced grounded case reports to $VAULT_ROOT"
