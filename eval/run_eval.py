"""
run_eval.py — Run self-evaluation to calculate NDCG scores against gold labels.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import build_lookups, load_candidates
from src.filters import early_eliminate, honeypot_full_pass
from src.features import (
    compute_behavioral_features,
    compute_tabular_features,
    compute_semantic_features,
)
from src.semantic import compute_tfidf_scores
from src.scorer import compute_scores
from src.output import select_top_100
from eval.gold_labeler import label_candidate, compute_ndcg


def main():
    parser = argparse.ArgumentParser(description="Self-Evaluation NDCG Evaluator")
    parser.add_argument(
        "--candidates", type=str, required=True, help="Path to candidates.jsonl file"
    )
    args = parser.parse_args()

    cand_path = Path(args.candidates)
    if not cand_path.exists():
        print(f"Error: candidates file {cand_path} does not exist.")
        sys.exit(1)

    print(f"Loading candidates from {cand_path}...")
    candidates = load_candidates(str(cand_path))
    print(f"Loaded {len(candidates)} candidates.")

    # Run pipeline stages
    lookups = build_lookups()
    survivors, eliminated = early_eliminate(candidates, lookups)
    compute_behavioral_features(survivors)
    compute_tabular_features(survivors, lookups)
    compute_semantic_features(survivors, lookups, n_workers=4)
    tfidf_scores = compute_tfidf_scores(survivors)
    honeypot_full_pass(survivors)
    compute_scores(survivors, tfidf_scores)
    top_100 = select_top_100(survivors)

    # Compute gold labels for all survivors
    all_gold_labels = {c.candidate_id: label_candidate(c) for c in survivors}

    # Gold labels for ranked top 100
    top_100_labels = [all_gold_labels[c.candidate_id] for c in top_100]

    # Overall label counts in top 100
    counts = {4: 0, 3: 0, 2: 0, 1: 0, 0: 0}
    for l in top_100_labels:
        counts[l] += 1

    # Calculate NDCG
    ndcg_10 = compute_ndcg(top_100_labels, 10)
    ndcg_50 = compute_ndcg(top_100_labels, 50)
    ndcg_100 = compute_ndcg(top_100_labels, 100)

    print("\n" + "=" * 50)
    print("  SELF-EVALUATION METRIC REPORT")
    print("=" * 50)
    print(f"  NDCG@10:  {ndcg_10:.4f}")
    print(f"  NDCG@50:  {ndcg_50:.4f}")
    print(f"  NDCG@100: {ndcg_100:.4f}")
    print("-" * 50)
    print("  Top 100 Quality Distribution:")
    print(f"    Textbook (4): {counts[4]}")
    print(f"    Strong (3):   {counts[3]}")
    print(f"    Gem (2):      {counts[2]}")
    print(f"    Weak (1):     {counts[1]}")
    print(f"    Irrelevant:   {counts[0]}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
