"""
scorer.py — Composite scoring module.

Combines all feature sub-scores into a single final_score per candidate.
Uses weights from config.TECHNICAL_WEIGHTS and behavioral multiplier.

Micro-bonuses (salary alignment, engagement recency, profile completeness)
add fine-grained discrimination among top-tier candidates where the main
features produce near-identical scores.
"""

from src.models import Candidate
from src.config import TECHNICAL_WEIGHTS


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
    JD: 'Active on Redrob platform (or has clear signal of being in the
    job market) so we can actually talk to them.'
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


def compute_scores(survivors: list[Candidate]) -> None:
    """
    For each survivor:
    1. Compute technical_score as weighted sum of feature sub-scores
    2. Apply title_chaser_penalty multiplicatively
    3. Apply title_relevance multiplicatively
    4. Add education bonus additively (clipped to [0, 1])
    5. Multiply by behavioral_multiplier
    6. Add micro-bonuses (salary alignment, engagement recency, profile completeness)
    7. If hard_disqualify → final_score = -1.0
    """
    for cand in survivors:
        if cand.hard_disqualify:
            cand.final_score = -1.0
            continue

        # Weighted sum of technical features
        tech_score = (
            TECHNICAL_WEIGHTS["career_nlp"]   * cand.features.get("career_nlp_score", 0.0) +
            TECHNICAL_WEIGHTS["skill_depth"]  * cand.features.get("skill_depth_score", 0.0) +
            TECHNICAL_WEIGHTS["domain"]       * cand.features.get("domain_score", 0.0) +
            TECHNICAL_WEIGHTS["exp_fit"]      * cand.features.get("exp_fit_score", 0.0) +
            TECHNICAL_WEIGHTS["company_type"] * cand.features.get("company_type_score", 0.0) +
            TECHNICAL_WEIGHTS["location"]     * cand.features.get("location_score", 0.0) +
            TECHNICAL_WEIGHTS["recency"]      * cand.features.get("recency_score", 0.0) +
            TECHNICAL_WEIGHTS["platform_cred"]* cand.features.get("platform_cred_score", 0.0)
        )

        # Apply title chaser penalty (multiplicative)
        penalty = cand.features.get("title_chaser_penalty", 0.0)
        if penalty > 0.0:
            tech_score *= (1.0 - penalty)

        # Apply title relevance (multiplicative — critical for filtering
        # keyword stuffers with non-ML titles like "Frontend Engineer")
        title_rel = cand.features.get("title_relevance", 0.5)
        tech_score *= title_rel

        # Add education bonus directly (additive, then clip)
        edu_bonus = cand.features.get("edu_bonus", 0.0)
        tech_score = max(0.0, min(1.0, tech_score + edu_bonus))

        # Multiply by behavioral multiplier
        mult = cand.features.get("behavioral_multiplier", 1.0)
        base_score = tech_score * mult

        # Micro-bonuses for fine-grained discrimination among top candidates
        salary_bonus = _salary_alignment_bonus(cand)
        engagement_bonus = _engagement_recency_bonus(cand)
        completeness_bonus = _profile_completeness_bonus(cand)

        cand.final_score = base_score + salary_bonus + engagement_bonus + completeness_bonus

