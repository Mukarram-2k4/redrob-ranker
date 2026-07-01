# Redrob Candidate Ranking Engine

**Team ForgeScaler** — India Runs Data & AI Challenge

A high-performance, hybrid semantic retrieval and Reciprocal Rank Fusion (RRF) candidate ranking system that ranks the top 100 candidates from a 100K-candidate pool for a Senior AI Engineer role. Runs in ~58 seconds on CPU with no GPU or network access.

## Reproduce Command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

That's it. One command, no pre-computation required.

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/Mukarram-2k4/redrob-ranker.git
cd redrob-ranker

# 2. Install dependencies (minimal — numpy, pyyaml, pyahocorasick)
pip install -r requirements.txt

# 3. Place candidates.jsonl in the project directory (or pass full path)
# File: ~465 MB plain-text JSONL, one candidate per line

# 4. Run
python rank.py --candidates ./candidates.jsonl --out ./submission.csv --profile
```

## Requirements

- Python 3.9+
- numpy
- pyyaml
- pyahocorasick (optional — falls back to regex automatically if unavailable)
- streamlit (for the sandbox dashboard only)

See `requirements.txt` for pinned versions.

## Sandbox / Demo

Interactive Streamlit dashboard with 5 tabs (Section 10.5 sandbox requirement):

```bash
streamlit run dashboard.py
```

| Tab | Features |
|-----|----------|
| 🚀 Run Engine | Demo dataset (50 curated top candidates) or upload JSONL/JSON |
| 📊 Results | Ranked candidates with per-stage timing, feature breakdowns, downloadable CSV |
| ❓ Ask the Engine | Lookup candidates, compare two side-by-side, filter by criteria, scoring explainer |
| 📈 Analytics | Score distribution, top-10 vs rest averages, company/location breakdown, honeypot summary |
| 🏗️ Architecture | Full pipeline docs, anti-gaming strategy, skill tiers, honeypot rules |

The demo dataset (`demo_candidates.jsonl`) contains real top-ranked candidates extracted from the 100K pipeline run — not the organizer's format-validation sample.

**Live Sandbox**: [Streamlit Cloud](https://robust-hybrid-redrob-ranker.streamlit.app/)

The pipeline runs 9 stages in sequence:

```
candidates.jsonl (100K profiles, ~465 MB)
        │
        ▼ Stage 0: Bootstrap (0.03s)
   Compile Aho-Corasick automaton from 80+ production/research NLP phrases
   (falls back to compiled regex if pyahocorasick unavailable)

        ▼ Stage 1: Ingestion (10.00s)
   Stream-parse JSONL line-by-line → 100,000 typed Candidate dataclasses
   Coerces types, handles malformed records gracefully

        ▼ Stage 2: Early Elimination (0.75s)
   Filters candidates with: YOE < 2, zero tech skills, or honeypot
   confidence ≥ 0.6 from HP01 (salary inversion), HP02 (YOE vs career span),
   HP05 (young career / high YOE), HP06 (impossible tenure)
   → 30,927 survivors (69,073 eliminated)

        ▼ Stage 3a: Behavioral Features (0.13s)
   Availability: recency, notice period, open-to-work, relocation, work mode
   Engagement: response rate, interview completion, response time, applications
   Credibility: GitHub activity, assessments, profile completeness, verification

        ▼ Stage 3b: Tabular Features (0.53s)
   Experience fit (5-9yr sweet spot), company type (product vs services),
   location (Pune/Noida preferred), title relevance (ML/NLP titles vs non-ML),
   education tier bonus, title-chaser penalty

        ▼ Stage 3c: Semantic Features (21.76s)
   Career NLP: Aho-Corasick scan for production phrases with temporal decay
   Skill depth: tier-weighted × proficiency × anti-stuffing penalty
   Domain: NLP_IR / GENERAL_ML / CV / SPEECH / DATA_ENG / NOT_TECH

        ▼ Stage 3d: TF-IDF Semantic Layer (19.68s)
   Build TF-IDF Vectorizer of Job Description and Candidate career details
   Compute local Cosine Similarity scores for plain-language matches

        ▼ Stage 4: Honeypot Full Pass (4.52s)
   HP03 (overlapping tenures), HP04 (edu vs career start),
   HP07 (perfect + abandoned), HP08 (all assessments perfect),
   HP09 (instant response), HP10 (fixture company names),
   HP11 (tech time-travel), HP12 (empty expertise),
   HP14 (skill adjacency corroboration)

        ▼ Stage 5: Scoring (0.55s)
   Map sub-scores to standard 1-based ranks.
   Fuse RRF ranks across 5 dimensions: Technical, Trajectory, Behavioral, Trust, and Semantic.
   Apply post-RRF trust multipliers, title-chaser, and architecture astronaut (HP13) penalties.

        ▼ Stage 6: Top-100 Selection (0.04s)
   Sort by fused RRF score → search_appearance_30d → saved_by_recruiters_30d → candidate_id
   Honeypot guardrail: if rate > 8% in top 100, swap excess honeypots with next-best clean survivors.

        ▼ Stage 7: Output (0.00s)
   Per-candidate reasoning referencing specific profile facts
   Score normalization with guaranteed unique scores per rank
   Tie-break by candidate_id ascending
