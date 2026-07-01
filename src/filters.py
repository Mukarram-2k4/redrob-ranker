from datetime import date
import re
from src.models import Candidate
from src.ingest import normalize_text
from src.config import (
    FIXTURE_COMPANIES,
    HARD_DISQUALIFY_RR_THRESHOLD,
    HARD_DISQUALIFY_ICR_THRESHOLD,
    get_skill_tier_name,
    HONEYPOT_RULES,
    HONEYPOT_CONFIDENCE_THRESHOLD,
    HP03_OVERLAP_DAYS,
    HP07_COMPLETENESS_THRESHOLD,
    HP07_INACTIVE_DAYS,
    HP08_MIN_ASSESSMENTS,
    HP08_SCORE_THRESHOLD,
    HP09_RESPONSE_TIME_THRESHOLD,
    CURRENT_YEAR,
    TECH_RELEASE_YEARS,
    SKILL_ADJACENCY,
    HP13_ARCHITECTURE_ASTRONAUT_PENALTY,
)

fixture_pattern = re.compile(
    r"\b(?:" + "|".join(re.escape(f) for f in FIXTURE_COMPANIES) + r")\b",
    re.IGNORECASE
)


def has_tech_skills(cand: Candidate) -> bool:
    """
    Technical skill is one with tier A/B/C/D/NEG, not tier E or UNK.
    """
    for s in cand.skills:
        tier = get_skill_tier_name(s.name)
        if tier in {"A", "B", "C", "D", "NEG"}:
            return True
    return False


def get_calendar_span_years(cand: Candidate) -> float:
    if not cand.career_history:
        return 0.0
    earliest_start = None
    latest_end = None
    for entry in cand.career_history:
        start = entry.start_date
        end = entry.end_date if (entry.end_date is not None and not entry.is_current) else date(CURRENT_YEAR, 6, 1)
        if earliest_start is None or start < earliest_start:
            earliest_start = start
        if latest_end is None or end > latest_end:
            latest_end = end
    if earliest_start is None or latest_end is None:
        return 0.0
    return (latest_end - earliest_start).days / 365.25


