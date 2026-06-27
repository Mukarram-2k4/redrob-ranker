"""
tests/stress_test_filters.py
Stress test harness for candidate filtering and honeypot detection logic in src/filters.py.
"""

import sys
from datetime import date
from src.models import Candidate, CareerEntry, EducationEntry, SkillEntry, Signals
from src.filters import early_eliminate, honeypot_full_pass
from src.config import HONEYPOT_CONFIDENCE_THRESHOLD, HP03_OVERLAP_DAYS, CURRENT_YEAR

def make_dummy_signals(**overrides) -> Signals:
    defaults = {
        "profile_completeness_score": 90.0,
        "signup_date": date(2025, 1, 1),
        "last_active_date": date(2026, 5, 25),
        "open_to_work_flag": True,
        "profile_views_received_30d": 50,
        "applications_submitted_30d": 2,
        "recruiter_response_rate": 0.8,
        "avg_response_time_hours": 2.0,
        "skill_assessment_scores": {},
        "connection_count": 100,
        "endorsements_received": 10,
        "notice_period_days": 30,
        "salary_min_lpa": 10.0,
        "salary_max_lpa": 20.0,
        "preferred_work_mode": "hybrid",
        "willing_to_relocate": True,
        "github_activity_score": 50.0,
        "search_appearance_30d": 20,
        "saved_by_recruiters_30d": 5,
        "interview_completion_rate": 0.8,
        "offer_acceptance_rate": 0.8,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True
    }
    defaults.update(overrides)
    
    # Handle nested expected_salary_range_inr_lpa structure if needed,
    # but here Signals expects min and max directly as floats:
    # salary_min_lpa: float, salary_max_lpa: float.
    return Signals(
        profile_completeness_score=defaults["profile_completeness_score"],
        signup_date=defaults["signup_date"],
        last_active_date=defaults["last_active_date"],
        open_to_work_flag=defaults["open_to_work_flag"],
        profile_views_received_30d=defaults["profile_views_received_30d"],
        applications_submitted_30d=defaults["applications_submitted_30d"],
        recruiter_response_rate=defaults["recruiter_response_rate"],
        avg_response_time_hours=defaults["avg_response_time_hours"],
        skill_assessment_scores=defaults["skill_assessment_scores"],
        connection_count=defaults["connection_count"],
        endorsements_received=defaults["endorsements_received"],
        notice_period_days=defaults["notice_period_days"],
        salary_min_lpa=defaults["salary_min_lpa"],
        salary_max_lpa=defaults["salary_max_lpa"],
        preferred_work_mode=defaults["preferred_work_mode"],
        willing_to_relocate=defaults["willing_to_relocate"],
        github_activity_score=defaults["github_activity_score"],
        search_appearance_30d=defaults["search_appearance_30d"],
        saved_by_recruiters_30d=defaults["saved_by_recruiters_30d"],
        interview_completion_rate=defaults["interview_completion_rate"],
        offer_acceptance_rate=defaults["offer_acceptance_rate"],
        verified_email=defaults["verified_email"],
        verified_phone=defaults["verified_phone"],
        linkedin_connected=defaults["linkedin_connected"]
    )

def make_candidate(candidate_id: str, **overrides) -> Candidate:
    defaults = {
        "anonymized_name": "Test Candidate",
        "headline": "AI Engineer",
        "summary": "Experienced in building vector search systems using FAISS.",
        "location": "Pune",
        "country": "India",
        "years_of_experience": 5.0,
        "current_title": "AI Engineer",
        "current_company": "Acme Corp",
        "current_company_size": "51-200",
        "current_industry": "software",
        "career_history": [],
        "education": [],
        "skills": [SkillEntry(name="FAISS", proficiency="expert", endorsements=5, duration_months=24)],
        "signals": make_dummy_signals()
    }
    defaults.update(overrides)
    return Candidate(
        candidate_id=candidate_id,
        anonymized_name=defaults["anonymized_name"],
        headline=defaults["headline"],
        summary=defaults["summary"],
        location=defaults["location"],
        country=defaults["country"],
        years_of_experience=defaults["years_of_experience"],
        current_title=defaults["current_title"],
        current_company=defaults["current_company"],
        current_company_size=defaults["current_company_size"],
        current_industry=defaults["current_industry"],
        career_history=defaults["career_history"],
        education=defaults["education"],
        skills=defaults["skills"],
        signals=defaults["signals"]
    )

def run_stress_tests():
    print("Running Candidate Filtering and Honeypot Detection Stress Tests...")
    failures = 0
    
    # ----------------------------------------------------
    # TEST 1: YOE Edge Case (2.0 threshold)
    # ----------------------------------------------------
    print("\n--- Test 1: YOE Boundaries (2.0 threshold) ---")
    c_1_99 = make_candidate("CAND_YOE_1_99", years_of_experience=1.99)
    c_2_00 = make_candidate("CAND_YOE_2_00", years_of_experience=2.0)
    c_2_01 = make_candidate("CAND_YOE_2_01", years_of_experience=2.01)
    
    candidates = [c_1_99, c_2_00, c_2_01]
    survivors, eliminated = early_eliminate(candidates, {})
    
    elim_ids = {c.candidate_id for c in eliminated}
    surv_ids = {c.candidate_id for c in survivors}
    
    if "CAND_YOE_1_99" not in elim_ids:
        print("FAIL: YOE 1.99 should have been eliminated.")
        failures += 1
    else:
        print("PASS: YOE 1.99 eliminated.")
        
    if "CAND_YOE_2_00" not in surv_ids:
        print("FAIL: YOE 2.00 should have survived.")
        failures += 1
    else:
        print("PASS: YOE 2.00 survived.")
        
    if "CAND_YOE_2_01" not in surv_ids:
        print("FAIL: YOE 2.01 should have survived.")
        failures += 1
    else:
        print("PASS: YOE 2.01 survived.")

    # ----------------------------------------------------
    # TEST 2: Multiple Education Degrees (HP05: YOE > CURRENT_YEAR - earliest_edu_end)
    # ----------------------------------------------------
    print("\n--- Test 2: Multiple Education Degrees (HP05 Rule) ---")
    # Candidate lists only M.Tech ending 2024. YOE = 3.0.
    # HP05 checks if YOE (3.0) > 2026 - 2024 = 2 -> True -> HP05 triggered (conf=0.8) -> eliminated.
    c_only_mtech = make_candidate(
        "CAND_ONLY_MTECH",
        years_of_experience=3.0,
        education=[EducationEntry("IIT", "M.Tech", "CS", 2022, 2024, "8.0", "tier_1")]
    )
    
    # Candidate lists B.Tech (end 2022) and M.Tech (end 2024). YOE = 3.0.
    # HP05 checks if YOE (3.0) > 2026 - 2022 = 4 -> False -> Survives.
    c_btech_mtech = make_candidate(
        "CAND_BTECH_MTECH",
        years_of_experience=3.0,
        education=[
            EducationEntry("IIT", "B.Tech", "CS", 2018, 2022, "8.0", "tier_1"),
            EducationEntry("IIT", "M.Tech", "CS", 2022, 2024, "8.0", "tier_1")
        ]
    )
    
    survivors, eliminated = early_eliminate([c_only_mtech, c_btech_mtech], {})
    elim_ids = {c.candidate_id for c in eliminated}
    surv_ids = {c.candidate_id for c in survivors}
    
    if "CAND_ONLY_MTECH" not in elim_ids:
        print("FAIL: CAND_ONLY_MTECH should have been flagged for HP05 and eliminated.")
        failures += 1
    else:
        print("PASS: CAND_ONLY_MTECH eliminated (HP05 triggered due to missing lower degree).")
        
    if "CAND_BTECH_MTECH" not in surv_ids:
        print("FAIL: CAND_BTECH_MTECH should have survived HP05 check.")
        failures += 1
    else:
        print("PASS: CAND_BTECH_MTECH survived (lower degree present, earliest end year is 2022).")

    # ----------------------------------------------------
    # TEST 3: Overlap Days Boundary (HP03 Rule: overlap > HP03_OVERLAP_DAYS)
    # ----------------------------------------------------
    print("\n--- Test 3: Overlap Days Boundaries (HP03 Rule) ---")
    # exactly 90 days overlap. Let's make entry 1 and entry 2 overlap by exactly 90 days.
    # Entry 1: 2020-01-01 to 2020-06-01 (152 days)
    # Entry 2: 2020-03-03 to 2020-08-01 (151 days)
    # Overlap starts max(2020-01-01, 2020-03-03) = 2020-03-03
    # Overlap ends min(2020-06-01, 2020-08-01) = 2020-06-01
    # Number of days between 2020-03-03 and 2020-06-01 is 90 days.
    # Let's verify: March has 31 days. April has 30 days. May has 31 days.
    # From March 3 to March 31: 28 days. April: 30 days. May: 31 days. June 1: 1 day.
    # 28 + 30 + 31 + 1 = 90 days. Perfect.
    e_90_1 = CareerEntry("A", "Eng", date(2020, 1, 1), date(2020, 6, 1), 5, False, "software", "51-200", "")
    e_90_2 = CareerEntry("B", "Eng", date(2020, 3, 3), date(2020, 8, 1), 5, False, "software", "51-200", "")
    
    # 91 days overlap.
    # Entry 1: 2020-01-01 to 2020-06-02 (153 days)
    # Entry 2: 2020-03-03 to 2020-08-01 (151 days)
    # Overlap: 2020-03-03 to 2020-06-02 -> 91 days.
    e_91_1 = CareerEntry("A", "Eng", date(2020, 1, 1), date(2020, 6, 2), 5, False, "software", "51-200", "")
    e_91_2 = CareerEntry("B", "Eng", date(2020, 3, 3), date(2020, 8, 1), 5, False, "software", "51-200", "")
    
    c_overlap_90 = make_candidate("CAND_OVERLAP_90", career_history=[e_90_1, e_90_2])
    c_overlap_91 = make_candidate("CAND_OVERLAP_91", career_history=[e_91_1, e_91_2])
    
    # HP03 is a full pass rule, so we run honeypot_full_pass on them (assuming they survived early_eliminate)
    # Let's ensure they have 0 early honeypot confidence first
    early_eliminate([c_overlap_90, c_overlap_91], {})
    honeypot_full_pass([c_overlap_90, c_overlap_91])
    
    if c_overlap_90.honeypot_flag:
        print("FAIL: CAND_OVERLAP_90 should not be flagged as honeypot (exactly 90 days overlap, threshold is > 90).")
        failures += 1
    else:
        print("PASS: CAND_OVERLAP_90 not flagged (exactly 90 days overlap is fine).")
        
    if not c_overlap_91.honeypot_flag:
        print("FAIL: CAND_OVERLAP_91 should be flagged as honeypot (91 days overlap > 90).")
        failures += 1
    else:
        print("PASS: CAND_OVERLAP_91 flagged.")

    # ----------------------------------------------------
    # TEST 4: Fixture Company Substring Variations (HP10 Rule)
    # ----------------------------------------------------
    print("\n--- Test 4: Fixture Company Substrings (HP10 Rule) ---")
    # Substrings variations: "Pied Piper Inc.", "WAYNE ENTERPRISES", "stark industries, llc", "Globex Corporation"
    # To check HP10, we need another HP rule to get total confidence >= 0.60, since HP10 itself is only 0.10.
    # Let's combine HP10 (0.10) with HP08 (0.50) = 0.60.
    # HP08: skill_assessment_scores count >= 3 and all scores >= 90.
    hp08_signals = make_dummy_signals(
        skill_assessment_scores={"Python": 95, "ML": 95, "SQL": 95}
    )
    
    c_pied_piper = make_candidate("CAND_PIED_PIPER", current_company="Pied Piper Inc.", signals=hp08_signals)
    c_wayne = make_candidate("CAND_WAYNE", current_company="WAYNE ENTERPRISES", signals=hp08_signals)
    c_stark = make_candidate("CAND_STARK", career_history=[
        CareerEntry("stark industries, llc", "Eng", date(2020, 1, 1), date(2022, 1, 1), 24, False, "software", "51-200", "")
    ], signals=hp08_signals)
    c_clean_co = make_candidate("CAND_CLEAN_CO", current_company="Google Inc.", signals=hp08_signals)
    
    early_eliminate([c_pied_piper, c_wayne, c_stark, c_clean_co], {})
    honeypot_full_pass([c_pied_piper, c_wayne, c_stark, c_clean_co])
    
    if not c_pied_piper.honeypot_flag:
        print("FAIL: CAND_PIED_PIPER should be flagged (Pied Piper substring).")
        failures += 1
    else:
        print("PASS: CAND_PIED_PIPER flagged.")
        
    if not c_wayne.honeypot_flag:
        print("FAIL: CAND_WAYNE should be flagged (WAYNE ENTERPRISES substring).")
        failures += 1
    else:
        print("PASS: CAND_WAYNE flagged.")
        
    if not c_stark.honeypot_flag:
        print("FAIL: CAND_STARK should be flagged (stark industries substring).")
        failures += 1
    else:
        print("PASS: CAND_STARK flagged.")
        
    if c_clean_co.honeypot_flag:
        print("FAIL: CAND_CLEAN_CO should not be flagged.")
        failures += 1
    else:
        print("PASS: CAND_CLEAN_CO not flagged.")

    # ----------------------------------------------------
    # TEST 5: Survivors vs Eliminated Lists & Mutation Consistency
    # ----------------------------------------------------
    print("\n--- Test 5: Survivors/Eliminated Disjointness and Flag Mutations ---")
    # Let's pass a variety of candidates and check for strict partitioning.
    c_junior = make_candidate("CAND_JUNIOR", years_of_experience=1.0) # eliminated (YOE < 2.0)
    c_no_tech = make_candidate("CAND_NO_TECH", skills=[SkillEntry("agile", "expert", 5, 12)]) # eliminated (no tech skills)
    c_hp_early = make_candidate("CAND_HP_EARLY", signals=make_dummy_signals(salary_min_lpa=50.0, salary_max_lpa=45.0)) # eliminated (HP01: inversion)
    c_valid = make_candidate("CAND_VALID", years_of_experience=5.0) # survivor
    
    candidates = [c_junior, c_no_tech, c_hp_early, c_valid]
    
    survivors, eliminated = early_eliminate(candidates, {})
    
    elim_ids = {c.candidate_id for c in eliminated}
    surv_ids = {c.candidate_id for c in survivors}
    
    # 1. Disjointness check
    intersection = elim_ids.intersection(surv_ids)
    if intersection:
        print(f"FAIL: Non-empty intersection between survivors and eliminated: {intersection}")
        failures += 1
    else:
        print("PASS: Survivors and eliminated lists are strictly disjoint.")
        
    # 2. Complete partitioning check
    total_ids = {c.candidate_id for c in candidates}
    union = elim_ids.union(surv_ids)
    if union != total_ids:
        print(f"FAIL: Missing or extra candidates in output. Expected: {total_ids}, Got: {union}")
        failures += 1
    else:
        print("PASS: Partitioning is complete.")
        
    # 3. Flag mutations check
    # Check that eliminated candidates have eliminated_early = True, and survivors have eliminated_early = False
    for c in eliminated:
        if not c.eliminated_early:
            print(f"FAIL: Candidate {c.candidate_id} was eliminated but eliminated_early flag is not True.")
            failures += 1
    for c in survivors:
        if c.eliminated_early:
            print(f"FAIL: Candidate {c.candidate_id} survived but eliminated_early flag is True.")
            failures += 1
            
    print("PASS: eliminated_early flags correctly mutated.")
    
    # Check that hard_disqualify flag is mutated correctly.
    # recruiter_response_rate < 0.10 and interview_completion_rate < 0.30 -> hard_disqualify = True
    c_disq = make_candidate("CAND_DISQ", signals=make_dummy_signals(recruiter_response_rate=0.05, interview_completion_rate=0.25))
    c_not_disq = make_candidate("CAND_NOT_DISQ", signals=make_dummy_signals(recruiter_response_rate=0.15, interview_completion_rate=0.25))
    
    early_eliminate([c_disq, c_not_disq], {})
    
    if not c_disq.hard_disqualify:
        print("FAIL: CAND_DISQ should have hard_disqualify = True.")
        failures += 1
    else:
        print("PASS: CAND_DISQ hard_disqualify flag set.")
        
    if c_not_disq.hard_disqualify:
        print("FAIL: CAND_NOT_DISQ should not have hard_disqualify = True.")
        failures += 1
    else:
        print("PASS: CAND_NOT_DISQ hard_disqualify flag not set.")
        
    # ----------------------------------------------------
    # Summary of failures
    # ----------------------------------------------------
    print(f"\nStress Testing completed with {failures} failures.")
    return failures

if __name__ == "__main__":
    sys.exit(run_stress_tests())
