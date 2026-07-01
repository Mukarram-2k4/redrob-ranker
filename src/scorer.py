"""
scorer.py — Composite scoring module.

Fuses 5 distinct dimensions of candidate quality using Reciprocal Rank Fusion (RRF):
1. Dimension 1: Technical Score (Vectorized via numpy.dot)
2. Dimension 2: Career Trajectory
3. Dimension 3: Behavioral Score
4. Dimension 4: Trust Score (Inverse honeypot confidence)
5. Dimension 5: Semantic TF-IDF Similarity Score

Applies post-RRF trust grading multipliers, architecture astronaut penalties,
and micro-bonuses for fine-grained ranking and tie-breaking.
"""

import numpy as np
from src.models import Candidate
from src.config import TECHNICAL_WEIGHTS
from src.dimensions import score_to_ranked_positions, reciprocal_rank_fusion


def _salary_alignment_bonus(cand: Candidate) -> float:
    """
    Small bonus for candidates whose expected salary aligns with Senior AI
    Engineer compensation in India (15-40 LPA sweet spot).
    """
    sal_min = cand.signals.salary_min_lpa
    sal_max = cand.signals.salary_max_lpa
    if sal_min <= 0 or sal_max <= 0:
        return 0.0
    midpoint = (sal_min + sal_max) / 2.0
    if 15.0 <= midpoint <= 40.0:
        return 0.01
    elif 10.0 <= midpoint < 15.0 or 40.0 < midpoint <= 55.0:
        return 0.005
    else:
        return 0.0


def _engagement_recency_bonus(cand: Candidate) -> float:
    """
    Small bonus for candidates showing active platform engagement.
    """
    search = min(cand.signals.search_appearance_30d, 100) / 100.0
    saved = min(cand.signals.saved_by_recruiters_30d, 50) / 50.0
    return min(0.015, (search * 0.01 + saved * 0.005))


def _profile_completeness_bonus(cand: Candidate) -> float:
    """Tiny bonus for high profile completeness (0 to 0.005)."""
    pcs = cand.signals.profile_completeness_score
    if pcs >= 90:
        return 0.005
    elif pcs >= 75:
        return 0.002
    return 0.0


def compute_scores(survivors: list[Candidate], tfidf_scores: dict[str, float]) -> None:
    """
    Compute 5-dimension RRF score for all candidates:
    1. Dimension 1: Technical (career_nlp + skill_depth + domain + exp_fit + company_type + recency + platform_cred)
    2. Dimension 2: Career Trajectory (title_relevance * (exp_fit + company_type + location) + edu_bonus)
    3. Dimension 3: Behavioral (behavioral_score)
    4. Dimension 4: Trust (1.0 - honeypot_confidence)
    5. Dimension 5: Semantic TF-IDF Similarity

    Fuse using RRF, apply trust multipliers and architecture astronaut penalties,
    and add micro-bonuses.
    """
    if not survivors:
        return

    features_keys = [
        "career_nlp_score",
        "skill_depth_score",
        "domain_score",
        "exp_fit_score",
        "company_type_score",
        "recency_score",
        "platform_cred_score"
    ]
    weights_keys = [
        "career_nlp",
        "skill_depth",
        "domain",
        "exp_fit",
        "company_type",
        "recency",
        "platform_cred"
    ]

    # Pre-compute normalized technical weights vector
    raw_weights = np.array([TECHNICAL_WEIGHTS[wk] for wk in weights_keys])
    w_vec = raw_weights / np.sum(raw_weights)

    tech_scores = {}
    traj_scores = {}
    beh_scores = {}
    trust_scores = {}
    sem_scores = {}

    for cand in survivors:
        cid = cand.candidate_id
        
        # 1. Technical (Vectorized via numpy.dot)
        feat_vals = np.array([cand.features.get(fk, 0.0) for fk in features_keys])
        tech_scores[cid] = float(np.dot(w_vec, feat_vals))

        # 2. Career Trajectory
        title_rel = cand.features.get("title_relevance", 0.5)
        exp_fit = cand.features.get("exp_fit_score", 0.0)
        comp_type = cand.features.get("company_type_score", 0.0)
        loc = cand.features.get("location_score", 0.0)
        edu_bonus = cand.features.get("edu_bonus", 0.0)
        traj_scores[cid] = title_rel * (exp_fit + comp_type + loc) + edu_bonus

        # 3. Behavioral
        beh_scores[cid] = cand.features.get("behavioral_score", 0.0)

        # 4. Trust (Higher trust is better)
        trust_scores[cid] = max(0.0, 1.0 - cand.honeypot_confidence)

        # 5. Semantic TF-IDF
        sem_scores[cid] = tfidf_scores.get(cid, 0.0)

    # Convert all scores to 1-based ranks
    tech_ranks = score_to_ranked_positions(tech_scores)
    traj_ranks = score_to_ranked_positions(traj_scores)
    beh_ranks = score_to_ranked_positions(beh_scores)
    trust_ranks = score_to_ranked_positions(trust_scores)
    sem_ranks = score_to_ranked_positions(sem_scores)

    # Fuse ranks via RRF
    rrf_weights = [1.6, 1.2, 0.8, 0.8, 1.0]
    fused_rrf = reciprocal_rank_fusion(
        [tech_ranks, traj_ranks, beh_ranks, trust_ranks, sem_ranks],
        k=60,
        weights=rrf_weights
    )

    # Apply penalties, multipliers, and micro-bonuses to survivors
    for cand in survivors:
        cid = cand.candidate_id
        
        # Store individual ranks on Candidate features so they can be written to reasoning
        cand.features["dim_ranks"] = {
            "T": tech_ranks.get(cid, 9999),
            "C": traj_ranks.get(cid, 9999),
            "B": beh_ranks.get(cid, 9999),
            "Tr": trust_ranks.get(cid, 9999),
            "S": sem_ranks.get(cid, 9999),
        }

        if cand.hard_disqualify:
            cand.final_score = -1.0
            continue

        base_score = fused_rrf.get(cid, 0.0)

        # Post-RRF trust multiplier
        hc = cand.honeypot_confidence
        if hc >= 0.6:
            trust_mult = 0.0
        elif hc >= 0.4:
            trust_mult = 0.2
        elif hc >= 0.25:
            trust_mult = 0.5
        else:
            trust_mult = 1.0

        score = base_score * trust_mult

        # Architecture astronaut penalty (multiplicative)
        aa_penalty = cand.features.get("architecture_astronaut_penalty", 0.0)
        if aa_penalty > 0.0:
            score *= (1.0 - aa_penalty)

        # Title chaser penalty (multiplicative)
        tc_penalty = cand.features.get("title_chaser_penalty", 0.0)
        if tc_penalty > 0.0:
            score *= (1.0 - tc_penalty)

        # Micro-bonuses for fine-grained discrimination
        salary_bonus = _salary_alignment_bonus(cand)
        engagement_bonus = _engagement_recency_bonus(cand)
        completeness_bonus = _profile_completeness_bonus(cand)

        cand.final_score = score + salary_bonus + engagement_bonus + completeness_bonus