```

### Reciprocal Rank Fusion (RRF) scoring model

Fuses 5 distinct dimensions of candidate quality using Reciprocal Rank Fusion (RRF):
1. **Dimension 1: Technical Score** (Career NLP scan, skill depth, domain score, YOE fit, company type, recency, platform credibility)
2. **Dimension 2: Career Trajectory** (Title seniority alignment + pedigree + location + education)
3. **Dimension 3: Behavioral Score** (Availability, engagement, and platform credibility)
4. **Dimension 4: Trust Score** (Inversion of active honeypot rules confidence score)
5. **Dimension 5: Semantic TF-IDF Similarity Score** (Cosine similarity mapping of candidate profile details against the JD)

```
RRF_score(d) = Σ_i  w_i / (60 + rank_i(d))
```
Where weights are `w = [1.6, 1.2, 0.8, 0.8, 1.0]`.

Post-RRF, we apply multiplicative penalties for title-chasing, architecture astronauts (HP13), and trust multipliers, then add micro-bonuses (salary alignment, engagement, completeness) for fine-grained tie breaking.

### Key Design Decisions

**Why title_relevance?**
The JD explicitly warns: *"The right answer is NOT find candidates whose skills section contains the most AI keywords."* Candidates with Frontend Engineer, .NET Developer, or Cloud Engineer titles who keyword-stuff their skills section score 0.25× on title relevance — regardless of skills listed.

**Why temporal decay on career NLP?**
A production ML deployment from 2019 is weaker evidence than the same from 2024. We apply exponential decay to each career entry's NLP signal based on how many years ago it ended.

**Why ~69K eliminated in Stage 2?**
The synthetic dataset has high base rates of HP01 (salary inversion) and HP06 (impossible tenure) signals. Our 0.6 confidence threshold is intentionally conservative to avoid false positives.

**No API dependencies, no network, no GPU**
The system is entirely self-contained, running on pure Python using numpy and scikit-learn. No external API calls are executed during ranking, which satisfies the compute constraints and can be reproduced exactly.

## Performance

```
Stage 0: Bootstrap               0.03s
Stage 1: Ingestion              10.00s  █████
Stage 2: Early Elimination       0.75s
Stage 3a: Behavioral Features    0.13s
Stage 3b: Tabular Features       0.53s
Stage 3c: Semantic Features     21.76s  ███████████
Stage 3d: TF-IDF Semantic Layer 19.68s  ██████████
Stage 4: Honeypot Full Pass      4.52s  ██
Stage 5: Scoring                 0.55s
Stage 6: Top-100 + Guardrails    0.04s
Stage 7: Output                  0.00s
─────────────────────────────────────
TOTAL                           57.99s  (budget: 300s)
```

## Compute Constraints Compliance

| Constraint | Limit | Actual |
|-----------|-------|--------|
| Runtime | ≤ 5 min | ~58s ✅ |
| Memory | ≤ 16 GB | ~2-3 GB ✅ |
| Compute | CPU only | Pure Python ✅ |
| Network | None | No API calls ✅ |
| GPU | None | Not used ✅ |

## File Structure

```
redrob-ranker/
├── rank.py                   # CLI entry point + stage orchestrator
├── requirements.txt          # numpy, pyyaml, pyahocorasick, streamlit
├── submission_metadata.yaml  # Portal metadata (filled)
├── README.md                 # This file
├── dashboard.py              # Streamlit sandbox dashboard
├── src/
│   ├── config.py
│   ├── models.py
│   ├── ingest.py
│   ├── filters.py
│   ├── features.py
│   ├── scorer.py
│   ├── output.py
│   ├── dimensions.py         # RRF algorithm implementation
│   └── semantic.py           # TF-IDF scoring layer
├── eval/                     # Evaluation scripts for NDCG metrics
│   ├── gold_labeler.py
│   └── run_eval.py
└── tests/
    ├── candidate_templates.py
    ├── run_e2e_tests.py
    ├── stress_test_filters.py
    └── stress_test_ingest.py
```

## Validation

After running, validate locally:

```bash
python validate_submission.py submission.csv
# Expected output: Submission is valid.
```

## License

MIT
