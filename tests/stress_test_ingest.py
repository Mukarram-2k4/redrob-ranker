import os
import sys
import json
import time
import gc
import traceback
from datetime import date

# Ensure src is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingest import load_candidates, build_lookups
from src.models import Candidate

# Try to import psutil for memory measurement
try:
    import psutil
    def get_memory_usage_mb():
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
except ImportError:
    # Fallback for Windows using ctypes if psutil is not available
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t),
                ('PrivateUsage', ctypes.c_size_t),
            ]

        def get_memory_usage_mb():
            GetProcessMemoryCounters = ctypes.windll.psapi.GetProcessMemoryCounters
            GetStdHandle = ctypes.windll.kernel32.GetStdHandle
            GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
            
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            
            if GetProcessMemoryCounters(GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize / (1024 * 1024)
            return 0.0
    except Exception:
        def get_memory_usage_mb():
            return 0.0

def create_temp_file(filename, lines):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return path

def delete_temp_file(path):
    if os.path.exists(path):
        os.remove(path)

# Base template for candidate
BASE_CANDIDATE = {
    "candidate_id": "CAND_0000001",
    "profile": {
        "anonymized_name": "John Doe",
        "headline": "Senior AI Engineer | Vector Search & NLP Expert",
        "summary": "Experienced AI Engineer specializing in building scalable search systems.",
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
            "description": "Developed and deployed vector search systems using FAISS."
        }
    ],
    "education": [
        {
            "institution": "IIT Bombay",
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": 2015,
            "end_year": 2019,
            "grade": "8.5 CGPA",
            "tier": "tier_1"
        }
    ],
    "skills": [
        {
            "name": "Python",
            "proficiency": "expert",
            "endorsements": 50,
            "duration_months": 84
        }
    ]
}

def run_test_case(name, lines):
    print(f"--- Running Test Case: {name} ---")
    path = create_temp_file(f"temp_{name}.jsonl", lines)
    
    gc.collect()
    mem_before = get_memory_usage_mb()
    t_start = time.perf_counter()
    
    candidates = []
    error = None
    try:
        candidates = load_candidates(path)
        success = True
    except Exception as e:
        success = False
        error = e
        traceback.print_exc()
        
    t_end = time.perf_counter()
    mem_after = get_memory_usage_mb()
    
    delete_temp_file(path)
    
    print(f"Success: {success}")
    if success:
        print(f"Parsed {len(candidates)} candidates.")
        if candidates:
            print(f"First candidate ID: {candidates[0].candidate_id}")
    else:
        print(f"Error: {type(error).__name__} - {error}")
    print(f"Execution time: {(t_end - t_start)*1000:.3f} ms")
    print(f"Memory delta: {mem_after - mem_before:.3f} MB (Before: {mem_before:.3f} MB, After: {mem_after:.3f} MB)")
    print()
    return success, len(candidates), error, (t_end - t_start), (mem_after - mem_before)

def test_empty_and_corrupt():
    results = {}
    
    # 1. Completely empty
    results["completely_empty"] = run_test_case("completely_empty", [])
    
    # 2. Only whitespace
    results["whitespace_only"] = run_test_case("whitespace_only", ["   ", "", "\n\n"])
    
    # 3. Invalid JSON formatting
    results["corrupt_json"] = run_test_case("corrupt_json", [
        "not a json at all",
        '{"candidate_id": "CAND_0001", "profile": ', # Unclosed
        '{"candidate_id": "CAND_0002", "profile": {}, "redrob_signals": {}}', # Valid but empty profile/signals
        '{"candidate_id": "CAND_0003", "profile": {}, "redrob_signals": {},' # Trailing comma
    ])
    
    # 4. Deeply nested JSON (Recursion limit stress test)
    # Constructing a JSON object with 1500 nested dictionaries: {"a":{"a": ... {"a":1} ... }}
    deep_json = '{"candidate_id": "CAND_0004", "profile": {}, "redrob_signals": {}, "nested": '
    for _ in range(1500):
        deep_json += '{"a": '
    deep_json += "1"
    for _ in range(1500):
        deep_json += "}"
    deep_json += "}"
    results["deeply_nested_json"] = run_test_case("deeply_nested_json", [deep_json])
    
    return results

def test_missing_and_invalid_types():
    results = {}
    
    # 1. Missing top level keys
    cand1 = BASE_CANDIDATE.copy()
    cand1.pop("candidate_id")
    
    cand2 = BASE_CANDIDATE.copy()
    cand2.pop("profile")
    
    cand3 = BASE_CANDIDATE.copy()
    cand3.pop("redrob_signals")
    
    results["missing_top_level_keys"] = run_test_case("missing_top_level", [
        json.dumps(cand1),
        json.dumps(cand2),
        json.dumps(cand3),
    ])
    
    # 2. Invalid top-level types
    cand_bad_id = BASE_CANDIDATE.copy()
    cand_bad_id["candidate_id"] = 12345 # Should be str
    
    cand_bad_profile = BASE_CANDIDATE.copy()
    cand_bad_profile["profile"] = "not a dict" # Should be dict
    
    cand_bad_signals = BASE_CANDIDATE.copy()
    cand_bad_signals["redrob_signals"] = [] # Should be dict
    
    results["invalid_top_level_types"] = run_test_case("invalid_top_level_types", [
        json.dumps(cand_bad_id),
        json.dumps(cand_bad_profile),
        json.dumps(cand_bad_signals),
    ])
    
    # 3. Missing and non-list collections (career_history, education, skills)
    cand_no_cols = BASE_CANDIDATE.copy()
    cand_no_cols.pop("career_history")
    cand_no_cols.pop("education")
    cand_no_cols.pop("skills")
    
    cand_dict_cols = BASE_CANDIDATE.copy()
    cand_dict_cols["career_history"] = {"company": "not a list"}
    cand_dict_cols["education"] = "not a list"
    cand_dict_cols["skills"] = 42
    
    results["missing_and_non_list_collections"] = run_test_case("missing_non_list_cols", [
        json.dumps(cand_no_cols),
        json.dumps(cand_dict_cols),
    ])
    
    # 4. Non-dictionary items in collections (AttributeError checks)
    cand_bad_list_items = BASE_CANDIDATE.copy()
    cand_bad_list_items["career_history"] = ["not a dict", None, 123, []]
    cand_bad_list_items["education"] = [None]
    cand_bad_list_items["skills"] = ["python"]
    
    results["non_dict_items_in_collections"] = run_test_case("non_dict_items_in_cols", [
        json.dumps(cand_bad_list_items)
    ])
    
    # 5. Invalid inner field types
    cand_invalid_inner = BASE_CANDIDATE.copy()
    # Bad dates
    cand_invalid_inner["career_history"] = [
        {
            "company": "X",
            "title": "Y",
            "start_date": "not-a-date", # Invalid format
            "end_date": 2026, # Not a string
            "duration_months": "twelve", # Non-coercible string
            "is_current": "maybe", # Should resolve to False
            "industry": None,
            "company_size": [],
            "description": {}
        }
    ]
    cand_invalid_inner["education"] = [
        {
            "institution": "U",
            "degree": "D",
            "field_of_study": "F",
            "start_year": "2015", # Coercible string to int
            "end_year": [2019], # Non-coercible list to int
            "grade": None,
            "tier": 3.0 # Float instead of str
        }
    ]
    results["invalid_inner_field_types"] = run_test_case("invalid_inner_field_types", [
        json.dumps(cand_invalid_inner)
    ])
    
    # 6. Signals extreme/nested/missing values
    cand_signals_abuse = BASE_CANDIDATE.copy()
    cand_signals_abuse["redrob_signals"] = {
        "profile_completeness_score": {"nested": "value"}, # Non-coercible dict
        "signup_date": None,
        "last_active_date": "invalid-date",
        "open_to_work_flag": "TRUE", # Coercible string bool
        "profile_views_received_30d": "150", # Coercible string int
        "applications_submitted_30d": [1, 2], # Non-coercible list
        "recruiter_response_rate": "0.95", # Coercible string float
        "avg_response_time_hours": None, # Default should apply
        "skill_assessment_scores": "not a dict", # Invalid type
        "connection_count": None,
        "expected_salary_range_inr_lpa": "not a dict", # Invalid type
        "preferred_work_mode": None,
        "willing_to_relocate": "yes", # Coercible string bool
        "github_activity_score": -99.9,
        "offer_acceptance_rate": 1.5,
    }
    results["signals_abuse"] = run_test_case("signals_abuse", [
        json.dumps(cand_signals_abuse)
    ])
    
    # 7. Signals nested salary and scores abuse
    cand_salary_scores_abuse = BASE_CANDIDATE.copy()
    cand_salary_scores_abuse["redrob_signals"] = BASE_CANDIDATE["redrob_signals"].copy()
    cand_salary_scores_abuse["redrob_signals"]["expected_salary_range_inr_lpa"] = {
        "min": {"very": "nested"}, # Non-coercible dict
        "max": "45.5" # Coercible string float
    }
    cand_salary_scores_abuse["redrob_signals"]["skill_assessment_scores"] = {
        "Python": "90", # Coercible string int
        "ML": "invalid", # Non-coercible string
        "C++": [100] # Non-coercible list
    }
    results["salary_scores_abuse"] = run_test_case("salary_scores_abuse", [
        json.dumps(cand_salary_scores_abuse)
    ])
    
    return results

def test_scaling_and_large_inputs():
    results = {}
    
    # 1. Candidate with huge text fields (10MB summary)
    cand_huge_text = BASE_CANDIDATE.copy()
    cand_huge_text["profile"] = BASE_CANDIDATE["profile"].copy()
    cand_huge_text["profile"]["summary"] = "A" * 10 * 1024 * 1024 # 10MB
    results["huge_text"] = run_test_case("huge_text", [json.dumps(cand_huge_text)])
    
    # 2. Candidate with massive career history list (10,000 entries)
    # This also checks sorting time complexity
    cand_huge_career = BASE_CANDIDATE.copy()
    huge_career = []
    for i in range(10000):
        # Generate varied dates to ensure sorting is exercised
        y = 2000 + (i % 25)
        m = 1 + (i % 12)
        d = 1 + (i % 28)
        huge_career.append({
            "company": f"Company {i}",
            "title": f"Title {i}",
            "start_date": f"{y:04d}-{m:02d}-{d:02d}",
            "end_date": None,
            "duration_months": 12,
            "is_current": False,
            "industry": "IT",
            "company_size": "10-50",
            "description": "Short description"
        })
    cand_huge_career["career_history"] = huge_career
    results["huge_career_list"] = run_test_case("huge_career_list", [json.dumps(cand_huge_career)])
    
    # 3. Candidate with massive skills list (10,000 entries)
    cand_huge_skills = BASE_CANDIDATE.copy()
    huge_skills = []
    for i in range(10000):
        huge_skills.append({
            "name": f"Skill {i}",
            "proficiency": "expert",
            "endorsements": i % 100,
            "duration_months": 24
        })
    cand_huge_skills["skills"] = huge_skills
    results["huge_skills_list"] = run_test_case("huge_skills_list", [json.dumps(cand_huge_skills)])
    
    # 4. Large file scaling: 5000 valid candidates in one file
    # We want to measure the processing time and memory growth per 1000 candidates
    candidates_lines = []
    for i in range(5000):
        cand = BASE_CANDIDATE.copy()
        cand["candidate_id"] = f"CAND_{i:07d}"
        candidates_lines.append(json.dumps(cand))
        
    results["large_scale_5000"] = run_test_case("large_scale_5000", candidates_lines)
    
    return results

if __name__ == "__main__":
    print("Starting Ingestion Stress Test Suite...")
    print(f"Python version: {sys.version}")
    print(f"Initial process memory: {get_memory_usage_mb():.3f} MB")
    print()
    
    # Run tests
    r_empty_corrupt = test_empty_and_corrupt()
    r_missing_invalid = test_missing_and_invalid_types()
    r_scaling = test_scaling_and_large_inputs()
    
    print("Stress Test Suite Complete.")
