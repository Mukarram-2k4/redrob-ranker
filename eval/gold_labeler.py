"""
gold_labeler.py — Independent gold labeler and NDCG evaluator.

Defines a 5-tier relevance scale to assess candidate quality objectively,
independently from the ranking engine's weights and scores:
- 4: Textbook (sweet-spot YOE, Pune/Noida, product background, core skills, no flags)
- 3: Strong (acceptable YOE, acceptable location, vector search or NLP, no flags)
- 2: Gem (service background or junior, but possesses strong vector search skills)
- 1: Weak (general SWE with minimal NLP/ML evidence or international location)
- 0: Irrelevant/Disqualified (eliminated early, hard disqualified, or honeypot)
"""

import math
from src.models import Candidate
from src.config import get_skill_tier_name, LOCATION_PREFERRED, LOCATION_ACCEPTABLE


def label_candidate(cand: Candidate) -> int:
    """
    Independently assign a gold relevance score [0, 4] to a candidate.
    """
    # 0. Disqualified, honeypot, or too junior
    if cand.hard_disqualify or cand.honeypot_flag or cand.years_of_experience < 2.0:
        return 0

    yoe = cand.years_of_experience
    loc = cand.location.lower().strip()

    # Extract skill checks
    skills_set = {s.name.lower().strip() for s in cand.skills}
    has_vector_search = any(
        s in skills_set
        for s in ["faiss", "pinecone", "weaviate", "qdrant", "milvus", "vector search"]
    )
    has_nlp = any(get_skill_tier_name(s.name) in {"A", "B"} for s in cand.skills)
    has_python = "python" in skills_set

    # Check product company background
    # Classified as product startup, scaleup, or enterprise
    comp_score = cand.features.get("company_type_score", 0.0)
    is_product = comp_score >= 0.5  # Startup/Scaleup/Enterprise weights are >= 2.0 before normalization, so >= 0.666 normalized

    # 4: Textbook Match
    if (
        5.0 <= yoe <= 9.0
        and loc in LOCATION_PREFERRED
        and is_product
        and has_vector_search
        and has_python
    ):
        return 4

    # 3: Strong Match
    if (
        3.0 <= yoe <= 12.0
        and (loc in LOCATION_PREFERRED or loc in LOCATION_ACCEPTABLE)
        and (has_vector_search or has_nlp)
    ):
        return 3

    # 2: Gem (e.g. strong vector search developer despite service company or slightly lower YOE)
    if has_vector_search and yoe >= 2.0:
        return 2

    # 1: Weak Match
    if has_python or has_nlp or yoe >= 2.0:
        return 1

    return 0


def compute_ndcg(ranked_labels: list[int], k: int) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at k (NDCG@k).
    """
    if not ranked_labels:
        return 0.0

    actual_labels = ranked_labels[:k]

    # DCG@k
    dcg = 0.0
    for i, label in enumerate(actual_labels):
        dcg += (2**label - 1) / math.log2(i + 2)

    # IDCG@k (Ideal DCG)
    ideal_labels = sorted(ranked_labels, reverse=True)[:k]
    idcg = 0.0
    for i, label in enumerate(ideal_labels):
        idcg += (2**label - 1) / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg
