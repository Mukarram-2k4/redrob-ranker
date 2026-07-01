"""
semantic.py — TF-IDF Semantic Similarity Layer (Dimension 5).

Uses scikit-learn TfidfVectorizer to compute cosine similarity between
a synthetic JD query and all candidate profile text. This catches
"plain-language gems" who describe real work differently than our
Aho-Corasick keyword list.

Pure math (tf-idf + cosine). No neural network, no API, no model download.
Runs ~3s on 30K candidates.
"""

from __future__ import annotations
from typing import Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from src.models import Candidate
from src.ingest import normalize_text


# ═══════════════════════════════════════════════════════════════════════════
# JD QUERY CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def _build_jd_query() -> str:
    """
    Construct a synthetic JD query document.
    
    Core concepts are repeated 3x to boost their TF weight — this is
    standard IR practice for query expansion. The JD says "Senior AI
    Engineer" for a search/ranking team, so we weight those concepts.
    """
    core = (
        "machine learning deep learning nlp natural language processing "
        "information retrieval search ranking recommendation "
        "vector search embeddings deployed production serving "
        "pytorch tensorflow model training inference "
        "transformer bert llm fine tuning "
    )
    secondary = (
        "python numpy faiss pinecone qdrant "
        "mlops kubernetes docker aws gcp "
        "data pipeline feature engineering "
        "a/b testing experiment evaluation ndcg mrr "
        "system design microservices api "
    )
    return (core * 3 + secondary).strip()


# ═══════════════════════════════════════════════════════════════════════════
# CANDIDATE DOCUMENT CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def _build_candidate_document(cand: Candidate) -> str:
    """
    Build a single text document from a candidate's profile for TF-IDF.
    Concatenates career descriptions, titles, headline, summary, and skill names.
    All normalized for consistent matching.
    """
    parts = []
    
    # Career descriptions + titles (most important signals)
    for entry in cand.career_history:
        parts.append(normalize_text(entry.description))
        parts.append(normalize_text(entry.title))
    
    # Headline and summary
    if cand.headline:
        parts.append(normalize_text(cand.headline))
    if cand.summary:
        parts.append(normalize_text(cand.summary))
    
    # Skill names
    skill_text = " ".join(s.name for s in cand.skills)
    parts.append(normalize_text(skill_text))
    
    # Current title (boost)
    if cand.current_title:
        parts.append(normalize_text(cand.current_title))
    
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# BATCH TF-IDF COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_tfidf_scores(survivors: list[Candidate]) -> dict[str, float]:
    """
    Compute TF-IDF cosine similarity between JD query and each candidate.
    
    Returns {candidate_id: similarity_score} where score is in [0.0, 1.0].
    Falls back to empty dict if scikit-learn is not installed.
    """
    if not HAS_SKLEARN:
        print("    [WARN] scikit-learn not installed, skipping TF-IDF")
        return {}
    
    if not survivors:
        return {}
    
    # Build documents: JD query (index 0) + candidate docs (index 1..N)
    jd_query = _build_jd_query()
    candidate_docs = []
    candidate_ids = []
    
    for cand in survivors:
        doc = _build_candidate_document(cand)
        candidate_docs.append(doc)
        candidate_ids.append(cand.candidate_id)
    
    all_docs = [jd_query] + candidate_docs
    
    # Fit TF-IDF vectorizer
    min_df_val = 2 if len(all_docs) >= 5 else 1
    max_df_val = 0.95 if len(all_docs) >= 5 else 1.0
    
    vectorizer = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=min_df_val,
        max_df=max_df_val,
        strip_accents="unicode",
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(all_docs)
    except ValueError:
        # Fallback to no pruning if vocabulary becomes empty
        vectorizer = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            max_df=1.0,
            strip_accents="unicode",
        )
        tfidf_matrix = vectorizer.fit_transform(all_docs)
    
    # Compute cosine similarity between JD (row 0) and all candidates (rows 1..N)
    jd_vector = tfidf_matrix[0:1]
    candidate_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(jd_vector, candidate_vectors).flatten()
    
    # Build result dict
    scores = {}
    for cid, sim in zip(candidate_ids, similarities):
        scores[cid] = float(max(0.0, min(1.0, sim)))
    
    return scores