def early_eliminate(candidates: list[Candidate], lookups: dict) -> tuple[list[Candidate], list[Candidate]]:
    """
    Eliminate candidate early if:
      - YOE < 2.0
      - OR zero tech skills (technical skill is one with tier A/B/C/D/NEG, not tier E or UNK)
      - OR early honeypot confidence >= HONEYPOT_CONFIDENCE_THRESHOLD.
    Set cand.eliminated_early = True on eliminated.
    Flag cand.hard_disqualify = True if recruiter_response_rate < HARD_DISQUALIFY_RR_THRESHOLD AND interview_completion_rate < HARD_DISQUALIFY_ICR_THRESHOLD.

    Early honeypot rules to check:
      - HP01: salary_min_lpa > salary_max_lpa (confidence = HONEYPOT_RULES["HP01_SALARY_INVERSION"])
      - HP02: YOE > calendar_span_years + 0.1. (confidence = HONEYPOT_RULES["HP02_YOE_VS_CAREER_SPAN"])
      - HP05: YOE > CURRENT_YEAR - earliest_education_end_year. (confidence = HONEYPOT_RULES["HP05_YOUNG_CAREER_HIGH_YOE"])
      - HP06: Any career entry duration_months > calendar_months + 2. (confidence = HONEYPOT_RULES["HP06_IMPOSSIBLE_TENURE"])

    Return (survivors, eliminated).
    """
    survivors = []
    eliminated = []

    for cand in candidates:
        # HP01
        hp01_conf = 0.0
        if cand.signals.salary_min_lpa > cand.signals.salary_max_lpa:
            hp01_conf = HONEYPOT_RULES["HP01_SALARY_INVERSION"]

        # HP02
        hp02_conf = 0.0
        if cand.career_history:
            span_years = get_calendar_span_years(cand)
            if cand.years_of_experience > span_years + 0.1:
                hp02_conf = HONEYPOT_RULES["HP02_YOE_VS_CAREER_SPAN"]

        # HP05
        hp05_conf = 0.0
        if cand.education:
            valid_edu_ends = [edu.end_year for edu in cand.education if edu.end_year > 0]
            if valid_edu_ends:
                earliest_edu_end = min(valid_edu_ends)
                pg_pattern = re.compile(r"\b(?:master's|masters|master|phd|ph\.d|m\.tech|mtech|m\.s\.|ms)\b", re.IGNORECASE)
                ug_pattern = re.compile(r"\b(?:bachelor's|bachelors|bachelor|b\.tech|btech|b\.e\.|be|b\.s\.|bs)\b", re.IGNORECASE)
                
                has_pg = any(pg_pattern.search(edu.degree) for edu in cand.education)
                has_ug = any(ug_pattern.search(edu.degree) for edu in cand.education)
                
                edu_buffer = 4 if (has_pg and not has_ug) else 0
                if cand.years_of_experience > (2026 - earliest_edu_end + edu_buffer) + 1.0:
                    hp05_conf = HONEYPOT_RULES["HP05_YOUNG_CAREER_HIGH_YOE"]

        # HP06
        hp06_conf = 0.0
        for entry in cand.career_history:
            start = entry.start_date
            end = entry.end_date if (entry.end_date is not None and not entry.is_current) else date(CURRENT_YEAR, 6, 1)
            cal_months = (end - start).days / (365.25 / 12)
            if entry.duration_months > cal_months + 2:
                hp06_conf = HONEYPOT_RULES["HP06_IMPOSSIBLE_TENURE"]
                break

        # Set early honeypot confidence
        cand.honeypot_confidence = hp01_conf + hp02_conf + hp05_conf + hp06_conf

        # Flag hard disqualify
        if cand.signals.recruiter_response_rate < HARD_DISQUALIFY_RR_THRESHOLD and cand.signals.interview_completion_rate < HARD_DISQUALIFY_ICR_THRESHOLD:
            cand.hard_disqualify = True

        # Check early elimination condition
        if cand.years_of_experience < 2.0 or not has_tech_skills(cand) or cand.honeypot_confidence >= HONEYPOT_CONFIDENCE_THRESHOLD:
            cand.eliminated_early = True
            eliminated.append(cand)
        else:
            survivors.append(cand)

    return survivors, eliminated


def get_overlap_days(e1, e2) -> int:
    s1 = e1.start_date
    d1 = e1.end_date if (e1.end_date is not None and not e1.is_current) else date(CURRENT_YEAR, 6, 1)
    s2 = e2.start_date
    d2 = e2.end_date if (e2.end_date is not None and not e2.is_current) else date(CURRENT_YEAR, 6, 1)

    start_overlap = max(s1, s2)
    end_overlap = min(d1, d2)
    if start_overlap < end_overlap:
        return (end_overlap - start_overlap).days
    return 0


def _get_max_career_year(cand: Candidate) -> int:
    """Get the maximum career end year across all entries."""
    if not cand.career_history:
        return 0
    max_year = 0
    for entry in cand.career_history:
        if entry.is_current:
            max_year = CURRENT_YEAR
        elif entry.end_date is not None:
            max_year = max(max_year, entry.end_date.year)
    return max_year


def _check_time_travel(cand: Candidate) -> float:
    """
    HP11: Technology Time-Travel Fraud Detection.
    
    Bulletproof version: checks BOTH:
    1. Global profile (skills + headline + summary) against max_career_year
    2. Per-entry career descriptions against entry end_date
    """
    confidence = 0.0
    max_career_year = _get_max_career_year(cand)
    
    if max_career_year == 0:
        return 0.0
    
    # Check 1: Global profile — skills, headline, summary
    global_text = " ".join(s.name.lower() for s in cand.skills)
    if cand.headline:
        global_text += " " + cand.headline.lower()
    if cand.summary:
        global_text += " " + cand.summary.lower()
    global_text = normalize_text(global_text)
    
    for tech, release_year in TECH_RELEASE_YEARS.items():
        if tech in global_text and max_career_year < release_year:
            confidence = HONEYPOT_RULES["HP11_TECH_TIME_TRAVEL"]
            return confidence  # One violation is enough
    
    # Check 2: Per-entry career descriptions
    for entry in cand.career_history:
        end_year = entry.end_date.year if (entry.end_date and not entry.is_current) else CURRENT_YEAR
        desc_lower = normalize_text(entry.description + " " + entry.title)
        for tech, release_year in TECH_RELEASE_YEARS.items():
            if tech in desc_lower and end_year < release_year:
                confidence = HONEYPOT_RULES["HP11_TECH_TIME_TRAVEL"]
                return confidence
    
    return confidence


def _check_empty_expertise(cand: Candidate) -> float:
    """
    HP12: Expert proficiency claims with 0 months duration and no endorsements.
    Common synthetic honeypot pattern.
    """
    count = sum(
        1 for s in cand.skills
        if s.proficiency == "expert"
        and s.duration_months == 0
        and s.endorsements <= 1
    )
    if count >= 10:
        return HONEYPOT_RULES["HP12_EMPTY_EXPERTISE"]
    elif count >= 5:
        return 0.40
    return 0.0


def _check_architecture_astronaut(cand: Candidate) -> float:
    """
    HP13: Manager/Director/VP titles without hands-on coding evidence.
    JD says "founding team member who codes" — not a honeypot but a penalty.
    Returns the penalty value (not honeypot confidence).
    """
    title_lower = cand.current_title.lower() if cand.current_title else ""
    
    manager_keywords = ["director", "vp ", "vice president", "head of", "general manager"]
    is_manager = any(kw in title_lower for kw in manager_keywords)
    is_pure_architect = "architect" in title_lower and "engineer" not in title_lower
    
    if not (is_manager or is_pure_architect):
        return 0.0
    
    # Check recent career (≤3 years ago) for hands-on markers
    hands_on_markers = [
        "wrote", "coded", "implemented", "developed", "built",
        "engineered", "deployed", "shipped", "python", "git",
        "hands-on", "hands on", "contributed code",
    ]
    recent_desc = " ".join(
        entry.description.lower() for entry in cand.career_history
        if entry.years_ago <= 3
    )
    
    if any(marker in recent_desc for marker in hands_on_markers):
        return 0.0  # They have hands-on evidence
    
    return HP13_ARCHITECTURE_ASTRONAUT_PENALTY


def _check_skill_adjacency(cand: Candidate) -> float:
    """
    HP14: Skill Adjacency Corroboration.
    High-value skills without adjacent supporting skills → reduced trust.
    """
    skill_names = {s.name.lower().strip() for s in cand.skills}
    
    corroborated = 0
    checkable = 0
    for skill_key, adjacencies in SKILL_ADJACENCY.items():
        if skill_key in skill_names:
            checkable += 1
            if any(adj in skill_names for adj in adjacencies):
                corroborated += 1
    
    if checkable == 0:
        return 0.0  # No checkable skills = neutral
    
    ratio = corroborated / checkable
    if ratio < 0.5:
        return HONEYPOT_RULES["HP14_SKILL_ADJACENCY"] * (1.0 - ratio)
    return 0.0


