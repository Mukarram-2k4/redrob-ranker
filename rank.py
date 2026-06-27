#!/usr/bin/env python3
"""
rank.py — CLI entry point for the Redrob Candidate Ranking Engine.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Produces a CSV ranking the top 100 candidates for the Senior AI Engineer role.
Must complete within 5 minutes on CPU with 16 GB RAM and no network access.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


class StageTimer:
    """Simple timer for logging per-stage performance."""

    def __init__(self):
        self.stages: list[tuple[str, float]] = []
        self._start: float = 0.0

    def start(self, name: str):
        self._current_name = name
        self._start = time.perf_counter()
        print(f"  ▸ {name}...", end="", flush=True)

    def stop(self):
        elapsed = time.perf_counter() - self._start
        self.stages.append((self._current_name, elapsed))
        print(f" {elapsed:.2f}s")

    def summary(self):
        total = sum(t for _, t in self.stages)
        print(f"\n{'─' * 50}")
        print(f"  STAGE TIMING SUMMARY")
        print(f"{'─' * 50}")
        for name, elapsed in self.stages:
            bar = "█" * int(elapsed / total * 30) if total > 0 else ""
            print(f"  {name:<30s} {elapsed:6.2f}s  {bar}")
        print(f"{'─' * 50}")
        print(f"  {'TOTAL':<30s} {total:6.2f}s")
        print(f"  {'Budget remaining':<30s} {300 - total:6.2f}s")
        print(f"{'─' * 50}")


def main():
    parser = argparse.ArgumentParser(
        description="Redrob AI Candidate Ranking Engine — "
                    "Rank top 100 candidates for Senior AI Engineer role.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--candidates",
        type=str,
        required=True,
        help="Path to candidates.jsonl (100K candidate profiles)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./submission.csv",
        help="Output path for submission CSV (default: ./submission.csv)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of multiprocessing workers for NLP stage "
             "(default: min(cpu_count, 8))",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print per-stage timing summary after completion",
    )

    args = parser.parse_args()

    # Validate input path
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        print(f"ERROR: Candidates file not found: {candidates_path}")
        sys.exit(1)

    # Determine worker count
    if args.workers is None:
        try:
            cpu_count = os.cpu_count() or 4
            n_workers = min(cpu_count, 8)
        except Exception:
            n_workers = 4
    else:
        n_workers = args.workers

    # Ensure output directory exists
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    timer = StageTimer()
    pipeline_start = time.perf_counter()

    print(f"\n{'═' * 50}")
    print(f"  REDROB AI CANDIDATE RANKING ENGINE")
    print(f"{'═' * 50}")
    print(f"  Input:   {candidates_path}")
    print(f"  Output:  {out_path}")
    print(f"  Workers: {n_workers}")
    print(f"{'═' * 50}\n")

    # ── Stage 0: Bootstrap ──────────────────────────────────────────────
    timer.start("Stage 0: Bootstrap")
    from src.ingest import build_lookups
    lookups = build_lookups()
    timer.stop()

    # ── Stage 1: Ingestion ──────────────────────────────────────────────
    timer.start("Stage 1: Ingestion")
    from src.ingest import load_candidates
    candidates = load_candidates(str(candidates_path))
    print(f"    Loaded {len(candidates)} candidates", end="")
    timer.stop()

    # ── Stage 2: Early Elimination ──────────────────────────────────────
    timer.start("Stage 2: Early Elimination")
    from src.filters import early_eliminate
    survivors, eliminated = early_eliminate(candidates, lookups)
    print(f"    {len(survivors)} survivors, {len(eliminated)} eliminated", end="")
    timer.stop()

    # ── Stage 3: Feature Extraction ─────────────────────────────────────
    timer.start("Stage 3a: Behavioral Features")
    from src.features import compute_behavioral_features
    compute_behavioral_features(survivors)
    timer.stop()

    timer.start("Stage 3b: Tabular Features")
    from src.features import compute_tabular_features
    compute_tabular_features(survivors, lookups)
    timer.stop()

    timer.start("Stage 3c: Semantic Features")
    from src.features import compute_semantic_features
    compute_semantic_features(survivors, lookups, n_workers=n_workers)
    timer.stop()

    # ── Stage 4: Honeypot Full Pass ─────────────────────────────────────
    timer.start("Stage 4: Honeypot Full Pass")
    from src.filters import honeypot_full_pass
    honeypot_full_pass(survivors)
    flagged = sum(1 for c in survivors if c.honeypot_flag)
    print(f"    {flagged} honeypots flagged", end="")
    timer.stop()

    # ── Stage 5: Scoring ────────────────────────────────────────────────
    timer.start("Stage 5: Scoring")
    from src.scorer import compute_scores
    compute_scores(survivors)
    timer.stop()

    # ── Stage 6: Top-100 Selection + Guardrails ─────────────────────────
    timer.start("Stage 6: Top-100 + Guardrails")
    from src.output import select_top_100
    top_100 = select_top_100(survivors)
    timer.stop()

    # ── Stage 7: Reasoning + CSV ────────────────────────────────────────
    timer.start("Stage 7: Output")
    from src.output import write_submission_csv
    write_submission_csv(top_100, str(out_path))
    timer.stop()

    # ── Summary ─────────────────────────────────────────────────────────
    total_time = time.perf_counter() - pipeline_start
    print(f"\n  ✓ Submission written to: {out_path}")
    print(f"  ✓ Total runtime: {total_time:.2f}s")

    if total_time > 300:
        print(f"  ⚠ WARNING: Exceeded 5-minute budget!")
    else:
        print(f"  ✓ Within 5-minute budget ({300 - total_time:.0f}s remaining)")

    if args.profile:
        timer.summary()

    # Quick sanity check on output
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"\n  Output: {len(lines) - 1} data rows (expected 100)")
        if len(lines) >= 2:
            print(f"  Rank 1:   {lines[1].strip()[:80]}...")
        if len(lines) >= 101:
            print(f"  Rank 100: {lines[100].strip()[:80]}...")


if __name__ == "__main__":
    main()
