"""
config.py — Central configuration for the Redrob Ranking Engine.

All scoring weights, skill tier taxonomies, company classifications,
location tiers, phrase lists for NLP scanning, and honeypot thresholds.

Tunable: Modify weights here between submissions. No other file
needs to change to adjust scoring behavior.
"""

from __future__ import annotations

# ─── CURRENT YEAR (fixed for determinism) ──────────────────────────────────
CURRENT_YEAR: int = 2026

# ─── TECHNICAL SCORE WEIGHTS (must sum to 1.0) ─────────────────────────────
# These weights define how sub-scores contribute to the technical composite.
# Rationale drawn from job_description.docx — "shipper > researcher",
# production ML experience is the strongest signal.
TECHNICAL_WEIGHTS = {
    "career_nlp":    0.35,   # Production deployment evidence — strongest signal
    "skill_depth":   0.15,   # Tiered skill quality with corroboration
    "domain":        0.10,   # NLP/IR alignment vs other domains
    "exp_fit":       0.08,   # Experience band fit (5-9 ideal)
    "company_type":  0.12,   # Product company vs services
    "location":      0.05,   # Pune/Noida preferred
    "education":     0.03,   # Tier-1/2 mild bonus
    "recency":       0.07,   # Career recency (recent ML work)
    "platform_cred": 0.05,   # GitHub, assessments, profile completeness
}

# ─── BEHAVIORAL MULTIPLIER BANDS ──────────────────────────────────────────
# behavioral_score → multiplier applied to technical_score
BEHAVIORAL_MULTIPLIER_BANDS = [
    (0.70, 1.15),   # ≥ 0.70 → excellent: 15% boost
    (0.50, 1.00),   # 0.50–0.69 → neutral: no change
    (0.35, 0.85),   # 0.35–0.49 → mild penalty
    (0.20, 0.60),   # 0.20–0.34 → significant penalty
    (0.00, 0.35),   # < 0.20 → severe penalty
]

# ─── BEHAVIORAL SUB-SCORE WEIGHTS ─────────────────────────────────────────
BEHAVIORAL_WEIGHTS = {
    "availability": 0.40,
    "engagement":   0.35,
    "credibility":  0.25,
}

# ─── AVAILABILITY SUB-COMPONENTS ──────────────────────────────────────────
AVAILABILITY_WEIGHTS = {
    "recency":       0.40,   # Days since last_active_date
    "notice":        0.25,   # Notice period
    "open_to_work":  0.20,   # open_to_work_flag
    "relocate":      0.10,   # willing_to_relocate
    "work_mode":     0.05,   # preferred_work_mode
}

# ─── ENGAGEMENT SUB-COMPONENTS ────────────────────────────────────────────
ENGAGEMENT_WEIGHTS = {
    "response_rate": 0.40,   # recruiter_response_rate
    "interview_completion": 0.30,   # interview_completion_rate
    "response_time": 0.15,   # avg_response_time_hours
    "offer_acceptance": 0.10,  # offer_acceptance_rate
    "applications":  0.05,   # applications_submitted_30d
}

# ─── CREDIBILITY SUB-COMPONENTS ───────────────────────────────────────────
CREDIBILITY_WEIGHTS = {
    "github":        0.30,   # github_activity_score (0-100 scale)
    "assessments":   0.25,   # skill_assessment_scores mean
    "profile_comp":  0.20,   # profile_completeness_score
    "verification":  0.10,   # verified_email + verified_phone
    "endorsements":  0.10,   # endorsements_received
    "linkedin":      0.05,   # linkedin_connected
}

# ─── HARD BEHAVIORAL DISQUALIFIERS ───────────────────────────────────────
# If BOTH conditions are met, candidate is hard-disqualified (score = -1.0)
HARD_DISQUALIFY_RR_THRESHOLD = 0.10     # recruiter_response_rate
HARD_DISQUALIFY_ICR_THRESHOLD = 0.30    # interview_completion_rate


# ═══════════════════════════════════════════════════════════════════════════
# SKILL TIER TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════
# Derived from JD requirements + PRD skill taxonomy. Case-insensitive matching.
# Weight = base contribution to skill_depth_score per skill.

# Tier A (3.0) — Core JD requirements: embeddings, vector search, retrieval
TIER_A_SKILLS = {
    "faiss": 3.0,
    "pinecone": 3.0,
    "weaviate": 3.0,
    "qdrant": 3.0,
    "milvus": 3.0,
    "opensearch": 3.0,
    "elasticsearch": 3.0,
    "sentence-transformers": 3.0,
    "sentence transformers": 3.0,
    "bge": 3.0,
    "e5": 3.0,
    "colbert": 3.0,
    "dense retrieval": 3.0,
    "hybrid search": 3.0,
    "vector search": 3.0,
    "vector database": 3.0,
    "embedding": 3.0,
    "embeddings": 3.0,
    "bm25": 3.0,
    "information retrieval": 3.0,
    "learning to rank": 3.0,
    "re-ranking": 3.0,
    "reranking": 3.0,
    "ranking systems": 3.0,
    "search systems": 3.0,
    "ndcg": 3.0,
    "mrr": 3.0,
}

# Tier B (2.5) — Strong ML/AI skills, adjacent to JD core
TIER_B_SKILLS = {
    "pytorch": 2.5,
    "tensorflow": 2.5,
    "hugging face": 2.5,
    "huggingface": 2.5,
    "transformers": 2.5,
    "bert": 2.5,
    "gpt": 2.5,
    "llm": 2.5,
    "llms": 2.5,
    "large language models": 2.5,
    "fine-tuning": 2.5,
    "fine tuning": 2.5,
    "fine-tuning llms": 2.5,
    "lora": 2.5,
    "qlora": 2.5,
    "peft": 2.5,
    "rag": 2.5,
    "retrieval augmented generation": 2.5,
    "langchain": 2.5,
    "llamaindex": 2.5,
    "mlflow": 2.5,
    "weights & biases": 2.5,
    "wandb": 2.5,
    "a/b testing": 2.5,
    "recommendation systems": 2.5,
    "recommender systems": 2.5,
}

# Tier C (2.0) — General NLP/ML competence
TIER_C_SKILLS = {
    "nlp": 2.0,
    "natural language processing": 2.0,
    "text classification": 2.0,
    "named entity recognition": 2.0,
    "ner": 2.0,
    "sentiment analysis": 2.0,
    "text mining": 2.0,
    "topic modeling": 2.0,
    "word2vec": 2.0,
    "glove": 2.0,
    "spacy": 2.0,
    "nltk": 2.0,
    "machine learning": 2.0,
    "deep learning": 2.0,
    "neural networks": 2.0,
    "scikit-learn": 2.0,
    "sklearn": 2.0,
    "xgboost": 2.0,
    "lightgbm": 2.0,
    "catboost": 2.0,
    "keras": 2.0,
    "model evaluation": 2.0,
    "feature engineering": 2.0,
    "data science": 2.0,
    "statistical modeling": 2.0,
    "bentoml": 2.0,
    "triton": 2.0,
    "onnx": 2.0,
    "model serving": 2.0,
}

# Tier D (1.5) — Infrastructure/engineering skills
TIER_D_SKILLS = {
    "python": 1.5,
    "sql": 1.5,
    "docker": 1.5,
    "kubernetes": 1.5,
    "aws": 1.5,
    "gcp": 1.5,
    "azure": 1.5,
    "spark": 1.5,
    "pyspark": 1.5,
    "airflow": 1.5,
    "kafka": 1.5,
    "redis": 1.5,
    "postgresql": 1.5,
    "mongodb": 1.5,
    "git": 1.5,
    "linux": 1.5,
    "ci/cd": 1.5,
    "terraform": 1.5,
    "mlops": 1.5,
    "data pipelines": 1.5,
    "etl": 1.5,
    "data engineering": 1.5,
    "apache beam": 1.5,
    "dbt": 1.5,
    "snowflake": 1.5,
    "bigquery": 1.5,
    "flask": 1.5,
    "fastapi": 1.5,
    "django": 1.5,
    "rest api": 1.5,
}

# Tier E (0.5) — Generic/non-technical
TIER_E_SKILLS = {
    "project management": 0.5,
    "agile": 0.5,
    "scrum": 0.5,
    "jira": 0.5,
    "communication": 0.5,
    "leadership": 0.5,
    "teamwork": 0.5,
    "excel": 0.5,
    "powerpoint": 0.5,
    "tableau": 0.5,
    "power bi": 0.5,
    "react": 0.5,
    "javascript": 0.5,
    "typescript": 0.5,
    "html": 0.5,
    "css": 0.5,
    "node.js": 0.5,
    "java": 0.5,
    "c++": 0.5,
    "c#": 0.5,
    "go": 0.5,
    "rust": 0.5,
    "ruby": 0.5,
    "php": 0.5,
    "swift": 0.5,
    "kotlin": 0.5,
    "android": 0.5,
    "ios": 0.5,
    "photoshop": 0.5,
    "figma": 0.5,
    "tailwind": 0.5,
    "marketing": 0.5,
    "seo": 0.5,
    "content writing": 0.5,
}

# Negative skills (-2.0) — Wrong domain for NLP/IR role
NEGATIVE_SKILLS = {
    "opencv": -2.0,
    "yolo": -2.0,
    "yolov5": -2.0,
    "yolov8": -2.0,
    "image classification": -2.0,
    "object detection": -2.0,
    "image segmentation": -2.0,
    "computer vision": -2.0,
    "ros": -2.0,
    "ros2": -2.0,
    "robotics": -2.0,
    "slam": -2.0,
    "point cloud": -2.0,
    "speech recognition": -2.0,
    "speech synthesis": -2.0,
    "tts": -2.0,
    "asr": -2.0,
    "gans": -2.0,
    "generative adversarial": -2.0,
    "stable diffusion": -2.0,
    "image generation": -2.0,
    "3d modeling": -2.0,
}

# Negative skills cap: max 3 negative skills contribute
MAX_NEGATIVE_SKILLS = 3

# Anti-stuffing: penalize candidates listing >40 skills
SKILL_STUFFING_THRESHOLD = 40
SKILL_STUFFING_PENALTY_RATE = 0.005   # per skill above threshold
SKILL_STUFFING_PENALTY_FLOOR = 0.70   # minimum multiplier


def get_skill_tier_weight(skill_name: str) -> float:
    """Look up a skill name in the tier taxonomy. Returns weight or 0.0 for unknown."""
    key = skill_name.lower().strip()
    for tier_dict in (TIER_A_SKILLS, TIER_B_SKILLS, TIER_C_SKILLS,
                      TIER_D_SKILLS, TIER_E_SKILLS, NEGATIVE_SKILLS):
        if key in tier_dict:
            return tier_dict[key]
    return 0.0  # Unknown skill — no contribution


def get_skill_tier_name(skill_name: str) -> str:
    """Return tier letter (A/B/C/D/E/NEG/UNK) for a skill name."""
    key = skill_name.lower().strip()
    if key in TIER_A_SKILLS: return "A"
    if key in TIER_B_SKILLS: return "B"
    if key in TIER_C_SKILLS: return "C"
    if key in TIER_D_SKILLS: return "D"
    if key in TIER_E_SKILLS: return "E"
    if key in NEGATIVE_SKILLS: return "NEG"
    return "UNK"


# ═══════════════════════════════════════════════════════════════════════════
# PROFICIENCY MULTIPLIERS
# ═══════════════════════════════════════════════════════════════════════════
PROFICIENCY_MULTIPLIERS = {
    "beginner":     0.50,
    "intermediate": 0.75,
    "advanced":     1.00,
    "expert":       1.25,
}


# ═══════════════════════════════════════════════════════════════════════════
# DOMAIN CLUSTER KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════
# Used for domain classification from skills and career text.
# Each keyword maps to a domain cluster and casts 1 vote.

DOMAIN_KEYWORDS = {
    "NLP_IR": [
        "nlp", "natural language processing", "information retrieval",
        "text mining", "text classification", "named entity recognition",
        "sentiment analysis", "topic modeling", "word2vec", "glove",
        "bert", "gpt", "transformers", "hugging face", "huggingface",
        "spacy", "nltk", "retrieval", "ranking", "search",
        "embeddings", "embedding", "vector search", "hybrid search",
        "faiss", "pinecone", "weaviate", "qdrant", "milvus",
        "opensearch", "elasticsearch", "bm25", "dense retrieval",
        "sentence-transformers", "sentence transformers",
        "reranking", "re-ranking", "learning to rank",
        "rag", "retrieval augmented generation",
        "langchain", "llamaindex", "llm", "llms",
        "large language models", "fine-tuning", "fine tuning",
        "lora", "qlora", "peft",
        "recommendation systems", "recommender systems",
    ],
    "GENERAL_ML": [
        "machine learning", "deep learning", "neural networks",
        "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn",
        "xgboost", "lightgbm", "catboost",
        "data science", "feature engineering", "model evaluation",
        "statistical modeling", "mlflow", "mlops",
        "a/b testing", "weights & biases", "wandb",
    ],
    "DATA_ENG": [
        "data engineering", "data pipelines", "etl",
        "spark", "pyspark", "airflow", "kafka",
        "sql", "postgresql", "mongodb", "redis",
        "snowflake", "bigquery", "dbt", "apache beam",
        "data warehouse", "data lake",
    ],
    "CV": [
        "computer vision", "opencv", "yolo", "yolov5", "yolov8",
        "image classification", "object detection", "image segmentation",
        "gans", "generative adversarial", "stable diffusion",
        "image generation", "3d modeling",
    ],
    "SPEECH": [
        "speech recognition", "speech synthesis", "tts", "asr",
        "audio processing", "voice",
    ],
    "ROBOTICS": [
        "robotics", "ros", "ros2", "slam", "point cloud",
        "autonomous", "control systems",
    ],
}

# Domain scores — how much a primary domain aligns with the JD
DOMAIN_SCORES = {
    "NLP_IR":     1.00,
    "GENERAL_ML": 0.50,   # Bumped to 0.75 if also has NLP_IR signal
    "DATA_ENG":   0.40,   # Bumped to 0.60 if has production ML evidence
    "CV":         0.20,   # Bumped to 0.55 if also has NLP_IR signal (hybrid)
    "SPEECH":     0.20,   # Same as CV
    "ROBOTICS":   0.15,
    "NOT_TECH":   0.00,
}


# ═══════════════════════════════════════════════════════════════════════════
# COMPANY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

# Services companies (full blacklist from JD)
SERVICES_BLACKLIST = {
    "tcs", "tata consultancy services", "tata consultancy",
    "infosys",
    "wipro",
    "accenture",
    "cognizant", "cognizant technology solutions",
    "capgemini",
    "hcl", "hcl technologies",
    "tech mahindra",
    "mindtree",
    "mphasis",
    "l&t infotech", "lti", "ltimindtree",
    "hexaware",
    "persistent systems",
    "zensar",
    "cyient",
    "niit technologies",
    "coforge",
    "birlasoft",
    "sonata software",
}

# Known product companies (high-signal)
PRODUCT_COMPANIES = {
    # Big tech
    "google", "microsoft", "amazon", "meta", "apple", "netflix",
    "uber", "airbnb", "stripe", "spotify", "twitter", "x",
    "linkedin", "salesforce", "adobe", "nvidia", "intel",
    "openai", "anthropic", "cohere", "deepmind",
    # Indian product companies
    "flipkart", "swiggy", "zomato", "razorpay", "cred",
    "zerodha", "phonepe", "paytm", "ola", "meesho",
    "freshworks", "zoho", "postman", "browserstack",
    "dream11", "myntra", "nykaa", "urban company",
    "sharechat", "dailyhunt", "lenskart", "bigbasket",
    "udaan", "groww", "jupiter", "slice", "khatabook",
    "unacademy", "upgrad", "byju's", "byjus", "vedantu",
    "redrob",
}

# Industry signals for product classification fallback
PRODUCT_INDUSTRIES = {
    "technology", "software", "internet", "saas", "fintech",
    "e-commerce", "artificial intelligence", "machine learning",
    "data analytics",
}

# Services industries
SERVICES_INDUSTRIES = {
    "it services", "consulting", "outsourcing",
    "staffing", "bpo", "kpo",
    "information technology and services",
}

# Company type scoring weights (for weighted avg by duration)
COMPANY_TYPE_WEIGHTS = {
    "PRODUCT_STARTUP":    3.0,   # Small product co (1-200 employees)
    "PRODUCT_SCALEUP":    2.5,   # Mid product co (201-5000)
    "PRODUCT_ENTERPRISE": 2.0,   # Large product co (5001+)
    "SERVICES_ML":        1.2,   # Services but with ML role
    "UNKNOWN":            0.8,   # Can't classify
    "SERVICES_OTHER":     0.5,   # Services blacklist
}

ALL_SERVICES_HARD_CAP = 0.30  # If ALL career entries are services → cap score


# ═══════════════════════════════════════════════════════════════════════════
# LOCATION TIERS
# ═══════════════════════════════════════════════════════════════════════════

LOCATION_PREFERRED = {"pune", "noida"}     # Score: 1.0
LOCATION_ACCEPTABLE = {                     # Score: 0.9
    "hyderabad", "mumbai", "delhi", "delhi ncr",
    "gurgaon", "gurugram", "bangalore", "bengaluru",
    "chennai", "kolkata",
}
LOCATION_OTHER_INDIA_SCORE = 0.70
LOCATION_INTERNATIONAL_RELOCATE_SCORE = 0.50
LOCATION_INTERNATIONAL_NO_RELOCATE_SCORE = 0.20


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIENCE FIT — Piecewise Linear Scoring
# ═══════════════════════════════════════════════════════════════════════════
# JD: "5-9 years" with flexibility.
# y < 2:        0.00  (too junior to consider)
# 2 ≤ y < 3:    0.15
# 3 ≤ y < 5:    0.30 + 0.14 × (y - 3)   → ramps 0.30 to 0.58
# 5 ≤ y ≤ 9:    1.00  (sweet spot)
# 9 < y ≤ 12:   1.00 - 0.10 × (y - 9)   → declines 1.0 to 0.70
# 12 < y ≤ 15:  0.70 - 0.067 × (y - 12) → declines to ~0.50
# y > 15:       0.45  (over-qualified floor)

EXP_FIT_BANDS = [
    # (min_yoe, max_yoe, score_at_min, score_at_max)
    (0.0,   2.0,  0.00, 0.00),
    (2.0,   3.0,  0.15, 0.30),
    (3.0,   5.0,  0.30, 0.58),
    (5.0,   9.0,  1.00, 1.00),
    (9.0,  12.0,  1.00, 0.70),
    (12.0, 15.0,  0.70, 0.50),
    (15.0, 99.0,  0.45, 0.45),
]


def compute_exp_fit(yoe: float) -> float:
    """Piecewise linear experience fit score."""
    for lo, hi, s_lo, s_hi in EXP_FIT_BANDS:
        if lo <= yoe < hi:
            if hi == lo:
                return s_lo
            t = (yoe - lo) / (hi - lo)
            return s_lo + t * (s_hi - s_lo)
    return 0.45  # fallback for very high YOE


# ═══════════════════════════════════════════════════════════════════════════
# EDUCATION TIER BONUS
# ═══════════════════════════════════════════════════════════════════════════

EDUCATION_TIER_BONUS = {
    "tier_1":   0.05,    # IIT, IIIT, BITS, NIT top, IISc, etc.
    "tier_2":   0.02,    # Good state universities, NITs
    "tier_3":   0.00,    # Average
    "tier_4":  -0.02,    # Below average
    "unknown":  0.00,    # Can't classify
}


# ═══════════════════════════════════════════════════════════════════════════
# TITLE SENIORITY MAP (for title-chaser detection)
# ═══════════════════════════════════════════════════════════════════════════

TITLE_SENIORITY_MAP = {
    "intern":       0,
    "trainee":      0,
    "junior":       1,
    "associate":    1,
    "analyst":      2,
    "engineer":     2,
    "developer":    2,
    "scientist":    2,
    "designer":     2,
    "consultant":   2,
    "senior":       3,
    "lead":         4,
    "staff":        4,
    "principal":    5,
    "manager":      4,
    "director":     5,
    "vp":           6,
    "head":         5,
    "chief":        6,
    "cto":          6,
    "ceo":          6,
    "founder":      5,
    "co-founder":   5,
}

# Title-chaser thresholds
TITLE_CHASER_MIN_COMPANIES = 3          # Need at least 3 short stints
TITLE_CHASER_MAX_TENURE_MONTHS = 18     # Each stint ≤ 18 months
TITLE_CHASER_PENALTY = 0.20             # Multiplicative penalty


# ═══════════════════════════════════════════════════════════════════════════
# CAREER NLP — Phrase Lists for Aho-Corasick / Regex Scanning
# ═══════════════════════════════════════════════════════════════════════════

# Production/deployment phrases — strong positive signal
PRODUCTION_PHRASES = [
    "deployed", "deployment", "production", "shipped", "ship",
    "launched", "launch", "live system", "live traffic",
    "real-time", "realtime", "real time",
    "serving", "model serving", "inference",
    "latency", "throughput", "qps", "requests per second",
    "a/b test", "ab test", "a/b testing",
    "ml pipeline", "data pipeline", "feature pipeline",
    "scale", "scaled", "scaling", "at scale",
    "monitoring", "alerting", "observability",
    "sla", "uptime", "reliability",
    "api", "microservice", "endpoint",
    "containerized", "docker", "kubernetes",
    "ci/cd", "continuous integration", "continuous deployment",
    "etl", "batch processing", "stream processing",
    "millions of", "billions of",
    "user-facing", "customer-facing",
    "end-to-end", "e2e", "full-stack ml",
    "recommendation engine", "ranking system", "search system",
    "retrieval system", "matching system",
    "embedding pipeline", "vector index",
    "fine-tuned", "fine-tuning",
    "evaluation framework", "eval framework",
    "ndcg", "mrr", "map", "precision", "recall",
    "recruiter", "hiring", "talent",
]

# Research-only phrases — mild positive but not what JD wants
RESEARCH_PHRASES = [
    "published", "paper", "conference", "journal",
    "arxiv", "neurips", "icml", "acl", "emnlp", "iclr",
    "thesis", "dissertation", "phd",
    "benchmark", "benchmarked", "baseline",
    "state-of-the-art", "sota",
    "novel approach", "proposed method",
    "ablation study", "ablation",
    "theoretical", "proof",
    "kaggle", "competition",
]


# ═══════════════════════════════════════════════════════════════════════════
# HONEYPOT DETECTION THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════

HONEYPOT_CONFIDENCE_THRESHOLD = 0.60     # Flag if confidence ≥ this
HONEYPOT_MAX_RATE_TOP100 = 0.08          # Trigger rerank if > 8%
HONEYPOT_TARGET_RATE = 0.05              # Target after rerank

# Per-rule confidence contributions
HONEYPOT_RULES = {
    "HP01_SALARY_INVERSION":      0.80,
    "HP02_YOE_VS_CAREER_SPAN":    0.70,
    "HP03_OVERLAPPING_TENURES":   0.60,
    "HP04_EDU_VS_CAREER_START":   0.30,
    "HP05_YOUNG_CAREER_HIGH_YOE": 0.80,
    "HP06_IMPOSSIBLE_TENURE":     0.90,
    "HP07_PERFECT_ABANDONED":     0.40,
    "HP08_ALL_ASSESSMENTS_PERF":  0.50,
    "HP09_INSTANT_RESPONSE":      0.40,
    "HP10_FIXTURE_COMPANY":       0.10,
    "HP11_TECH_TIME_TRAVEL":      0.90,
    "HP12_EMPTY_EXPERTISE":       0.90,
    "HP14_SKILL_ADJACENCY":       0.15,
}

# HP13 is a behavioral penalty, not a honeypot confidence — stored separately
HP13_ARCHITECTURE_ASTRONAUT_PENALTY = 0.35

# Fixture company names (honeypot markers)
FIXTURE_COMPANIES = {
    "dunder mifflin", "initech", "hooli", "piedpiper", "pied piper",
    "acme corp", "acme", "globex", "cyberdyne", "umbrella corp",
    "umbrella corporation", "wayne enterprises", "stark industries",
    "wonka industries", "prestige worldwide", "vandelay industries",
}

# HP-07 thresholds
HP07_COMPLETENESS_THRESHOLD = 100.0
HP07_INACTIVE_DAYS = 1095               # 3 years

# HP-08 thresholds
HP08_SCORE_THRESHOLD = 90
HP08_MIN_ASSESSMENTS = 3

# HP-09 threshold
HP09_RESPONSE_TIME_THRESHOLD = 0.1      # hours

# HP-03 overlap threshold
HP03_OVERLAP_DAYS = 90


# ═══════════════════════════════════════════════════════════════════════════
# SYNONYM EXPANSION — O(1) "semantic" matching before Aho-Corasick/TF-IDF
# ═══════════════════════════════════════════════════════════════════════════
# Sorted by length descending at runtime for longest-match-first replacement.
SYNONYM_MAP = {
    "released to production": "deployed",
    "put into production": "deployed",
    "pushed to prod": "deployed",
    "went live": "deployed",
    "shipped": "deployed",
    "launched": "deployed",
    "aws instances": "cloud deployment",
    "gcp instances": "cloud deployment",
    "azure instances": "cloud deployment",
    "large language model": "llm",
    "large language models": "llm",
    "genai": "generative ai",
    "gen ai": "generative ai",
    "dl": "deep learning",
    "ir": "information retrieval",
    "recsys": "recommendation systems",
    "rec sys": "recommendation systems",
    "recommender system": "recommendation systems",
}

