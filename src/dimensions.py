"""
dimensions.py — Reciprocal Rank Fusion (RRF) utilities.

RRF (Cormack, Clarke & Buettcher, 2009) fuses multiple ranked lists into
a single score without requiring weight tuning on a hold-out set.

    RRF_score(d) = Σ_i  w_i / (k + rank_i(d))

where k=60 is standard, rank_i is the 1-based position in dimension i,
and w_i is an optional per-dimension importance weight.
"""

from __future__ import annotations


def score_to_ranked_positions(scores: dict[str, float]) -> dict[str, int]:
    """
    Convert {candidate_id: raw_score} to {candidate_id: rank_position}.
    
    Higher scores get lower (better) rank positions.
    Ties get the same rank position (Standard competition ranking, e.g. 1, 1, 3).
    
    Returns 1-based ranks.
    """
    sorted_items = sorted(
        scores.items(),
        key=lambda x: -x[1]
    )
    ranks = {}
    current_rank = 1
    for i, (cid, score) in enumerate(sorted_items):
        if i > 0 and score < sorted_items[i - 1][1]:
            current_rank = i + 1
        ranks[cid] = current_rank
    return ranks


def reciprocal_rank_fusion(
    dimension_rank_lists: list[dict[str, int]],
    k: int = 60,
    weights: list[float] | None = None,
) -> dict[str, float]:
    """
    Standard RRF fusion across multiple rank lists.
    
    Args:
        dimension_rank_lists: List of {cand_id: rank_position} dicts,
                              one per dimension.
        k: RRF smoothing parameter. k=60 is standard (reduces impact
           of outlier ranks). Higher k → more uniform contribution.
        weights: Optional per-dimension importance weights.
                 Default: all dimensions weighted equally.
    
    Returns:
        {candidate_id: rrf_score} — higher is better.
    """
    n_dims = len(dimension_rank_lists)
    if weights is None:
        weights = [1.0] * n_dims
    
    assert len(weights) == n_dims, f"weights length {len(weights)} != {n_dims} dimensions"
    
    # Collect all candidate IDs across all dimensions
    all_cids = set()
    for rank_list in dimension_rank_lists:
        all_cids.update(rank_list.keys())
    
    # Compute RRF score for each candidate
    rrf_scores = {}
    max_rank = len(all_cids) + 1  # Fallback rank for missing candidates
    
    for cid in all_cids:
        score = 0.0
        for i, rank_list in enumerate(dimension_rank_lists):
            rank = rank_list.get(cid, max_rank)
            score += weights[i] / (k + rank)
        rrf_scores[cid] = score
    
    return rrf_scores
