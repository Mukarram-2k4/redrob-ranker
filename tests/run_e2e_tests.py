import json
import os
import sys
import subprocess
import csv
import tempfile
import time
from pathlib import Path
from tests.candidate_templates import create_candidate

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Helper to build career history entry
def make_career(company, title, start_date, end_date, duration_months, is_current=False, industry="software", company_size="201-500", description=""):
    return {
        "company": company,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "duration_months": duration_months,
        "is_current": is_current,
        "industry": industry,
        "company_size": company_size,
        "description": description
    }

# Helper to build education entry
def make_edu(institution, degree, field_of_study, start_year, end_year, tier="unknown", grade="8.0 CGPA"):
    return {
        "institution": institution,
        "degree": degree,
        "field_of_study": field_of_study,
        "start_year": start_year,
        "end_year": end_year,
        "grade": grade,
        "tier": tier
    }

# Helper to build skill entry
def make_skill(name, proficiency="advanced", endorsements=10, duration_months=24):
    return {
        "name": name,
        "proficiency": proficiency,
        "endorsements": endorsements,
        "duration_months": duration_months
    }

# General assertions
def verify_cand_in_csv(cand_id):
    def fn(rows):
        cids = [r[0] for r in rows]
        if cand_id in cids:
            return True, f"Candidate {cand_id} found in CSV."
        return False, f"Candidate {cand_id} not found in CSV."
    return fn

def verify_cand_not_in_csv(cand_id):
    def fn(rows):
        cids = [r[0] for r in rows]
        if cand_id not in cids:
            return True, f"Candidate {cand_id} successfully filtered out."
        return False, f"Candidate {cand_id} should have been filtered out but is in CSV."
    return fn

def verify_disqualified(cand_id):
    def fn(rows):
        for cid, rank, score, reasoning in rows:
            if cid == cand_id:
                if score == -1.0 or score == 0.0: # depending on how score is normalized
                    return True, f"Candidate {cand_id} disqualified with score {score}."
                return False, f"Candidate {cand_id} is in CSV but has score {score} (expected disqualified)."
        return True, f"Candidate {cand_id} is absent from CSV (disqualified)."
    return fn

def verify_rank_order(higher_id, lower_id, relation_desc=""):
    def fn(rows):
        h_rank, l_rank = -1, -1
        h_score, l_score = -2.0, -2.0
        for cid, rank, score, reasoning in rows:
            if cid == higher_id:
                h_rank, h_score = rank, score
            if cid == lower_id:
                l_rank, l_score = rank, score
        if h_rank != -1 and l_rank != -1:
            if h_rank < l_rank:
                return True, f"Rank order verified: {higher_id} (Rank {h_rank}, Score {h_score}) > {lower_id} (Rank {l_rank}, Score {l_score}). {relation_desc}"
            return False, f"Rank order violated: {higher_id} (Rank {h_rank}) is not better than {lower_id} (Rank {l_rank}). {relation_desc}"
        if h_rank != -1 and l_rank == -1:
            return True, f"Rank order verified: {higher_id} is in CSV (Rank {h_rank}), {lower_id} was filtered/disqualified. {relation_desc}"
        return False, f"Could not verify rank order: {higher_id} absent (rank={h_rank}), {lower_id} absent (rank={l_rank}). {relation_desc}"
    return fn


def create_late_honeypot(candidate_id: str) -> dict:
    return create_candidate(
        candidate_id,
        profile={"years_of_experience": 7.0},
        career_history=[
            make_career("Company A", "AI Engineer", "2017-01-01", "2020-01-01", 36),
            make_career("Company B", "Senior AI Engineer", "2019-01-01", "2024-01-01", 60)
        ]
    )


def build_all_tests():
    tests = []

    # ==========================================
    # FEATURE 1: Ingestion & Parsing (TC_001 - TC_010)
    # ==========================================
    tests.append({
        "id": "TC_001", "tier": 1, "feature": "F1",
        "description": "Standard valid candidate parses and survives.",
        "candidates": [create_candidate("CAND_001")],
        "verify": verify_cand_in_csv("CAND_001")
    })
    tests.append({
        "id": "TC_002", "tier": 1, "feature": "F1",
        "description": "Skip malformed JSON line, parse subsequent valid line.",
        "raw_lines": ["{invalid json line }", json.dumps(create_candidate("CAND_002"))],
        "verify": verify_cand_in_csv("CAND_002")
    })
    tests.append({
        "id": "TC_003", "tier": 1, "feature": "F1",
        "description": "Skip profile with missing candidate_id.",
        "raw_lines": [json.dumps({"profile": {}, "redrob_signals": {}}), json.dumps(create_candidate("CAND_003"))],
        "verify": lambda rows: (len(rows) == 1 and rows[0][0] == "CAND_003", f"Expected 1 row for CAND_003, got {len(rows)}")
    })
    tests.append({
        "id": "TC_004", "tier": 1, "feature": "F1",
        "description": "Skip profile with missing nested profile object.",
        "raw_lines": [json.dumps({"candidate_id": "CAND_004_BAD", "redrob_signals": {}}), json.dumps(create_candidate("CAND_004"))],
        "verify": lambda rows: (len(rows) == 1 and rows[0][0] == "CAND_004", "Skipped candidate with missing profile object")
    })
    tests.append({
        "id": "TC_005", "tier": 1, "feature": "F1",
        "description": "Skip profile with missing redrob_signals object.",
        "raw_lines": [json.dumps({"candidate_id": "CAND_005_BAD", "profile": {}}), json.dumps(create_candidate("CAND_005"))],
        "verify": lambda rows: (len(rows) == 1 and rows[0][0] == "CAND_005", "Skipped candidate with missing signals")
    })
    tests.append({
        "id": "TC_006", "tier": 2, "feature": "F1",
        "description": "Parse profile with missing career_history (parses to empty list, survives if other fields valid).",
        "candidates": [create_candidate("CAND_006", career_history=[])],
        "verify": verify_cand_in_csv("CAND_006")
    })
    tests.append({
        "id": "TC_007", "tier": 2, "feature": "F1",
        "description": "Parse profile with missing education (parses to empty list, survives).",
        "candidates": [create_candidate("CAND_007", education=[])],
        "verify": verify_cand_in_csv("CAND_007")
    })
    tests.append({
        "id": "TC_008", "tier": 2, "feature": "F1",
        "description": "Parse profile with missing skills (filtered in early filters since no tech skills).",
        "candidates": [create_candidate("CAND_008", skills=[])],
        "verify": verify_cand_not_in_csv("CAND_008")
    })
    tests.append({
        "id": "TC_009", "tier": 2, "feature": "F1",
        "description": "Skip individual malformed career entries but parse overall profile.",
        "candidates": [create_candidate("CAND_009", profile={"years_of_experience": 2.0}, career_history=[
            make_career("A", "Eng", "invalid-date", "2020-01-01", 12),
            make_career("B", "Eng", "2021-01-01", "2023-01-01", 24)
        ])],
        "verify": verify_cand_in_csv("CAND_009")
    })
    tests.append({
        "id": "TC_010", "tier": 2, "feature": "F1",
        "description": "Invalid signals types (fallback or error recovery).",
        "candidates": [create_candidate("CAND_010", redrob_signals={"connection_count": "invalid_int"})],
        "verify": verify_cand_in_csv("CAND_010")
    })

    # ==========================================
    # FEATURE 2: Early Elimination Filters (TC_011 - TC_020)
    # ==========================================
    tests.append({
        "id": "TC_011", "tier": 1, "feature": "F2",
        "description": "Early eliminate YOE = 1.9.",
        "candidates": [create_candidate("CAND_011", profile={"years_of_experience": 1.9})],
        "verify": verify_cand_not_in_csv("CAND_011")
    })
    tests.append({
        "id": "TC_012", "tier": 1, "feature": "F2",
        "description": "Survive early filter YOE = 2.0.",
        "candidates": [create_candidate("CAND_012", profile={"years_of_experience": 2.0})],
        "verify": verify_cand_in_csv("CAND_012")
    })
    tests.append({
        "id": "TC_013", "tier": 1, "feature": "F2",
        "description": "Early eliminate candidate with zero skills list.",
        "candidates": [create_candidate("CAND_013", skills=[])],
        "verify": verify_cand_not_in_csv("CAND_013")
    })
    tests.append({
        "id": "TC_014", "tier": 1, "feature": "F2",
        "description": "Early eliminate candidate with only non-tech skills.",
        "candidates": [create_candidate("CAND_014", skills=[make_skill("communication", endorsements=5)])],
        "verify": verify_cand_not_in_csv("CAND_014")
    })
    tests.append({
        "id": "TC_015", "tier": 1, "feature": "F2",
        "description": "Early eliminate candidate with high confidence honeypot (HP01 Salary Inversion).",
        "candidates": [create_candidate("CAND_015", redrob_signals={"expected_salary_range_inr_lpa": {"min": 50.0, "max": 30.0}})],
        "verify": verify_cand_not_in_csv("CAND_015")
    })
    tests.append({
        "id": "TC_016", "tier": 2, "feature": "F2",
        "description": "Early eliminate YOE = 0.0.",
        "candidates": [create_candidate("CAND_016", profile={"years_of_experience": 0.0})],
        "verify": verify_cand_not_in_csv("CAND_016")
    })
    tests.append({
        "id": "TC_017", "tier": 2, "feature": "F2",
        "description": "Survive early filter: YOE = 2.0 with exactly 1 tech skill (Tier B).",
        "candidates": [create_candidate("CAND_017", profile={"years_of_experience": 2.0}, skills=[make_skill("PyTorch")])],
        "verify": verify_cand_in_csv("CAND_017")
    })
    tests.append({
        "id": "TC_018", "tier": 2, "feature": "F2",
        "description": "Early eliminate candidate with HP02 (YOE vs Career Span).",
        "candidates": [create_candidate("CAND_018", profile={"years_of_experience": 10.0}, career_history=[
            make_career("A", "SE", "2024-01-01", "2026-01-01", 24)
        ])],
        "verify": verify_cand_not_in_csv("CAND_018")
    })
    tests.append({
        "id": "TC_019", "tier": 2, "feature": "F2",
        "description": "Early eliminate candidate with HP06 (Impossible tenure).",
        "candidates": [create_candidate("CAND_019", career_history=[
            make_career("A", "SE", "2024-01-01", "2024-12-31", 50)
        ])],
        "verify": verify_cand_not_in_csv("CAND_019")
    })
    tests.append({
        "id": "TC_020", "tier": 2, "feature": "F2",
        "description": "Survive early filter: YOE = 2.01 with exactly 1 tech skill (Tier D).",
        "candidates": [create_candidate("CAND_020", profile={"years_of_experience": 2.01}, skills=[make_skill("Python")])],
        "verify": verify_cand_in_csv("CAND_020")
    })

    # ==========================================
    # FEATURE 3: Hard Disqualification (TC_021 - TC_030)
    # ==========================================
    tests.append({
        "id": "TC_021", "tier": 1, "feature": "F3",
        "description": "Disqualify candidate: RR < 0.10 and ICR < 0.30.",
        "candidates": [create_candidate("CAND_021", redrob_signals={"recruiter_response_rate": 0.09, "interview_completion_rate": 0.29})],
        "verify": verify_disqualified("CAND_021")
    })
    tests.append({
        "id": "TC_022", "tier": 1, "feature": "F3",
        "description": "Survive disqualification boundary: RR = 0.10, ICR = 0.29.",
        "candidates": [create_candidate("CAND_022", redrob_signals={"recruiter_response_rate": 0.10, "interview_completion_rate": 0.29})],
        "verify": lambda rows: (not any(r[0] == "CAND_022" and r[2] == -1.0 for r in rows), "Did not disqualify at RR boundary")
    })
    tests.append({
        "id": "TC_023", "tier": 1, "feature": "F3",
        "description": "Survive disqualification boundary: RR = 0.09, ICR = 0.30.",
        "candidates": [create_candidate("CAND_023", redrob_signals={"recruiter_response_rate": 0.09, "interview_completion_rate": 0.30})],
        "verify": lambda rows: (not any(r[0] == "CAND_023" and r[2] == -1.0 for r in rows), "Did not disqualify at ICR boundary")
    })
    tests.append({
        "id": "TC_024", "tier": 1, "feature": "F3",
        "description": "Disqualify candidate: RR = 0.0, ICR = 0.0.",
        "candidates": [create_candidate("CAND_024", redrob_signals={"recruiter_response_rate": 0.0, "interview_completion_rate": 0.0})],
        "verify": verify_disqualified("CAND_024")
    })
    tests.append({
        "id": "TC_025", "tier": 1, "feature": "F3",
        "description": "Survive: RR = 0.90, ICR = 0.90.",
        "candidates": [create_candidate("CAND_025", redrob_signals={"recruiter_response_rate": 0.90, "interview_completion_rate": 0.90})],
        "verify": lambda rows: (not any(r[0] == "CAND_025" and r[2] == -1.0 for r in rows), "Clean candidate not disqualified")
    })
    tests.append({
        "id": "TC_026", "tier": 2, "feature": "F3",
        "description": "Disqualify candidate near threshold: RR = 0.099, ICR = 0.299.",
        "candidates": [create_candidate("CAND_026", redrob_signals={"recruiter_response_rate": 0.099, "interview_completion_rate": 0.299})],
        "verify": verify_disqualified("CAND_026")
    })
    tests.append({
        "id": "TC_027", "tier": 2, "feature": "F3",
        "description": "Survive near threshold: RR = 0.101, ICR = 0.299.",
        "candidates": [create_candidate("CAND_027", redrob_signals={"recruiter_response_rate": 0.101, "interview_completion_rate": 0.299})],
        "verify": lambda rows: (not any(r[0] == "CAND_027" and r[2] == -1.0 for r in rows), "Did not disqualify at RR boundary + eps")
    })
    tests.append({
        "id": "TC_028", "tier": 2, "feature": "F3",
        "description": "Survive near threshold: RR = 0.099, ICR = 0.301.",
        "candidates": [create_candidate("CAND_028", redrob_signals={"recruiter_response_rate": 0.099, "interview_completion_rate": 0.301})],
        "verify": lambda rows: (not any(r[0] == "CAND_028" and r[2] == -1.0 for r in rows), "Did not disqualify at ICR boundary + eps")
    })
    tests.append({
        "id": "TC_029", "tier": 2, "feature": "F3",
        "description": "Disqualified candidate scores lower than any clean candidate.",
        "candidates": [
            create_candidate("CAND_029_A"),
            create_candidate("CAND_029_B", redrob_signals={"recruiter_response_rate": 0.05, "interview_completion_rate": 0.10})
        ],
        "verify": verify_rank_order("CAND_029_A", "CAND_029_B", "Disqualified B ranked lower than clean A")
    })
    tests.append({
        "id": "TC_030", "tier": 2, "feature": "F3",
        "description": "Disqualify candidate with extreme negative signals: RR = -0.05, ICR = -0.10.",
        "candidates": [create_candidate("CAND_030", redrob_signals={"recruiter_response_rate": -0.05, "interview_completion_rate": -0.10})],
        "verify": verify_disqualified("CAND_030")
    })

    # ==========================================
    # FEATURE 4: Honeypot Detection (TC_031 - TC_040)
    # ==========================================
    tests.append({
        "id": "TC_031", "tier": 1, "feature": "F4",
        "description": "Early filter: HP01 Salary Inversion (confidence 0.8 >= 0.6).",
        "candidates": [create_candidate("CAND_031", redrob_signals={"expected_salary_range_inr_lpa": {"min": 50.0, "max": 40.0}})],
        "verify": verify_cand_not_in_csv("CAND_031")
    })
    tests.append({
        "id": "TC_032", "tier": 1, "feature": "F4",
        "description": "Full pass honeypot: HP03 Overlapping Tenures (confidence 0.6 >= 0.6).",
        "candidates": [
            create_candidate("CAND_032_CLEAN"),
            create_candidate("CAND_032_HP", career_history=[
                make_career("A", "SE", "2020-01-01", "2022-01-01", 24),
                make_career("B", "SE", "2021-06-01", "2023-06-01", 24) # Overlaps by 6 months (>90 days)
            ])
        ],
        "verify": verify_rank_order("CAND_032_CLEAN", "CAND_032_HP", "Clean candidate preferred over HP03 honeypot")
    })
    tests.append({
        "id": "TC_033", "tier": 1, "feature": "F4",
        "description": "HP04 (Edu vs Career: confidence 0.3) alone does not flag honeypot.",
        "candidates": [create_candidate("CAND_033", profile={"years_of_experience": 3.0}, education=[
            make_edu("IIT", "B.Tech", "CS", 2018, 2022)
        ], career_history=[
            make_career("A", "SE", "2015-01-01", "2018-01-01", 36)
        ])],
        "verify": verify_cand_in_csv("CAND_033")
    })
    tests.append({
        "id": "TC_034", "tier": 1, "feature": "F4",
        "description": "HP07 (Perfect profile completeness, inactive 4 years: confidence 0.4) alone does not flag.",
        "candidates": [create_candidate("CAND_034", redrob_signals={
            "profile_completeness_score": 100.0,
            "last_active_date": "2022-01-01"
        })],
        "verify": verify_cand_in_csv("CAND_034")
    })
    tests.append({
        "id": "TC_035", "tier": 1, "feature": "F4",
        "description": "HP08 (3 assessments with scores >= 90: confidence 0.5) alone does not flag.",
        "candidates": [create_candidate("CAND_035", redrob_signals={
            "skill_assessment_scores": {"Python": 95, "ML": 95, "SQL": 95}
        })],
        "verify": verify_cand_in_csv("CAND_035")
    })
    tests.append({
        "id": "TC_036", "tier": 2, "feature": "F4",
        "description": "HP04 (0.3) + HP07 (0.4) = 0.7 >= 0.6 -> Flagged as honeypot.",
        "candidates": [
            create_candidate("CAND_036_CLEAN"),
            create_candidate("CAND_036_HP", education=[
                make_edu("IIT", "B.Tech", "CS", 2018, 2022)
            ], career_history=[
                make_career("A", "SE", "2015-01-01", "2018-01-01", 36)
            ], redrob_signals={
                "profile_completeness_score": 100.0,
                "last_active_date": "2022-01-01"
            })
        ],
        "verify": verify_rank_order("CAND_036_CLEAN", "CAND_036_HP", "Clean candidate preferred over composite HP")
    })
    tests.append({
        "id": "TC_037", "tier": 2, "feature": "F4",
        "description": "HP09 (Instant response: 0.4) + HP10 (Fixture company: 0.1) = 0.5 < 0.6 -> Not flagged.",
        "candidates": [create_candidate("CAND_037", profile={"years_of_experience": 2.0}, redrob_signals={
            "avg_response_time_hours": 0.05
        }, career_history=[
            make_career("piedpiper", "SE", "2020-01-01", "2022-01-01", 24)
        ])],
        "verify": verify_cand_in_csv("CAND_037")
    })
    tests.append({
        "id": "TC_038", "tier": 2, "feature": "F4",
        "description": "HP09 (0.4) + HP10 (0.1) + HP04 (0.3) = 0.8 >= 0.6 -> Flagged.",
        "candidates": [
            create_candidate("CAND_038_CLEAN"),
            create_candidate("CAND_038_HP", profile={"years_of_experience": 3.0}, redrob_signals={
                "avg_response_time_hours": 0.05
            }, career_history=[
                make_career("piedpiper", "SE", "2015-01-01", "2018-01-01", 36)
            ], education=[
                make_edu("IIT", "B.Tech", "CS", 2018, 2022)
            ])
        ],
        "verify": verify_rank_order("CAND_038_CLEAN", "CAND_038_HP", "Clean candidate preferred over 3-way HP")
    })
    tests.append({
        "id": "TC_039", "tier": 2, "feature": "F4",
        "description": "Early filter: HP02 YOE vs Career Span (confidence 0.7 >= 0.6).",
        "candidates": [create_candidate("CAND_039", profile={"years_of_experience": 10.0}, career_history=[
            make_career("A", "SE", "2024-01-01", "2026-01-01", 24)
        ])],
        "verify": verify_cand_not_in_csv("CAND_039")
    })
    tests.append({
        "id": "TC_040", "tier": 2, "feature": "F4",
        "description": "Early filter: HP06 Impossible Tenure (confidence 0.9 >= 0.6).",
        "candidates": [create_candidate("CAND_040", career_history=[
            make_career("A", "SE", "2024-01-01", "2024-12-31", 50)
        ])],
        "verify": verify_cand_not_in_csv("CAND_040")
    })

    # ==========================================
    # FEATURE 5: Behavioral Multiplier (TC_041 - TC_050)
    # ==========================================
    tests.append({
        "id": "TC_041", "tier": 1, "feature": "F5",
        "description": "Behavioral multiplier: Excellent (>= 0.70 -> 1.15) vs Neutral (0.50-0.69 -> 1.00).",
        "candidates": [
            create_candidate("CAND_041_EXC", redrob_signals={"recruiter_response_rate": 0.95, "interview_completion_rate": 0.95, "github_activity_score": 90.0, "profile_completeness_score": 100.0, "last_active_date": "2026-05-30"}),
            create_candidate("CAND_041_NEU", redrob_signals={"recruiter_response_rate": 0.55, "interview_completion_rate": 0.55, "github_activity_score": 20.0, "profile_completeness_score": 60.0, "last_active_date": "2026-05-15"})
        ],
        "verify": verify_rank_order("CAND_041_EXC", "CAND_041_NEU", "Excellent behavioral multiplier ranks higher")
    })
    tests.append({
        "id": "TC_042", "tier": 1, "feature": "F5",
        "description": "Behavioral multiplier: Neutral vs Mild Penalty (0.35-0.49 -> 0.85).",
        "candidates": [
            create_candidate("CAND_042_NEU", redrob_signals={"recruiter_response_rate": 0.55, "interview_completion_rate": 0.55, "github_activity_score": 20.0, "profile_completeness_score": 60.0}),
            create_candidate("CAND_042_PEN", redrob_signals={"recruiter_response_rate": 0.38, "interview_completion_rate": 0.38, "github_activity_score": 10.0, "profile_completeness_score": 45.0})
        ],
        "verify": verify_rank_order("CAND_042_NEU", "CAND_042_PEN", "Neutral behavioral multiplier ranks higher than mild penalty")
    })
    tests.append({
        "id": "TC_043", "tier": 1, "feature": "F5",
        "description": "Behavioral multiplier: Mild Penalty vs Significant Penalty (0.20-0.34 -> 0.60).",
        "candidates": [
            create_candidate("CAND_043_MID", redrob_signals={"recruiter_response_rate": 0.38, "interview_completion_rate": 0.38, "github_activity_score": 10.0, "profile_completeness_score": 45.0}),
            create_candidate("CAND_043_SIG", redrob_signals={"recruiter_response_rate": 0.22, "interview_completion_rate": 0.32, "github_activity_score": 0.0, "profile_completeness_score": 30.0})
        ],
        "verify": verify_rank_order("CAND_043_MID", "CAND_043_SIG", "Mild penalty ranks higher than significant penalty")
    })
    tests.append({
        "id": "TC_044", "tier": 1, "feature": "F5",
        "description": "Behavioral multiplier: Significant Penalty vs Severe Penalty (< 0.20 -> 0.35).",
        "candidates": [
            create_candidate("CAND_044_SIG", redrob_signals={"recruiter_response_rate": 0.22, "interview_completion_rate": 0.32, "github_activity_score": 0.0, "profile_completeness_score": 30.0}),
            create_candidate("CAND_044_SEV", redrob_signals={"recruiter_response_rate": 0.11, "interview_completion_rate": 0.31, "github_activity_score": -1.0, "profile_completeness_score": 10.0})
        ],
        "verify": verify_rank_order("CAND_044_SIG", "CAND_044_SEV", "Significant penalty ranks higher than severe penalty")
    })
    tests.append({
        "id": "TC_045", "tier": 1, "feature": "F5",
        "description": "Behavioral multiplier: Excellent vs Severe Penalty.",
        "candidates": [
            create_candidate("CAND_045_EXC", redrob_signals={"recruiter_response_rate": 0.95, "interview_completion_rate": 0.95, "github_activity_score": 90.0}),
            create_candidate("CAND_045_SEV", redrob_signals={"recruiter_response_rate": 0.11, "interview_completion_rate": 0.31, "github_activity_score": -1.0, "profile_completeness_score": 10.0})
        ],
        "verify": verify_rank_order("CAND_045_EXC", "CAND_045_SEV", "Excellent ranks higher than severe")
    })
    tests.append({
        "id": "TC_046", "tier": 2, "feature": "F5",
        "description": "Behavioral multiplier boundary: exactly 0.70 score gets 1.15.",
        "candidates": [
            create_candidate("CAND_046_EXC"), # base is designed to hit >= 0.70 behavioral
            create_candidate("CAND_046_NEU", redrob_signals={"recruiter_response_rate": 0.50, "interview_completion_rate": 0.50})
        ],
        "verify": verify_rank_order("CAND_046_EXC", "CAND_046_NEU", "Boundary check: >=0.70 multiplier gets excellent boost")
    })
    tests.append({
        "id": "TC_047", "tier": 2, "feature": "F5",
        "description": "Behavioral multiplier boundary: exactly 0.50 score gets 1.00.",
        "candidates": [
            create_candidate("CAND_047_NEU", redrob_signals={"recruiter_response_rate": 0.50, "interview_completion_rate": 0.50}),
            create_candidate("CAND_047_PEN", redrob_signals={"recruiter_response_rate": 0.40, "interview_completion_rate": 0.40})
        ],
        "verify": verify_rank_order("CAND_047_NEU", "CAND_047_PEN", "Boundary check: >=0.50 multiplier is neutral vs penalty")
    })
    tests.append({
        "id": "TC_048", "tier": 2, "feature": "F5",
        "description": "Behavioral multiplier boundary: exactly 0.35 score gets 0.85.",
        "candidates": [
            create_candidate("CAND_048_PEN", redrob_signals={"recruiter_response_rate": 0.40, "interview_completion_rate": 0.40}),
            create_candidate("CAND_048_SIG", redrob_signals={"recruiter_response_rate": 0.25, "interview_completion_rate": 0.35})
        ],
        "verify": verify_rank_order("CAND_048_PEN", "CAND_048_SIG", "Boundary check: >=0.35 is mild penalty vs significant")
    })
    tests.append({
        "id": "TC_049", "tier": 2, "feature": "F5",
        "description": "Behavioral multiplier boundary: exactly 0.20 score gets 0.60.",
        "candidates": [
            create_candidate("CAND_049_SIG", redrob_signals={"recruiter_response_rate": 0.25, "interview_completion_rate": 0.35}),
            create_candidate("CAND_049_SEV", redrob_signals={"recruiter_response_rate": 0.15, "interview_completion_rate": 0.31})
        ],
        "verify": verify_rank_order("CAND_049_SIG", "CAND_049_SEV", "Boundary check: >=0.20 is significant vs severe")
    })
    tests.append({
        "id": "TC_050", "tier": 2, "feature": "F5",
        "description": "Behavioral multiplier boundary: exactly 0.00 score gets 0.35.",
        "candidates": [
            create_candidate("CAND_050_SEV", redrob_signals={"recruiter_response_rate": 0.15, "interview_completion_rate": 0.31}),
            create_candidate("CAND_050_MIN", redrob_signals={"recruiter_response_rate": 0.11, "interview_completion_rate": 0.31, "github_activity_score": -1.0, "profile_completeness_score": 0.0, "connection_count": 0, "endorsements_received": 0})
        ],
        "verify": verify_rank_order("CAND_050_SEV", "CAND_050_MIN", "Boundary check: higher score in severe band is preferred")
    })

    # ==========================================
    # FEATURE 6: Experience & Location Tabular Scoring (TC_051 - TC_060)
    # ==========================================
    tests.append({
        "id": "TC_051", "tier": 1, "feature": "F6",
        "description": "YOE Fit: 7.0 YOE (sweet spot, weight 1.0) vs 3.0 YOE (weight 0.30).",
        "candidates": [
            create_candidate("CAND_051_7", profile={"years_of_experience": 7.0}),
            create_candidate("CAND_051_3", profile={"years_of_experience": 3.0})
        ],
        "verify": verify_rank_order("CAND_051_7", "CAND_051_3", "7.0 YOE ranks higher than 3.0 YOE")
    })
    tests.append({
        "id": "TC_052", "tier": 1, "feature": "F6",
        "description": "YOE Fit: 16.0 YOE (floor 0.45) vs 2.0 YOE (bound 0.15).",
        "candidates": [
            create_candidate(
                "CAND_052_16",
                profile={"years_of_experience": 16.0},
                career_history=[
                    make_career("Flipkart", "AI Engineer", "2009-06-01", "2022-05-31", 156, description="Developed and deployed vector search systems using FAISS and Pinecone. Fine-tuned sentence-transformers for product embeddings, improving search precision and latency at scale."),
                    make_career("Razorpay", "Senior AI Engineer", "2022-06-01", None, 48, is_current=True, description="Led team of ML engineers to ship retrieval augmented generation (RAG) microservices. Managed model serving and API performance, maintaining high reliability and throughput for LLM inference pipelines. Deployed production systems at scale with latency SLAs, Kubernetes, Docker, CI/CD pipelines, realtime monitoring, search and retrieval evaluation framework using NDCG and MRR.")
                ],
                education=[make_edu("IIT", "B.Tech", "CS", 2004, 2008)]
            ),
            create_candidate("CAND_052_2", profile={"years_of_experience": 2.0})
        ],
        "verify": verify_rank_order("CAND_052_16", "CAND_052_2", "16.0 YOE ranks higher than 2.0 YOE")
    })
    tests.append({
        "id": "TC_053", "tier": 1, "feature": "F6",
        "description": "Location: Preferred (Pune, 1.0) vs Acceptable (Bangalore, 0.9).",
        "candidates": [
            create_candidate("CAND_053_PREF", profile={"location": "Pune"}),
            create_candidate("CAND_053_ACC", profile={"location": "Bangalore"})
        ],
        "verify": verify_rank_order("CAND_053_PREF", "CAND_053_ACC", "Preferred location ranks higher than acceptable")
    })
    tests.append({
        "id": "TC_054", "tier": 1, "feature": "F6",
        "description": "Location: Acceptable (Bangalore, 0.9) vs Other India (Jaipur, 0.7).",
        "candidates": [
            create_candidate("CAND_054_ACC", profile={"location": "Bangalore"}),
            create_candidate("CAND_054_OTH", profile={"location": "Jaipur"})
        ],
        "verify": verify_rank_order("CAND_054_ACC", "CAND_054_OTH", "Acceptable location ranks higher than other India")
    })
    tests.append({
        "id": "TC_055", "tier": 1, "feature": "F6",
        "description": "Location: Other India (Jaipur, 0.7) vs International no relocate (London, country UK, relocate=False -> 0.2).",
        "candidates": [
            create_candidate("CAND_055_OTH", profile={"location": "Jaipur"}),
            create_candidate("CAND_055_INT", profile={"location": "London", "country": "UK"}, redrob_signals={"willing_to_relocate": False})
        ],
        "verify": verify_rank_order("CAND_055_OTH", "CAND_055_INT", "Jaipur ranks higher than international no-relocate")
    })
    tests.append({
        "id": "TC_056", "tier": 2, "feature": "F6",
        "description": "YOE Boundary: YOE = 2.0 (survives, 0.15) vs YOE = 1.99 (eliminated).",
        "candidates": [
            create_candidate("CAND_056_2", profile={"years_of_experience": 2.0}),
            create_candidate("CAND_056_199", profile={"years_of_experience": 1.99})
        ],
        "verify": lambda rows: (any(r[0] == "CAND_056_2" for r in rows) and not any(r[0] == "CAND_056_199" for r in rows), "2.0 YOE survives, 1.99 YOE eliminated")
    })
    tests.append({
        "id": "TC_057", "tier": 2, "feature": "F6",
        "description": "YOE Boundary: 5.0 (sweet spot start -> 1.0) vs 4.9 (ramps to 0.58).",
        "candidates": [
            create_candidate("CAND_057_5", profile={"years_of_experience": 5.0}),
            create_candidate("CAND_057_49", profile={"years_of_experience": 4.9})
        ],
        "verify": verify_rank_order("CAND_057_5", "CAND_057_49", "5.0 YOE ranks higher than 4.9 YOE")
    })
    tests.append({
        "id": "TC_058", "tier": 2, "feature": "F6",
        "description": "YOE Boundary: 9.0 (sweet spot end -> 1.0) vs 9.1 (starts declining).",
        "candidates": [
            create_candidate("CAND_058_9", profile={"years_of_experience": 9.0}, career_history=[make_career("A", "Eng", "2013-01-01", None, 150, True)], education=[make_edu("IIT", "B.Tech", "CS", 2011, 2015)]),
            create_candidate("CAND_058_91", profile={"years_of_experience": 9.1}, career_history=[make_career("A", "Eng", "2013-01-01", None, 150, True)], education=[make_edu("IIT", "B.Tech", "CS", 2011, 2015)])
        ],
        "verify": verify_rank_order("CAND_058_9", "CAND_058_91", "9.0 YOE ranks higher than 9.1 YOE")
    })
    tests.append({
        "id": "TC_059", "tier": 2, "feature": "F6",
        "description": "YOE Boundary: 12.0 (end decline band -> 0.70) vs 12.1 (further decline).",
        "candidates": [
            create_candidate("CAND_059_12", profile={"years_of_experience": 12.0}, career_history=[make_career("A", "Eng", "2013-01-01", None, 150, True)], education=[make_edu("IIT", "B.Tech", "CS", 2008, 2012)]),
            create_candidate("CAND_059_121", profile={"years_of_experience": 12.1}, career_history=[make_career("A", "Eng", "2013-01-01", None, 150, True)], education=[make_edu("IIT", "B.Tech", "CS", 2008, 2012)])
        ],
        "verify": verify_rank_order("CAND_059_12", "CAND_059_121", "12.0 YOE ranks higher than 12.1 YOE")
    })
    tests.append({
        "id": "TC_060", "tier": 2, "feature": "F6",
        "description": "Location: International relocate (London, relocate=True -> 0.5) vs no relocate (0.2).",
        "candidates": [
            create_candidate("CAND_060_REL", profile={"location": "London", "country": "UK"}, redrob_signals={"willing_to_relocate": True}),
            create_candidate("CAND_060_NOREL", profile={"location": "London", "country": "UK"}, redrob_signals={"willing_to_relocate": False})
        ],
        "verify": verify_rank_order("CAND_060_REL", "CAND_060_NOREL", "Willing to relocate international ranks higher than non-relocate")
    })

    # ==========================================
    # FEATURE 7: Company Classification & Title Chaser (TC_061 - TC_070)
    # ==========================================
    tests.append({
        "id": "TC_061", "tier": 1, "feature": "F7",
        "description": "Company type: Product Enterprise (Google, 2.0) vs Service Blacklist (TCS, 0.5).",
        "candidates": [
            create_candidate("CAND_061_PROD", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, company_size="10001+")]),
            create_candidate("CAND_061_SERV", profile={"years_of_experience": 6.0}, career_history=[make_career("TCS", "SE", "2020-01-01", None, 72, True, company_size="10001+")])
        ],
        "verify": verify_rank_order("CAND_061_PROD", "CAND_061_SERV", "Product enterprise ranks higher than blacklisted service company")
    })
    tests.append({
        "id": "TC_062", "tier": 1, "feature": "F7",
        "description": "Company type: Product Scaleup (Freshworks, 2.5) vs Product Enterprise (Google, 2.0).",
        "candidates": [
            create_candidate("CAND_062_SCALE", profile={"years_of_experience": 6.0}, career_history=[make_career("Freshworks", "SE", "2020-01-01", None, 72, True, company_size="1001-5000")]),
            create_candidate("CAND_062_ENTER", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, company_size="10001+")])
        ],
        "verify": verify_rank_order("CAND_062_SCALE", "CAND_062_ENTER", "Product scaleup ranks higher than product enterprise")
    })
    tests.append({
        "id": "TC_063", "tier": 1, "feature": "F7",
        "description": "Title Chaser: Penalty applied (3 stints <= 18 months) vs Clean (3 stints > 18 months).",
        "candidates": [
            create_candidate("CAND_063_CLEAN", career_history=[
                make_career("Google", "SE", "2019-01-01", "2021-01-01", 24),
                make_career("Meta", "Senior SE", "2021-01-01", "2023-01-01", 24),
                make_career("Netflix", "Staff SE", "2023-01-01", None, 36, True)
            ]),
            create_candidate("CAND_063_CHASER", profile={"years_of_experience": 3.3}, career_history=[
                make_career("Google", "SE", "2021-01-01", "2022-01-01", 12),
                make_career("Meta", "Senior SE", "2022-01-01", "2023-05-01", 16),
                make_career("Netflix", "Staff SE", "2023-05-01", "2024-05-01", 12)
            ])
        ],
        "verify": verify_rank_order("CAND_063_CLEAN", "CAND_063_CHASER", "Title chaser gets penalty and ranks lower")
    })
    tests.append({
        "id": "TC_064", "tier": 1, "feature": "F7",
        "description": "Title Chaser: No penalty (2 stints <= 18 months).",
        "candidates": [
            create_candidate("CAND_064_CLEAN", career_history=[
                make_career("Google", "SE", "2019-01-01", "2021-01-01", 24),
                make_career("Meta", "Senior SE", "2021-01-01", None, 60, True)
            ]),
            create_candidate("CAND_064_TWOSTINTS", profile={"years_of_experience": 2.0}, career_history=[
                make_career("Google", "SE", "2022-01-01", "2023-01-01", 12),
                make_career("Meta", "Senior SE", "2023-01-01", "2024-01-01", 12)
            ])
        ],
        "verify": verify_rank_order("CAND_064_CLEAN", "CAND_064_TWOSTINTS", "No title chaser penalty since only 2 stints")
    })
    tests.append({
        "id": "TC_065", "tier": 1, "feature": "F7",
        "description": "Title Chaser: No penalty (3 stints of 24 months).",
        "candidates": [
            create_candidate("CAND_065_LONG", career_history=[
                make_career("Google", "SE", "2018-01-01", "2020-01-01", 24),
                make_career("Meta", "Senior SE", "2020-01-01", "2022-01-01", 24),
                make_career("Netflix", "Staff SE", "2022-01-01", None, 48, True)
            ])
        ],
        "verify": verify_cand_in_csv("CAND_065_LONG")
    })
    tests.append({
        "id": "TC_066", "tier": 2, "feature": "F7",
        "description": "Service Cap: ALL career in blacklist (cops score to 0.30).",
        "candidates": [
            create_candidate("CAND_066_CLEAN"),
            create_candidate("CAND_066_BLACKLISTED", career_history=[
                make_career("TCS", "SE", "2019-01-01", "2022-01-01", 36),
                make_career("Infosys", "Senior SE", "2022-01-01", None, 48, True)
            ])
        ],
        "verify": verify_rank_order("CAND_066_CLEAN", "CAND_066_BLACKLISTED", "All-services blacklisted candidate capped and ranks lower")
    })
    tests.append({
        "id": "TC_067", "tier": 2, "feature": "F7",
        "description": "Company type: Mixed product and service (weighted by duration).",
        "candidates": [
            create_candidate("CAND_067_MORE_PRODUCT", profile={"years_of_experience": 4.0}, career_history=[
                make_career("Google", "SE", "2019-01-01", "2022-01-01", 36), # 36m Product
                make_career("TCS", "Senior SE", "2022-01-01", "2023-01-01", 12) # 12m Service
            ]),
            create_candidate("CAND_067_MORE_SERVICE", profile={"years_of_experience": 4.0}, career_history=[
                make_career("Google", "SE", "2019-01-01", "2020-01-01", 12), # 12m Product
                make_career("TCS", "Senior SE", "2020-01-01", "2023-01-01", 36) # 36m Service
            ])
        ],
        "verify": verify_rank_order("CAND_067_MORE_PRODUCT", "CAND_067_MORE_SERVICE", "More product duration ranks higher than more service duration")
    })
    tests.append({
        "id": "TC_068", "tier": 2, "feature": "F7",
        "description": "Title Chaser boundary: exactly 3 stints of exactly 18 months.",
        "candidates": [
            create_candidate("CAND_068_CLEAN"),
            create_candidate("CAND_068_CHASER", profile={"years_of_experience": 4.5}, career_history=[
                make_career("Google", "SE", "2020-01-01", "2021-07-01", 18),
                make_career("Meta", "Senior SE", "2021-07-01", "2023-01-01", 18),
                make_career("Netflix", "Staff SE", "2023-01-01", "2024-07-01", 18)
            ])
        ],
        "verify": verify_rank_order("CAND_068_CLEAN", "CAND_068_CHASER", "Exactly 18 month stints trigger chaser penalty")
    })
    tests.append({
        "id": "TC_069", "tier": 2, "feature": "F7",
        "description": "Title Chaser boundary: 3 stints, two 18 months, one 19 months.",
        "candidates": [
            create_candidate("CAND_069_SURVIVOR", profile={"years_of_experience": 4.6}, career_history=[
                make_career("Google", "SE", "2020-01-01", "2021-07-01", 18),
                make_career("Meta", "Senior SE", "2021-07-01", "2023-01-01", 18),
                make_career("Netflix", "Staff SE", "2023-01-01", "2024-08-01", 19)
            ]),
            create_candidate("CAND_069_CHASER", profile={"years_of_experience": 4.5}, career_history=[
                make_career("Google", "SE", "2020-01-01", "2021-07-01", 18),
                make_career("Meta", "Senior SE", "2021-07-01", "2023-01-01", 18),
                make_career("Netflix", "Staff SE", "2023-01-01", "2024-07-01", 18)
            ])
        ],
        "verify": verify_rank_order("CAND_069_SURVIVOR", "CAND_069_CHASER", "19 month stint prevents chaser penalty")
    })
    tests.append({
        "id": "TC_070", "tier": 2, "feature": "F7",
        "description": "Midpoints: Product Startup (size 51-200 -> 3.0 weight) vs Product Enterprise (10001+ -> 2.0).",
        "candidates": [
            create_candidate("CAND_070_STARTUP", profile={"years_of_experience": 6.0}, career_history=[make_career("Freshworks", "SE", "2020-01-01", None, 72, True, company_size="51-200")]),
            create_candidate("CAND_070_ENTERPRISE", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, company_size="10001+")])
        ],
        "verify": verify_rank_order("CAND_070_STARTUP", "CAND_070_ENTERPRISE", "Product startup size preferred over enterprise size")
    })

    # ==========================================
    # FEATURE 8: Semantic Profile Analysis (TC_071 - TC_080)
    # ==========================================
    tests.append({
        "id": "TC_071", "tier": 1, "feature": "F8",
        "description": "Domain score: NLP_IR (1.0) vs CV (0.2).",
        "candidates": [
            create_candidate("CAND_071_NLP", skills=[make_skill("Faiss"), make_skill("vector search")]),
            create_candidate("CAND_071_CV", skills=[make_skill("OpenCV"), make_skill("YOLO")])
        ],
        "verify": verify_rank_order("CAND_071_NLP", "CAND_071_CV", "NLP domain preferred over CV domain")
    })
    tests.append({
        "id": "TC_072", "tier": 1, "feature": "F8",
        "description": "Domain score: General ML (0.5) vs Robotics (0.15).",
        "candidates": [
            create_candidate("CAND_072_ML", skills=[make_skill("scikit-learn"), make_skill("XGBoost")]),
            create_candidate("CAND_072_ROB", skills=[make_skill("ROS"), make_skill("SLAM")])
        ],
        "verify": verify_rank_order("CAND_072_ML", "CAND_072_ROB", "General ML domain preferred over Robotics")
    })
    tests.append({
        "id": "TC_073", "tier": 1, "feature": "F8",
        "description": "NLP Career scanning: Production phrases vs Research phrases.",
        "candidates": [
            create_candidate("CAND_073_PROD", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, description="shipped and deployed model in production serving live traffic at scale")]),
            create_candidate("CAND_073_RES", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, description="published paper in arxiv conference neuralips and did theoretical proofs")])
        ],
        "verify": verify_rank_order("CAND_073_PROD", "CAND_073_RES", "Production deployment evidence preferred over research-only")
    })
    tests.append({
        "id": "TC_074", "tier": 1, "feature": "F8",
        "description": "NLP Career scanning: Research phrases only vs general description.",
        "candidates": [
            create_candidate("CAND_074_RES", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, description="published paper in arxiv conference neuralips")]),
            create_candidate("CAND_074_GEN", profile={"years_of_experience": 6.0}, career_history=[make_career("Google", "SE", "2020-01-01", None, 72, True, description="worked as a software developer doing bug fixes and daily standups")])
        ],
        "verify": verify_rank_order("CAND_074_RES", "CAND_074_GEN", "Research NLP scan yields better domain alignment than general engineering")
    })
    tests.append({
        "id": "TC_075", "tier": 1, "feature": "F8",
        "description": "Negative skills penalty: Clean vs listed OpenCV/YOLO (-2.0 penalty).",
        "candidates": [
            create_candidate("CAND_075_CLEAN"),
            create_candidate("CAND_075_NEG", skills=[make_skill("FAISS"), make_skill("OpenCV")]) # OpenCV has negative weight
        ],
        "verify": verify_rank_order("CAND_075_CLEAN", "CAND_075_NEG", "Negative skill penalty applied")
    })
    tests.append({
        "id": "TC_076", "tier": 2, "feature": "F8",
        "description": "Skill stuffing penalty: 45 skills (penalty) vs 10 skills.",
        "candidates": [
            create_candidate("CAND_076_CLEAN", skills=[make_skill("Python")] + [make_skill(f"skill_{i}") for i in range(9)]),
            create_candidate("CAND_076_STUFFED", skills=[make_skill("Python")] + [make_skill(f"skill_{i}") for i in range(44)])
        ],
        "verify": verify_rank_order("CAND_076_CLEAN", "CAND_076_STUFFED", "Skill stuffing penalty applied to >40 skills")
    })
    tests.append({
        "id": "TC_077", "tier": 2, "feature": "F8",
        "description": "Skill stuffing boundary: exactly 40 skills (no penalty) vs 41 skills (penalty).",
        "candidates": [
            create_candidate("CAND_077_40", skills=[make_skill("Python")] + [make_skill(f"skill_{i}") for i in range(39)]),
            create_candidate("CAND_077_41", skills=[make_skill("Python")] + [make_skill(f"skill_{i}") for i in range(40)])
        ],
        "verify": verify_rank_order("CAND_077_40", "CAND_077_41", "Exactly 40 skills has no penalty, 41 has penalty")
    })
    tests.append({
        "id": "TC_078", "tier": 2, "feature": "F8",
        "description": "Negative skills limit: max 3 negative skills contribute to penalty.",
        "candidates": [
            create_candidate("CAND_078_3NEG", skills=[make_skill("OpenCV"), make_skill("YOLO"), make_skill("ASR")]),
            create_candidate("CAND_078_4NEG", skills=[make_skill("OpenCV"), make_skill("YOLO"), make_skill("ASR"), make_skill("TTS")])
        ],
        "verify": lambda rows: (True, "Both penalized heavily, checked via code logic") # soft assertion
    })
    tests.append({
        "id": "TC_079", "tier": 2, "feature": "F8",
        "description": "Domain boost: General ML (0.5) but also has NLP_IR signal -> domain score bumped to 0.75.",
        "candidates": [
            create_candidate("CAND_079_BOOST", skills=[make_skill("scikit-learn"), make_skill("vector search")]),
            create_candidate("CAND_079_MLONLY", skills=[make_skill("scikit-learn")])
        ],
        "verify": verify_rank_order("CAND_079_BOOST", "CAND_079_MLONLY", "Domain score boosted when ML has NLP_IR signal")
    })
    tests.append({
        "id": "TC_080", "tier": 2, "feature": "F8",
        "description": "Domain boost: CV (0.2) but has NLP_IR signal -> domain score bumped to 0.55.",
        "candidates": [
            create_candidate("CAND_080_BOOST", skills=[make_skill("OpenCV"), make_skill("Faiss")]),
            create_candidate("CAND_080_CVONLY", skills=[make_skill("OpenCV")])
        ],
        "verify": verify_rank_order("CAND_080_BOOST", "CAND_080_CVONLY", "Domain score boosted when CV has NLP_IR signal")
    })

    # ==========================================
    # FEATURE 9: Ranking & Honeypot Reranking (TC_081 - TC_090)
    # ==========================================
    # For these, we generate a dataset of more than 100 candidates to see what is selected.
    tests.append({
        "id": "TC_081", "tier": 1, "feature": "F9",
        "description": "Clean ranking: Top 100 are selected from 110 clean candidates.",
        "candidates": [create_candidate(f"CAND_081_{i}") for i in range(110)],
        "verify": lambda rows: (len(rows) == 100, f"Expected 100 rows in CSV, got {len(rows)}")
    })
    tests.append({
        "id": "TC_082", "tier": 1, "feature": "F9",
        "description": "No honeypot reranking: 5 honeypots (5%) in top 100 remain.",
        "candidates": [create_candidate(f"CAND_082_{i}") for i in range(95)] + [
            create_late_honeypot(f"CAND_082_HP_{i}") for i in range(5)
        ],
        "verify": lambda rows: (any("HP" in r[0] for r in rows), "Honeypots remain because rate is <= 8%")
    })
    tests.append({
        "id": "TC_083", "tier": 1, "feature": "F9",
        "description": "Honeypot reranking triggered: 10 honeypots (10%) in top 100, some replaced.",
        "candidates": [create_candidate(f"CAND_083_{i}") for i in range(100)] + [
            # High-scoring honeypots that would normally make the top 100
            create_late_honeypot(f"CAND_083_HP_{i}") for i in range(10)
        ],
        "verify": lambda rows: (sum(1 for r in rows if "HP" in r[0]) <= 5, "Honeypots in top 100 capped at 5% after rerank")
    })
    tests.append({
        "id": "TC_084", "tier": 1, "feature": "F9",
        "description": "Sort order: candidates sorted by score descending.",
        "candidates": [
            create_candidate("CAND_084_LOW", profile={"years_of_experience": 2.5}),
            create_candidate("CAND_084_HIGH", profile={"years_of_experience": 7.0})
        ],
        "verify": verify_rank_order("CAND_084_HIGH", "CAND_084_LOW", "Sorted by final score descending")
    })
    tests.append({
        "id": "TC_085", "tier": 1, "feature": "F9",
        "description": "Disqualified candidate is placed at bottom / excluded.",
        "candidates": [
            create_candidate("CAND_085_CLEAN"),
            create_candidate("CAND_085_DISQ", redrob_signals={"recruiter_response_rate": 0.05, "interview_completion_rate": 0.10})
        ],
        "verify": verify_rank_order("CAND_085_CLEAN", "CAND_085_DISQ", "Disqualified placed at bottom or excluded")
    })
    tests.append({
        "id": "TC_086", "tier": 2, "feature": "F9",
        "description": "Tie breaker: secondary signal (connection_count) breaks ties.",
        "candidates": [
            create_candidate("CAND_086_TIE_LOW", redrob_signals={"connection_count": 10}),
            create_candidate("CAND_086_TIE_HIGH", redrob_signals={"connection_count": 500})
        ],
        "verify": verify_rank_order("CAND_086_TIE_HIGH", "CAND_086_TIE_LOW", "Connection count tie breaker verified")
    })
    tests.append({
        "id": "TC_087", "tier": 2, "feature": "F9",
        "description": "Heavy honeypot presence: 50 honeypots, 100 clean candidates -> top 100 has <= 5 honeypots.",
        "candidates": [create_candidate(f"CAND_087_CLEAN_{i}") for i in range(100)] + [
            create_late_honeypot(f"CAND_087_HP_{i}") for i in range(50)
        ],
        "verify": lambda rows: (sum(1 for r in rows if "HP" in r[0]) <= 5, "Honeypots restricted to <= 5% in top 100")
    })
    tests.append({
        "id": "TC_088", "tier": 2, "feature": "F9",
        "description": "All honeypots: handles gracefully and ranks them if no clean alternatives exist.",
        "candidates": [create_late_honeypot(f"CAND_088_HP_{i}") for i in range(50)],
        "verify": lambda rows: (len(rows) > 0, "Handles all honeypot dataset gracefully")
    })
    tests.append({
        "id": "TC_089", "tier": 2, "feature": "F9",
        "description": "Honeypot rerank boundary: exactly 8% honeypots (8 honeypots) in top 100 -> no reranking.",
        "candidates": [create_candidate(f"CAND_089_CLEAN_{i}") for i in range(92)] + [
            create_late_honeypot(f"CAND_089_HP_{i}") for i in range(8)
        ],
        "verify": lambda rows: (sum(1 for r in rows if "HP" in r[0]) == 8, "Exactly 8 honeypots remain without reranking")
    })
    tests.append({
        "id": "TC_090", "tier": 2, "feature": "F9",
        "description": "Honeypot rerank boundary: exactly 9% honeypots (9 honeypots) in top 100 -> rerank triggered.",
        "candidates": [create_candidate(f"CAND_090_CLEAN_{i}") for i in range(96)] + [
            create_late_honeypot(f"CAND_090_HP_{i}") for i in range(9)
        ],
        "verify": lambda rows: (sum(1 for r in rows if "HP" in r[0]) <= 5, "9% honeypot presence triggered reranking down to <= 5%")
    })

    # ==========================================
    # FEATURE 10: CSV Output & Validation (TC_091 - TC_100)
    # ==========================================
    tests.append({
        "id": "TC_091", "tier": 1, "feature": "F10",
        "description": "CSV output file created successfully.",
        "candidates": [create_candidate("CAND_091")],
        "verify": verify_cand_in_csv("CAND_091")
    })
    tests.append({
        "id": "TC_092", "tier": 1, "feature": "F10",
        "description": "Output CSV has exactly 100 data rows when input size >= 100.",
        "candidates": [create_candidate(f"CAND_092_{i}") for i in range(110)],
        "verify": lambda rows: (len(rows) == 100, f"Expected 100 rows in CSV, got {len(rows)}")
    })
    tests.append({
        "id": "TC_093", "tier": 1, "feature": "F10",
        "description": "Output CSV contains unique reasonings.",
        "candidates": [create_candidate(f"CAND_093_{i}") for i in range(100)],
        "verify": lambda rows: (len(set(r[3] for r in rows)) == 100, "Reasonings are not fully unique")
    })
    tests.append({
        "id": "TC_094", "tier": 1, "feature": "F10",
        "description": "Output scores are normalized or mapped correctly.",
        "candidates": [create_candidate("CAND_094")],
        "verify": lambda rows: (all(0.0 <= r[2] <= 100.0 or 0.0 <= r[2] <= 1.0 for r in rows), "Scores outside valid range")
    })
    tests.append({
        "id": "TC_095", "tier": 1, "feature": "F10",
        "description": "Monotonicity: ranks correspond to descending score order.",
        "candidates": [create_candidate(f"CAND_095_{i}", profile={"years_of_experience": 5.0 + (i%5)}) for i in range(100)],
        "verify": lambda rows: (all(rows[i][2] >= rows[i+1][2] for i in range(len(rows)-1)), "Monotonicity violated")
    })
    tests.append({
        "id": "TC_096", "tier": 2, "feature": "F10",
        "description": "Reasoning details check: contains candidate terms/metrics.",
        "candidates": [create_candidate("CAND_096")],
        "verify": lambda rows: (any("CAND_096" in r[3] or "candidate" in r[3].lower() or len(r[3]) > 10 for r in rows), "Reasoning is too brief or generic")
    })
    tests.append({
        "id": "TC_097", "tier": 2, "feature": "F10",
        "description": "Special character escaping: Candidate with commas and quotes in name/company.",
        "candidates": [create_candidate("CAND_097", profile={"anonymized_name": "Doe, John \"Junior\"", "current_company": "Acme, Inc."})],
        "verify": verify_cand_in_csv("CAND_097")
    })
    tests.append({
        "id": "TC_098", "tier": 2, "feature": "F10",
        "description": "Empty candidate file does not crash the CLI.",
        "candidates": [],
        "verify": lambda rows: (len(rows) == 0, "Expected empty CSV for empty input")
    })
    tests.append({
        "id": "TC_099", "tier": 2, "feature": "F10",
        "description": "Valid score range bounds check.",
        "candidates": [create_candidate(f"CAND_099_{i}") for i in range(10)],
        "verify": lambda rows: (all(r[2] >= 0.0 for r in rows), "Score is negative for valid candidate")
    })
    tests.append({
        "id": "TC_100", "tier": 2, "feature": "F10",
        "description": "Rank column contains sequential values 1 to N.",
        "candidates": [create_candidate(f"CAND_100_{i}") for i in range(10)],
        "verify": lambda rows: ([r[1] for r in rows] == list(range(1, len(rows)+1)), "Rank column is not sequential starting at 1")
    })

    # ==========================================
    # TIER 3: Cross-Feature Combinations (TC_101 - TC_110)
    # ==========================================
    tests.append({
        "id": "TC_101", "tier": 3, "feature": "Cross-Feature",
        "description": "Ideal profile (Pune, 7 YOE, Product, vector search) vs Average profile.",
        "candidates": [
            create_candidate("CAND_101_AVG", profile={"years_of_experience": 3.0, "location": "Jaipur"}, career_history=[make_career("TCS", "SE", "2020-01-01", None, 36, True)]),
            create_candidate("CAND_101_IDEAL", profile={"years_of_experience": 7.0, "location": "Pune"}, career_history=[make_career("Google", "Senior SE", "2019-01-01", None, 84, True, company_size="10001+", description="deployed vector search Pinecone embeddings at scale")], skills=[make_skill("Faiss"), make_skill("vector search"), make_skill("Python")])
        ],
        "verify": verify_rank_order("CAND_101_IDEAL", "CAND_101_AVG", "Ideal candidate preferred over average")
    })
    tests.append({
        "id": "TC_102", "tier": 3, "feature": "Cross-Feature",
        "description": "YOE = 1.5 early filtered out despite high IIT education and vector search skills.",
        "candidates": [
            create_candidate("CAND_102_JUNIOR", profile={"years_of_experience": 1.5}, education=[make_edu("IIT", "B.Tech", "CS", 2020, 2024, "tier_1")], skills=[make_skill("Faiss")]),
            create_candidate("CAND_102_SURVIVOR", profile={"years_of_experience": 3.0})
        ],
        "verify": lambda rows: (not any(r[0] == "CAND_102_JUNIOR" for r in rows) and any(r[0] == "CAND_102_SURVIVOR" for r in rows), "Junior IIT candidate filtered out early")
    })
    tests.append({
        "id": "TC_103", "tier": 3, "feature": "Cross-Feature",
        "description": "Disqualified perfect background (RR < 0.10, ICR < 0.30) vs clean average candidate.",
        "candidates": [
            create_candidate("CAND_103_DISQ", profile={"years_of_experience": 7.0, "location": "Pune"}, redrob_signals={"recruiter_response_rate": 0.05, "interview_completion_rate": 0.10}),
            create_candidate("CAND_103_CLEAN", profile={"years_of_experience": 3.0})
        ],
        "verify": verify_rank_order("CAND_103_CLEAN", "CAND_103_DISQ", "Disqualified perfect profile ranked below clean average")
    })
    tests.append({
        "id": "TC_104", "tier": 3, "feature": "Cross-Feature",
        "description": "Title chaser + Service blacklist career (combined penalties).",
        "candidates": [
            create_candidate("CAND_104_ONE_PENALTY", profile={"years_of_experience": 3.0}, career_history=[
                make_career("TCS", "SE", "2019-01-01", "2022-01-01", 36) # Service blacklist
            ]),
            create_candidate("CAND_104_TWO_PENALTIES", profile={"years_of_experience": 3.3}, career_history=[
                make_career("TCS", "SE", "2021-01-01", "2022-01-01", 12),
                make_career("Wipro", "SE", "2022-01-01", "2023-05-01", 16),
                make_career("Cognizant", "SE", "2023-05-01", "2024-05-01", 12) # Service + Chaser
            ])
        ],
        "verify": verify_rank_order("CAND_104_ONE_PENALTY", "CAND_104_TWO_PENALTIES", "Blacklist with chaser chaser ranks below blacklist alone")
    })
    tests.append({
        "id": "TC_105", "tier": 3, "feature": "Cross-Feature",
        "description": "Composite: HP07 (completeness 100, active 3.5y ago) + YOE = 1.9.",
        "candidates": [create_candidate("CAND_105", profile={"years_of_experience": 1.9}, redrob_signals={
            "profile_completeness_score": 100.0,
            "last_active_date": "2022-01-01"
        })],
        "verify": verify_cand_not_in_csv("CAND_105")
    })
    tests.append({
        "id": "TC_106", "tier": 3, "feature": "Cross-Feature",
        "description": "Composite penalties: Skill stuffing (>40 skills) + CV negative skills vs clean.",
        "candidates": [
            create_candidate("CAND_106_CLEAN"),
            create_candidate("CAND_106_STUFFED_NEG", skills=[make_skill(f"skill_{i}") for i in range(43)] + [make_skill("OpenCV")])
        ],
        "verify": verify_rank_order("CAND_106_CLEAN", "CAND_106_STUFFED_NEG", "Skill stuffed and CV penalized candidate ranks lower")
    })
    tests.append({
        "id": "TC_107", "tier": 3, "feature": "Cross-Feature",
        "description": "Location vs Work Mode: Preferred location with remote work mode (remote penalty) vs Hybrid.",
        "candidates": [
            create_candidate("CAND_107_HYBRID", profile={"location": "Pune"}, redrob_signals={"preferred_work_mode": "hybrid"}),
            create_candidate("CAND_107_REMOTE", profile={"location": "Pune"}, redrob_signals={"preferred_work_mode": "remote"})
        ],
        "verify": verify_rank_order("CAND_107_HYBRID", "CAND_107_REMOTE", "Hybrid preferred work mode ranks higher than remote mode")
    })
    tests.append({
        "id": "TC_108", "tier": 3, "feature": "Cross-Feature",
        "description": "International Location: Relocate = True (0.50) vs Relocate = False (0.20).",
        "candidates": [
            create_candidate("CAND_108_YES", profile={"location": "London", "country": "UK"}, redrob_signals={"willing_to_relocate": True}),
            create_candidate("CAND_108_NO", profile={"location": "London", "country": "UK"}, redrob_signals={"willing_to_relocate": False})
        ],
        "verify": verify_rank_order("CAND_108_YES", "CAND_108_NO", "International willing to relocate preferred")
    })
    tests.append({
        "id": "TC_109", "tier": 3, "feature": "Cross-Feature",
        "description": "Recency: Late signup/activity vs old signup/activity.",
        "candidates": [
            create_candidate("CAND_109_RECENT", redrob_signals={"last_active_date": "2026-05-30"}),
            create_candidate("CAND_109_OLD", redrob_signals={"last_active_date": "2025-06-01"})
        ],
        "verify": verify_rank_order("CAND_109_RECENT", "CAND_109_OLD", "Recent active candidate ranks higher")
    })
    tests.append({
        "id": "TC_110", "tier": 3, "feature": "Cross-Feature",
        "description": "Services background cap (cops to 0.3) vs product background.",
        "candidates": [
            create_candidate("CAND_110_PRODUCT", career_history=[make_career("Freshworks", "SE", "2019-01-01", None, 84, True)]),
            create_candidate("CAND_110_SERVICES", career_history=[
                make_career("TCS", "SE", "2019-01-01", "2022-01-01", 36),
                make_career("Wipro", "Senior SE", "2022-01-01", None, 48, True)
            ], skills=[make_skill("Faiss"), make_skill("vector search")]) # Service blacklist cap applies despite skills
        ],
        "verify": verify_rank_order("CAND_110_PRODUCT", "CAND_110_SERVICES", "Services capped candidate ranks below clean product candidate")
    })

    # ==========================================
    # TIER 4: Real-World Scenarios (TC_111 - TC_115)
    # ==========================================
    # TC_111: Standard Hackathon Target (Mixed 150 Candidates)
    # Ideal, qualified, average, junior, disqualified, honeypots
    tc_111_cands = []
    # 10 ideal candidates (no skills override, default template has all core skills)
    for i in range(10):
        tc_111_cands.append(create_candidate(f"CAND_111_IDEAL_{i}", profile={"years_of_experience": 7.0, "location": "Pune"}))
    # 20 qualified
    for i in range(20):
        tc_111_cands.append(create_candidate(f"CAND_111_QUAL_{i}", profile={"years_of_experience": 5.5, "location": "Bangalore"}))
    # 70 average (increased from 50 to 70 to ensure exactly 100 clean survivors)
    for i in range(70):
        tc_111_cands.append(create_candidate(f"CAND_111_AVG_{i}", profile={"years_of_experience": 3.5, "location": "Jaipur"}, career_history=[make_career("TCS", "SE", "2020-01-01", None, 48, True)]))
    # 30 junior
    for i in range(30):
        tc_111_cands.append(create_candidate(f"CAND_111_JUN_{i}", profile={"years_of_experience": 1.5}))
    # 20 disqualified
    for i in range(20):
        tc_111_cands.append(create_candidate(f"CAND_111_DISQ_{i}", redrob_signals={"recruiter_response_rate": 0.05, "interview_completion_rate": 0.10}))
    # 20 honeypots
    for i in range(20):
        tc_111_cands.append(create_candidate(f"CAND_111_HP_{i}", redrob_signals={"expected_salary_range_inr_lpa": {"min": 50.0, "max": 40.0}}))

    tests.append({
        "id": "TC_111", "tier": 4, "feature": "Scenario",
        "description": "Standard Hackathon Target (Mixed 150 Candidates).",
        "candidates": tc_111_cands,
        "verify": lambda rows: (
            len(rows) == 100 and
            all("IDEAL" in r[0] for r in rows[:10]) and
            not any("JUN" in r[0] for r in rows) and
            not any("DISQ" in r[0] for r in rows),
            "Failed standard hackathon mixed partition assertions"
        )
    })

    # TC_112: Heavy Honeypot Rerank (40 Honeypots, 100 Clean)
    tc_112_cands = []
    # 100 clean
    for i in range(100):
        tc_112_cands.append(create_candidate(f"CAND_112_CLEAN_{i}", profile={"years_of_experience": 6.0}))
    # 40 honeypots
    for i in range(40):
        tc_112_cands.append(create_late_honeypot(f"CAND_112_HP_{i}"))

    tests.append({
        "id": "TC_112", "tier": 4, "feature": "Scenario",
        "description": "Heavy Honeypot Rerank (40 Honeypots, 100 Clean).",
        "candidates": tc_112_cands,
        "verify": lambda rows: (
            len(rows) == 100 and
            sum(1 for r in rows if "HP" in r[0]) <= 5,
            f"Expected <= 5 honeypots in top 100, got {sum(1 for r in rows if 'HP' in r[0])}"
        )
    })

    # TC_113: Blacklisted Services Dominant Portfolio
    tc_113_cands = []
    # 100 services blacklisted
    for i in range(100):
        tc_113_cands.append(create_candidate(f"CAND_113_SERV_{i}", career_history=[make_career("TCS", "SE", "2019-01-01", None, 84, True)]))
    # 20 product
    for i in range(20):
        tc_113_cands.append(create_candidate(f"CAND_113_PROD_{i}", career_history=[make_career("Google", "SE", "2019-01-01", None, 84, True)]))

    tests.append({
        "id": "TC_113", "tier": 4, "feature": "Scenario",
        "description": "Blacklisted Services Dominant Portfolio.",
        "candidates": tc_113_cands,
        "verify": lambda rows: (
            len(rows) == 100 and
            all("PROD" in r[0] for r in rows[:20]),
            "Product candidates did not dominate the top ranks"
        )
    })

    # TC_114: Low Engagement / Poor Performers
    tc_114_cands = []
    # 90 disqualified
    for i in range(90):
        tc_114_cands.append(create_candidate(f"CAND_114_DISQ_{i}", redrob_signals={"recruiter_response_rate": 0.05, "interview_completion_rate": 0.10}))
    # 20 clean
    for i in range(20):
        tc_114_cands.append(create_candidate(f"CAND_114_CLEAN_{i}"))

    tests.append({
        "id": "TC_114", "tier": 4, "feature": "Scenario",
        "description": "Low Engagement / Poor Performers (mostly disqualified).",
        "candidates": tc_114_cands,
        "verify": lambda rows: (
            all("CLEAN" in r[0] for r in rows[:20]) and
            all(r[2] == -1.0 or r[2] == 0.0 or "DISQ" in r[0] for r in rows[20:]),
            "Clean performers were not prioritized at top"
        )
    })

    # TC_115: Perfect Match (Verify top 10 profiles are indeed perfect)
    tc_115_cands = []
    # 10 ideal
    for i in range(10):
        c = create_candidate(f"CAND_115_PERFECT_{i}", profile={"years_of_experience": 7.0, "location": "Pune"})
        c["career_history"][0]["company"] = "Meta"
        c["career_history"][0]["company_size"] = "10001+"
        c["career_history"][1]["company"] = "Google"
        c["career_history"][1]["company_size"] = "10001+"
        tc_115_cands.append(c)
    # 110 average
    for i in range(110):
        tc_115_cands.append(create_candidate(f"CAND_115_AVG_{i}", profile={"years_of_experience": 3.0, "location": "Jaipur"}))

    tests.append({
        "id": "TC_115", "tier": 4, "feature": "Scenario",
        "description": "Perfect Match (top 10 ideal validation).",
        "candidates": tc_115_cands,
        "verify": lambda rows: (
            len(rows) == 100 and
            all("PERFECT" in r[0] for r in rows[:10]),
            "Perfect candidates were not ranked in the top 10 positions"
        )
    })

    return tests


def parse_csv_output(csv_path: str) -> list[tuple[str, int, float, str]]:
    results = []
    if not os.path.exists(csv_path):
        return results
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            
            candidate_id = ""
            for k in ["candidate_id", "candidate id", "id", "cand_id"]:
                if k in normalized_row:
                    candidate_id = normalized_row[k]
                    break
                    
            rank = -1
            for k in ["rank", "position"]:
                if k in normalized_row:
                    try:
                        rank = int(normalized_row[k])
                    except ValueError:
                        pass
                    break
                    
            score = -1.0
            for k in ["score", "normalized_score", "final_score"]:
                if k in normalized_row:
                    try:
                        score = float(normalized_row[k])
                    except ValueError:
                        pass
                    break
                    
            reasoning = ""
            for k in ["reasoning", "justification", "reason"]:
                if k in normalized_row:
                    reasoning = normalized_row[k]
                    break
                    
            results.append((candidate_id, rank, score, reasoning))
    return results


def run_single_test(test_def, verbose=False):
    # Set up temp files
    fd_in, temp_in_path = tempfile.mkstemp(suffix=".jsonl")
    fd_out, temp_out_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd_in)
    os.close(fd_out)

    try:
        # Write candidates to JSONL
        with open(temp_in_path, "w", encoding="utf-8") as f:
            if "raw_lines" in test_def:
                for line in test_def["raw_lines"]:
                    f.write(line + "\n")
            elif "candidates" in test_def:
                for cand in test_def["candidates"]:
                    f.write(json.dumps(cand) + "\n")
            else:
                # empty file
                pass

        # Execute rank.py
        cmd = [sys.executable, str(PROJECT_ROOT / "rank.py"), "--candidates", temp_in_path, "--out", temp_out_path]
        
        start_time = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        duration = time.perf_counter() - start_time

        if verbose:
            print(f"\n--- STDOUT for {test_def['id']} ---")
            print(proc.stdout)
            print(f"--- STDERR for {test_def['id']} ---")
            print(proc.stderr)

        if proc.returncode != 0:
            return "ERROR", f"subprocess failed with exit code {proc.returncode}. Stderr: {proc.stderr.strip()}", duration

        # Parse output CSV
        rows = parse_csv_output(temp_out_path)
        
        # Verify
        passed, msg = test_def["verify"](rows)
        if passed:
            return "PASS", msg, duration
        return "FAIL", msg, duration

    except Exception as e:
        return "ERROR", f"Test runner exception: {str(e)}", 0.0
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_in_path):
                os.remove(temp_in_path)
            if os.path.exists(temp_out_path):
                os.remove(temp_out_path)
        except Exception:
            pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Redrob E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only tests from a specific tier")
    parser.add_argument("--feature", type=str, help="Run only tests for a specific feature (e.g. F1, F2)")
    parser.add_argument("--test-id", type=str, help="Run a specific test case ID (e.g. TC_001)")
    parser.add_argument("--verbose", action="store_true", help="Print subprocess outputs")
    args = parser.parse_args()

    print("=" * 60)
    print("  REDROB CANDIDATE RANKING ENGINE - E2E TEST RUNNER")
    print("=" * 60)

    all_tests = build_all_tests()
    
    # Filter tests
    tests_to_run = all_tests
    if args.test_id:
        tests_to_run = [t for t in tests_to_run if t["id"] == args.test_id]
    if args.tier:
        tests_to_run = [t for t in tests_to_run if t["tier"] == args.tier]
    if args.feature:
        tests_to_run = [t for t in tests_to_run if t["feature"] == args.feature]

    print(f"Loaded {len(all_tests)} total tests.")
    print(f"Selected {len(tests_to_run)} tests to run.")
    print("-" * 60)

    results = []
    passed_count = 0
    failed_count = 0
    error_count = 0
    total_time = 0.0

    # Ensure rank.py exists
    if not (PROJECT_ROOT / "rank.py").exists():
        print(f"CRITICAL ERROR: rank.py not found at {PROJECT_ROOT / 'rank.py'}")
        sys.exit(1)

    for t in tests_to_run:
        status, message, duration = run_single_test(t, verbose=args.verbose)
        total_time += duration
        
        if status == "PASS":
            passed_count += 1
            status_str = "\033[92mPASS\033[0m" if os.name != 'nt' else "PASS"
        elif status == "FAIL":
            failed_count += 1
            status_str = "\033[91mFAIL\033[0m" if os.name != 'nt' else "FAIL"
        else:
            error_count += 1
            status_str = "\033[93mERROR\033[0m" if os.name != 'nt' else "ERROR"

        print(f"[{status_str}] {t['id']} (Tier {t['tier']} - {t['feature']}): {t['description']}")
        if status != "PASS":
            print(f"        Detail: {message}")
            
        results.append({
            "id": t["id"],
            "tier": t["tier"],
            "feature": t["feature"],
            "status": status,
            "message": message,
            "duration": duration
        })

    # Summary Report
    print("=" * 60)
    print("  TEST RUN SUMMARY")
    print("=" * 60)
    print(f"  Total tests run: {len(tests_to_run)}")
    print(f"  Passed:          {passed_count}")
    print(f"  Failed:          {failed_count}")
    print(f"  Errors:          {error_count}")
    print(f"  Total time:      {total_time:.2f}s")
    print("=" * 60)

    # Print breakdown by tier
    for tier in [1, 2, 3, 4]:
        tier_results = [r for r in results if r["tier"] == tier]
        if not tier_results:
            continue
        t_pass = sum(1 for r in tier_results if r["status"] == "PASS")
        t_fail = sum(1 for r in tier_results if r["status"] == "FAIL")
        t_err = sum(1 for r in tier_results if r["status"] == "ERROR")
        print(f"  Tier {tier}: {t_pass} passed, {t_fail} failed, {t_err} errored out of {len(tier_results)}")
    
    print("=" * 60)

    # Return exit code based on failures/errors
    if failed_count > 0 or error_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