# Pre-sort by length descending for longest-match-first replacement
_SYNONYM_PAIRS = sorted(SYNONYM_MAP.items(), key=lambda x: len(x[0]), reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# TECHNOLOGY RELEASE YEARS — for HP11 Time-Travel Fraud Detection
# ═══════════════════════════════════════════════════════════════════════════
TECH_RELEASE_YEARS = {
    "llama": 2023, "llama 2": 2023, "llama2": 2023,
    "llama 3": 2024, "llama3": 2024,
    "mistral": 2023, "mixtral": 2023,
    "gemini": 2023, "gpt 4": 2023, "gpt4": 2023,
    "chatgpt": 2022, "stable diffusion": 2022,
    "qlora": 2023, "peft": 2022,
    "langchain": 2022, "llamaindex": 2022,
    "claude": 2023, "anthropic": 2023,
    "crew ai": 2024, "crewai": 2024,
    "autogen": 2023, "dspy": 2023,
    "bge": 2023,
}


# ═══════════════════════════════════════════════════════════════════════════
# SKILL ADJACENCY GRAPH — for HP14 Corroboration Check
# ═══════════════════════════════════════════════════════════════════════════
SKILL_ADJACENCY = {
    "faiss":       {"vector search", "embeddings", "pytorch", "ann", "similarity search", "numpy"},
    "pinecone":    {"vector search", "embeddings", "vector database", "retrieval", "dense retrieval"},
    "weaviate":    {"vector search", "embeddings", "semantic search", "vector database"},
    "qdrant":      {"vector search", "embeddings", "similarity search", "vector database"},
    "milvus":      {"vector search", "embeddings", "ann", "vector database"},
    "sentence-transformers": {"embeddings", "pytorch", "transformers", "bert", "huggingface"},
    "sentence transformers": {"embeddings", "pytorch", "transformers", "bert", "huggingface"},
    "colbert":     {"retrieval", "ranking", "embeddings", "reranking", "information retrieval"},
    "ndcg":        {"ranking", "information retrieval", "mrr", "learning to rank"},
}


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE WEIGHTS — for source-aware NLP evidence weighting
# ═══════════════════════════════════════════════════════════════════════════
SOURCE_WEIGHTS = {
    "career_descriptions": 1.00,   # Strongest proof — they describe what they built
    "current_title":       0.85,   # Important but not sufficient
    "headline":            0.45,   # Helpful, self-written
    "summary":             0.45,   # Same
    "skill_names":         0.25,   # Weakest — just labels, not evidence
}


# ═══════════════════════════════════════════════════════════════════════════
# NOTICE PERIOD SCORING
# ═══════════════════════════════════════════════════════════════════════════

def compute_notice_score(days: int) -> float:
    """Score notice period — JD prefers sub-30-day."""
    if days <= 0:
        return 1.0
    elif days <= 30:
        return 0.95
    elif days <= 60:
        return 0.75
    elif days <= 90:
        return 0.50
    elif days <= 120:
        return 0.30
    else:
        return 0.15


# ═══════════════════════════════════════════════════════════════════════════
# WORK MODE SCORING
# ═══════════════════════════════════════════════════════════════════════════

WORK_MODE_SCORES = {
    "onsite":   1.0,
    "hybrid":   1.0,
    "flexible": 1.0,
    "remote":   0.7,
}


# ═══════════════════════════════════════════════════════════════════════════
# RECENCY SCORING (days since last active)
# ═══════════════════════════════════════════════════════════════════════════

def compute_recency_score(days_since_active: int) -> float:
    """Score recency of platform activity."""
    if days_since_active <= 7:
        return 1.0
    elif days_since_active <= 30:
        return 0.90
    elif days_since_active <= 90:
        return 0.70
    elif days_since_active <= 180:
        return 0.40
    elif days_since_active <= 365:
        return 0.20
    else:
        return 0.10


# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE TIME SCORING
# ═══════════════════════════════════════════════════════════════════════════

def compute_response_time_score(hours: float) -> float:
    """Score average response time to recruiter messages."""
    if hours <= 1.0:
        return 1.0
    elif hours <= 4.0:
        return 0.90
    elif hours <= 12.0:
        return 0.75
    elif hours <= 24.0:
        return 0.60
    elif hours <= 72.0:
        return 0.40
    elif hours <= 168.0:  # 1 week
        return 0.20
    else:
        return 0.10


# ═══════════════════════════════════════════════════════════════════════════
# GITHUB ACTIVITY SCORING (0-100 scale in data)
# ═══════════════════════════════════════════════════════════════════════════

def compute_github_score(score: float) -> float:
    """Score github_activity_score. -1 = no GitHub linked."""
    if score < 0:
        return 0.0   # No GitHub — neutral, not penalty
    elif score >= 50:
        return 1.0
    elif score >= 30:
        return 0.75
    elif score >= 10:
        return 0.50
    elif score > 0:
        return 0.25
    else:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# COMPANY SIZE PARSING
# ═══════════════════════════════════════════════════════════════════════════

COMPANY_SIZE_MIDPOINTS = {
    "1-10":       5,
    "11-50":      30,
    "51-200":     125,
    "201-500":    350,
    "501-1000":   750,
    "1001-5000":  3000,
    "5001-10000": 7500,
    "10001+":     15000,
}


def parse_company_size(size_str: str) -> int:
    """Parse company size string enum to integer midpoint."""
    return COMPANY_SIZE_MIDPOINTS.get(size_str, 500)  # default mid


# ═══════════════════════════════════════════════════════════════════════════
# TEMPORAL DECAY
# ═══════════════════════════════════════════════════════════════════════════
import math

TEMPORAL_DECAY_RATE = 0.1   # exp(-0.1 × years_ago)


def temporal_decay(years_ago: float) -> float:
    """Exponential decay for career entry age."""
    return math.exp(-TEMPORAL_DECAY_RATE * max(0.0, years_ago))