def honeypot_full_pass(survivors: list[Candidate]) -> None:
    """
    Check rules HP03, HP04, HP07, HP08, HP09, HP10, HP11, HP12, HP13, HP14 on survivors.
      - HP03: Overlap of any two career entries > HP03_OVERLAP_DAYS days.
      - HP04: Earliest job start year < earliest education start year.
      - HP07: profile_completeness_score == 100 AND inactivity > 3 years.
      - HP08: >= 3 assessments AND all scores >= 90.
      - HP09: average response time <= 0.1 hours.
      - HP10: Any company name in FIXTURE_COMPANIES.
      - HP11: Technology time-travel fraud.
      - HP12: Empty expertise (expert + 0 months + ≤1 endorsements).
      - HP13: Architecture astronaut (penalty, not confidence).
      - HP14: Skill adjacency corroboration.

    Sum confidences onto cand.honeypot_confidence.
    If accumulated confidence >= HONEYPOT_CONFIDENCE_THRESHOLD, set cand.honeypot_flag = True.
    """
    for cand in survivors:
        # HP03
        hp03_conf = 0.0
        n_entries = len(cand.career_history)
        for i in range(n_entries):
            for j in range(i + 1, n_entries):
                overlap = get_overlap_days(cand.career_history[i], cand.career_history[j])
                if overlap > HP03_OVERLAP_DAYS:
                    hp03_conf = HONEYPOT_RULES["HP03_OVERLAPPING_TENURES"]
                    break
            if hp03_conf > 0.0:
                break

        # HP04
        hp04_conf = 0.0
        if cand.career_history and cand.education:
            earliest_job_year = min(entry.start_date.year for entry in cand.career_history)
            earliest_edu_year = min(edu.start_year for edu in cand.education)
            if earliest_job_year < earliest_edu_year:
                hp04_conf = HONEYPOT_RULES["HP04_EDU_VS_CAREER_START"]

        # HP07
        hp07_conf = 0.0
        inactivity_days = (date(CURRENT_YEAR, 6, 1) - cand.signals.last_active_date).days
        if cand.signals.profile_completeness_score == HP07_COMPLETENESS_THRESHOLD and inactivity_days > HP07_INACTIVE_DAYS:
            hp07_conf = HONEYPOT_RULES["HP07_PERFECT_ABANDONED"]

        # HP08
        hp08_conf = 0.0
        n_assessments = len(cand.signals.skill_assessment_scores)
        if n_assessments >= HP08_MIN_ASSESSMENTS and all(val >= HP08_SCORE_THRESHOLD for val in cand.signals.skill_assessment_scores.values()):
            hp08_conf = HONEYPOT_RULES["HP08_ALL_ASSESSMENTS_PERF"]

        # HP09
        hp09_conf = 0.0
        if cand.signals.avg_response_time_hours <= HP09_RESPONSE_TIME_THRESHOLD:
            hp09_conf = HONEYPOT_RULES["HP09_INSTANT_RESPONSE"]

        # HP10
        hp10_conf = 0.0
        has_fixture = False
        if cand.current_company and fixture_pattern.search(cand.current_company):
            has_fixture = True
        else:
            for entry in cand.career_history:
                if entry.company and fixture_pattern.search(entry.company):
                    has_fixture = True
                    break
        if has_fixture:
            hp10_conf = HONEYPOT_RULES["HP10_FIXTURE_COMPANY"]

        # HP11: Time-travel fraud
        hp11_conf = _check_time_travel(cand)

        # HP12: Empty expertise
        hp12_conf = _check_empty_expertise(cand)

        # HP13: Architecture astronaut (penalty stored in features, not confidence)
        hp13_penalty = _check_architecture_astronaut(cand)
        if hp13_penalty > 0.0:
            cand.features["architecture_astronaut_penalty"] = hp13_penalty

        # HP14: Skill adjacency corroboration
        hp14_conf = _check_skill_adjacency(cand)

        # Sum confidences
        cand.honeypot_confidence += (
            hp03_conf + hp04_conf + hp07_conf + hp08_conf + hp09_conf + hp10_conf
            + hp11_conf + hp12_conf + hp14_conf
        )

        if cand.honeypot_confidence >= HONEYPOT_CONFIDENCE_THRESHOLD:
            cand.honeypot_flag = True
