import copy
from datetime import date

def get_base_candidate() -> dict:
    """
    Returns a base valid candidate dict representing a high-scoring Senior AI Engineer.
    Matches the parsing schema in src/models.py and scores highly under config.py.
    """
    return {
        "candidate_id": "CAND_0000001",
        "profile": {
            "anonymized_name": "John Doe",
            "headline": "Senior AI Engineer | Vector Search & NLP Expert",
            "summary": "Experienced AI Engineer specializing in building scalable search systems, vector database indexing, and deploying sentence-transformers in production environments.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Senior AI Engineer",
            "current_company": "Razorpay",
            "current_company_size": "1001-5000",
            "current_industry": "software"
        },
        "redrob_signals": {
            "profile_completeness_score": 95.0,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-05-25",
            "open_to_work_flag": True,
            "profile_views_received_30d": 120,
            "applications_submitted_30d": 4,
            "recruiter_response_rate": 0.85,
            "avg_response_time_hours": 0.5,
            "skill_assessment_scores": {
                "Python": 88,
                "Machine Learning": 85
            },
            "connection_count": 450,
            "endorsements_received": 35,
            "notice_period_days": 15,
            "expected_salary_range_inr_lpa": {
                "min": 30.0,
                "max": 45.0
            },
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 75.0,
            "search_appearance_30d": 90,
            "saved_by_recruiters_30d": 12,
            "interview_completion_rate": 0.90,
            "offer_acceptance_rate": 0.80,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True
        },
        "career_history": [
            {
                "company": "Flipkart",
                "title": "AI Engineer",
                "start_date": "2019-06-01",
                "end_date": "2022-05-31",
                "duration_months": 36,
                "is_current": False,
                "industry": "e-commerce",
                "company_size": "5001-10000",
                "description": "Developed and deployed vector search systems using FAISS and Pinecone. Fine-tuned sentence-transformers for product embeddings, improving search precision and latency at scale."
            },
            {
                "company": "Razorpay",
                "title": "Senior AI Engineer",
                "start_date": "2022-06-01",
                "end_date": None,
                "duration_months": 48,
                "is_current": True,
                "industry": "fintech",
                "company_size": "1001-5000",
                "description": "Led team of ML engineers to ship retrieval augmented generation (RAG) microservices. Managed model serving and API performance, maintaining high reliability and throughput for LLM inference pipelines."
            }
        ],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field_of_study": "Computer Science and Engineering",
                "start_year": 2015,
                "end_year": 2019,
                "grade": "8.5 CGPA",
                "tier": "tier_1"
            }
        ],
        "skills": [
            {
                "name": "FAISS",
                "proficiency": "expert",
                "endorsements": 25,
                "duration_months": 48
            },
            {
                "name": "Pinecone",
                "proficiency": "expert",
                "endorsements": 20,
                "duration_months": 48
            },
            {
                "name": "vector search",
                "proficiency": "expert",
                "endorsements": 30,
                "duration_months": 48
            },
            {
                "name": "PyTorch",
                "proficiency": "expert",
                "endorsements": 40,
                "duration_months": 72
            },
            {
                "name": "LLM",
                "proficiency": "expert",
                "endorsements": 15,
                "duration_months": 36
            },
            {
                "name": "Python",
                "proficiency": "expert",
                "endorsements": 50,
                "duration_months": 84
            }
        ]
    }

def create_candidate(candidate_id: str = "CAND_0000001", **overrides) -> dict:
    """
    Creates a candidate dict by taking the base candidate template and applying overrides.
    Supports nested dictionary overrides (e.g. profile, redrob_signals).
    """
    cand = copy.deepcopy(get_base_candidate())
    cand["candidate_id"] = candidate_id
    
    for key, value in overrides.items():
        if key in cand and isinstance(cand[key], dict) and isinstance(value, dict):
            # Shallow merge for one level of nesting (e.g. profile, redrob_signals)
            cand[key].update(value)
        else:
            cand[key] = value
            
    return cand
