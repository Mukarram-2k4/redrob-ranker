# Redrob Candidate Ranking Engine

**Team ForgeScaler** — India Runs Data & AI Challenge

A high-performance, rule-based + feature-weighted candidate ranking system that ranks the top 100 candidates from a 100K-candidate pool for a Senior AI Engineer role. Runs in ~27 seconds on CPU with no GPU or network access.

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

## Architecture

The pipeline runs 8 stages in sequence:

```
candidates.jsonl (100K profiles, ~465 MB)
        │
        ▼ Stage 0: Bootstrap (0.05s)
   Compile Aho-Corasick automaton from 80+ production/research NLP phrases
   (falls back to compiled regex if pyahocorasick unavailable)

        ▼ Stage 1: Ingestion (17s)
   Stream-parse JSONL line-by-line → 100,000 typed Candidate dataclasses
   Coerces types, handles malformed records gracefully

        ▼ Stage 2: Early Elimination (1s)
   Filters candidates with: YOE < 2, zero tech skills, or honeypot
   confidence ≥ 0.6 from HP01 (salary inversion), HP02 (YOE vs career span),
   HP05 (young career / high YOE), HP06 (impossible tenure)
   → 30,927 survivors (69,073 eliminated)

        ▼ Stage 3a: Behavioral Features (0.2s)
   Availability: recency, notice period, open-to-work, relocation, work mode
   Engagement: response rate, interview completion, response time, applications
   Credibility: GitHub activity, assessments, profile completeness, verification

        ▼ Stage 3b: Tabular Features (0.9s)
   Experience fit (5-9yr sweet spot), company type (product vs services),
   location (Pune/Noida preferred), title relevance (ML/NLP titles vs non-ML),
   education tier bonus, title-chaser penalty

        ▼ Stage 3c: Semantic Features (21s)
   Career NLP: Aho-Corasick scan for production phrases with temporal decay
   Skill depth: tier-weighted × proficiency × anti-stuffing penalty
   Domain: NLP_IR / GENERAL_ML / CV / SPEECH / DATA_ENG / NOT_TECH

        ▼ Stage 4: Honeypot Full Pass (0.3s)
   HP03 (overlapping tenures), HP04 (edu vs career start),
   HP07 (perfect + abandoned), HP08 (all assessments perfect),
   HP09 (instant response), HP10 (fixture company names)

        ▼ Stage 5: Scoring (0.1s)
   final_score = technical_score × title_relevance × behavioral_multiplier
                 + edu_bonus + micro_bonuses (salary, engagement, completeness)

        ▼ Stage 6: Top-100 Selection (0.1s)
   Sort by score → search_appearance_30d → saved_by_recruiters_30d → candidate_id
   Honeypot guardrail: if rate > 8%, replace with next-best clean candidates

        ▼ Stage 7: Output (0.01s)
   Per-candidate reasoning referencing specific profile facts
   Score normalization with guaranteed unique scores per rank
   Tie-break by candidate_id ascending
```

### Scoring Formula

```
technical_score = (
    0.35 × career_nlp_score      # Production evidence in career text
  + 0.15 × skill_depth_score     # Tier-weighted skills (Tier A=3.0 … Tier E=0.5, NEG=-2.0)
  + 0.10 × domain_score          # NLP/IR alignment
  + 0.08 × exp_fit_score         # 5-9 year sweet spot
  + 0.12 × company_type_score    # Product vs services background
  + 0.05 × location_score        # Pune/Noida proximity
  + 0.07 × recency_score         # Platform activity
  + 0.05 × platform_cred_score   # GitHub, assessments, verifications
)

final_score = technical_score
            × (1 - title_chaser_penalty)   # ≥3 short stints penalty
            × title_relevance              # Non-ML titles scored 0.25×
            × behavioral_multiplier        # 0.35–1.15× based on signals
            + edu_bonus                    # Tier-1 institution bonus
            + salary_alignment_bonus       # 15-40 LPA sweet spot
            + engagement_recency_bonus     # Platform activity signal
            + profile_completeness_bonus   # Completeness micro-bonus
```

### Key Design Decisions

**Why title_relevance?**
The JD explicitly warns: *"The right answer is NOT find candidates whose skills section contains the most AI keywords."* Candidates with Frontend Engineer, .NET Developer, or Cloud Engineer titles who keyword-stuff their skills section score 0.25× on title relevance — regardless of skills listed.

**Why temporal decay on career NLP?**
A production ML deployment from 2019 is weaker evidence than the same from 2024. We apply exponential decay to each career entry's NLP signal based on how many years ago it ended.

**Why ~69K eliminated in Stage 2?**
The synthetic dataset has high base rates of HP01 (salary inversion) and HP06 (impossible tenure) signals. Our 0.6 confidence threshold is intentionally conservative to avoid false positives.

**No LLM calls, no embeddings, no GPU**
The system is entirely rule-based + feature-weighted, running on pure Python with numpy. No API calls, no model inference. This satisfies the compute constraints and can be reproduced exactly in any environment.

## Performance

```
Stage 0: Bootstrap               0.03s
Stage 1: Ingestion              10.46s  ███████████
Stage 2: Early Elimination       0.84s
Stage 3a: Behavioral Features    0.13s
Stage 3b: Tabular Features       0.57s
Stage 3c: Semantic Features     14.26s  ████████████████
Stage 4: Honeypot Full Pass      0.19s
Stage 5: Scoring                 0.09s
Stage 6: Top-100 + Guardrails    0.04s
Stage 7: Output                  0.00s
─────────────────────────────────────
TOTAL                           26.62s  (budget: 300s)
```

## Compute Constraints Compliance

| Constraint | Limit | Actual |
|-----------|-------|--------|
| Runtime | ≤ 5 min | ~27s ✅ |
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
├── submission.csv            # Reference output (validated)
├── LICENSE                   # MIT
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── config.py             # All weights, skill tiers, phrase lists, utilities
│   ├── models.py             # Candidate dataclasses + parse_candidate()
│   ├── ingest.py             # build_lookups() + load_candidates()
│   ├── filters.py            # early_eliminate() + honeypot_full_pass()
│   ├── features.py           # compute_behavioral/tabular/semantic_features()
│   ├── scorer.py             # compute_scores() with micro-bonuses
│   └── output.py             # select_top_100() + write_submission_csv()
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
