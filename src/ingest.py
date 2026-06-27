import json
import re
from datetime import date
try:
    import pyahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False

from src.config import (
    TIER_A_SKILLS, TIER_B_SKILLS, TIER_C_SKILLS, TIER_D_SKILLS,
    PRODUCTION_PHRASES, RESEARCH_PHRASES
)
from src.models import parse_candidate, Candidate


def build_lookups() -> dict:
    """
    Compiles Aho-Corasick automaton if pyahocorasick is installed.
    Otherwise, compiles a case-insensitive regular expression using alternation
    with word boundaries: \\b(?:phrase1|phrase2|...)\\b.
    Pre-sort phrases by length descending to match longer patterns first.

    Extract all technical skill names from TIER_A_SKILLS, TIER_B_SKILLS,
    TIER_C_SKILLS, and TIER_D_SKILLS in config.py and compile them into a set
    of lowercased, stripped strings stored under key 'tech_skills'.
    """
    if HAS_AHOCORASICK:
        production_scanner = pyahocorasick.Automaton()
        for p in PRODUCTION_PHRASES:
            p_low = p.lower()
            production_scanner.add_word(p_low, p_low)
        production_scanner.make_automaton()

        research_scanner = pyahocorasick.Automaton()
        for p in RESEARCH_PHRASES:
            p_low = p.lower()
            research_scanner.add_word(p_low, p_low)
        research_scanner.make_automaton()
    else:
        prod_sorted = sorted(PRODUCTION_PHRASES, key=len, reverse=True)
        res_sorted = sorted(RESEARCH_PHRASES, key=len, reverse=True)

        prod_pattern = r"\b(?:" + "|".join(re.escape(p) for p in prod_sorted) + r")\b"
        res_pattern = r"\b(?:" + "|".join(re.escape(p) for p in res_sorted) + r")\b"

        production_scanner = re.compile(prod_pattern, re.IGNORECASE)
        research_scanner = re.compile(res_pattern, re.IGNORECASE)

    tech_skills = set()
    for skill_dict in (TIER_A_SKILLS, TIER_B_SKILLS, TIER_C_SKILLS, TIER_D_SKILLS):
        for k in skill_dict.keys():
            tech_skills.add(k.lower().strip())

    return {
        "production_scanner": production_scanner,
        "research_scanner": research_scanner,
        "tech_skills": tech_skills
    }


def safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_bool(val, default=False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def load_candidates(path: str) -> list[Candidate]:
    """
    Streams candidates line-by-line. Skips empty and malformed JSON lines cleanly.
    Verify top-level keys candidate_id, profile, and redrob_signals are present and are dicts.
    Set defaults to empty lists if career_history, education, or skills are missing/not lists.
    Coerce nested types in redrob_signals to correct types.
    Invoke models.parse_candidate and collect.
    """
    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                raw = json.loads(line_str)
            except (json.JSONDecodeError, RecursionError):
                continue

            if "candidate_id" not in raw or "profile" not in raw or "redrob_signals" not in raw:
                continue
            if not isinstance(raw["candidate_id"], str) or not isinstance(raw["profile"], dict) or not isinstance(raw["redrob_signals"], dict):
                continue

            for col in ("career_history", "education", "skills"):
                if col not in raw or not isinstance(raw[col], list):
                    raw[col] = []

            signals = raw["redrob_signals"]

            salary = signals.get("expected_salary_range_inr_lpa")
            if not isinstance(salary, dict):
                salary = {}
            signals["expected_salary_range_inr_lpa"] = {
                "min": safe_float(salary.get("min")),
                "max": safe_float(salary.get("max"))
            }

            scores = signals.get("skill_assessment_scores")
            if not isinstance(scores, dict):
                scores = {}
            new_scores = {}
            for k, v in scores.items():
                new_scores[str(k)] = safe_int(v)
            signals["skill_assessment_scores"] = new_scores

            for field in ["profile_completeness_score", "recruiter_response_rate", "avg_response_time_hours",
                          "github_activity_score", "interview_completion_rate", "offer_acceptance_rate"]:
                default_val = 24.0 if field == "avg_response_time_hours" else (-1.0 if field in ["github_activity_score", "offer_acceptance_rate"] else 0.0)
                signals[field] = safe_float(signals.get(field), default=default_val)

            for field in ["profile_views_received_30d", "applications_submitted_30d", "connection_count",
                          "endorsements_received", "notice_period_days", "search_appearance_30d", "saved_by_recruiters_30d"]:
                signals[field] = safe_int(signals.get(field))

            for field in ["open_to_work_flag", "willing_to_relocate", "verified_email", "verified_phone", "linkedin_connected"]:
                signals[field] = safe_bool(signals.get(field))

            for field in ["signup_date", "last_active_date"]:
                if field in signals and signals[field] is not None:
                    signals[field] = str(signals[field])

            # Sanitize career_history
            sanitized_career = []
            for entry in raw["career_history"]:
                if isinstance(entry, dict):
                    if "start_date" in entry:
                        sd = entry["start_date"]
                        if not isinstance(sd, (str, date)):
                            entry["start_date"] = str(sd)
                    if "end_date" in entry:
                        ed = entry["end_date"]
                        if ed is not None and not isinstance(ed, str):
                            entry["end_date"] = str(ed)
                    sanitized_career.append(entry)
            raw["career_history"] = sanitized_career

            # Sanitize education
            raw["education"] = [edu for edu in raw["education"] if isinstance(edu, dict)]

            # Sanitize skills
            raw["skills"] = [s for s in raw["skills"] if isinstance(s, dict)]

            cand = parse_candidate(raw)
            if cand is not None:
                candidates.append(cand)

    return candidates
