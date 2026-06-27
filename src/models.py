"""
models.py — Lightweight slotted dataclasses for the ranking pipeline.

These are the internal data structures that traverse the pipeline after
ingestion. No Pydantic overhead — direct dict → dataclass conversion.
All fields use __slots__ for memory efficiency at 100K instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(slots=True)
class CareerEntry:
    """A single career history entry."""
    company: str
    title: str
    start_date: date
    end_date: Optional[date]       # None = currently employed
    duration_months: int
    is_current: bool
    industry: str
    company_size: str              # String enum: "1-10", "51-200", etc.
    description: str

    @property
    def years_ago(self) -> float:
        """How many years ago this role started, relative to 2026."""
        return max(0.0, (date(2026, 6, 1) - self.start_date).days / 365.25)


@dataclass(slots=True)
class EducationEntry:
    """A single education record."""
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int
    grade: Optional[str]           # "8.24 CGPA", "77%", None
    tier: str                      # "tier_1", "tier_2", "tier_3", "tier_4", "unknown"


@dataclass(slots=True)
class SkillEntry:
    """A single declared skill."""
    name: str
    proficiency: str               # "beginner", "intermediate", "advanced", "expert"
    endorsements: int
    duration_months: int


@dataclass(slots=True)
class Signals:
    """All 23 behavioral signals from the redrob_signals object."""
    profile_completeness_score: float       # 0-100
    signup_date: date
    last_active_date: date
    open_to_work_flag: bool
    profile_views_received_30d: int
    applications_submitted_30d: int
    recruiter_response_rate: float          # 0.0-1.0
    avg_response_time_hours: float
    skill_assessment_scores: dict           # {skill_name: 0-100 score}
    connection_count: int
    endorsements_received: int
    notice_period_days: int
    salary_min_lpa: float                   # expected_salary_range_inr_lpa.min
    salary_max_lpa: float                   # expected_salary_range_inr_lpa.max
    preferred_work_mode: str                # "onsite", "hybrid", "remote", "flexible"
    willing_to_relocate: bool
    github_activity_score: float            # -1 to 100
    search_appearance_30d: int
    saved_by_recruiters_30d: int
    interview_completion_rate: float        # 0.0-1.0
    offer_acceptance_rate: float            # -1 to 1.0
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool


@dataclass(slots=True)
class Candidate:
    """
    Core candidate object that traverses the pipeline.

    Created from raw JSON dict at ingestion. All subsequent stages
    mutate the scoring/flag fields but never re-parse the raw data.
    """

    # ── Identity ──
    candidate_id: str                       # CAND_XXXXXXX

    # ── Profile (from nested 'profile' object) ──
    anonymized_name: str
    headline: str
    summary: str
    location: str                           # City string
    country: str
    years_of_experience: float
    current_title: str
    current_company: str
    current_company_size: str
    current_industry: str

    # ── Collections ──
    career_history: list[CareerEntry]
    education: list[EducationEntry]
    skills: list[SkillEntry]
    signals: Signals

    # ── Pipeline state (mutated by stages) ──
    honeypot_confidence: float = 0.0
    honeypot_flag: bool = False
    hard_disqualify: bool = False
    eliminated_early: bool = False
    final_score: float = -2.0               # -2 = unscored, -1 = disqualified
    rank: Optional[int] = None

    # ── Feature cache (populated during feature extraction) ──
    features: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# PARSING FUNCTIONS — Convert raw JSON dicts to dataclass instances
# ═══════════════════════════════════════════════════════════════════════════

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse an ISO date string to a date object. Returns None on failure."""
    if not date_str:
        return None
    try:
        parts = date_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def _parse_career_entry(raw: dict) -> Optional[CareerEntry]:
    """Parse a single career history entry from raw dict."""
    try:
        start = _parse_date(raw.get("start_date"))
        if start is None:
            return None
        return CareerEntry(
            company=str(raw.get("company", "")).strip(),
            title=str(raw.get("title", "")).strip(),
            start_date=start,
            end_date=_parse_date(raw.get("end_date")),
            duration_months=int(raw.get("duration_months", 0)),
            is_current=bool(raw.get("is_current", False)),
            industry=str(raw.get("industry", "")).strip(),
            company_size=str(raw.get("company_size", "")).strip(),
            description=str(raw.get("description", "")).strip(),
        )
    except (TypeError, ValueError):
        return None


def _parse_education_entry(raw: dict) -> Optional[EducationEntry]:
    """Parse a single education entry from raw dict."""
    try:
        return EducationEntry(
            institution=str(raw.get("institution", "")).strip(),
            degree=str(raw.get("degree", "")).strip(),
            field_of_study=str(raw.get("field_of_study", "")).strip(),
            start_year=int(raw.get("start_year", 0)),
            end_year=int(raw.get("end_year", 0)),
            grade=raw.get("grade"),
            tier=str(raw.get("tier", "unknown")).strip(),
        )
    except (TypeError, ValueError):
        return None


def _parse_skill_entry(raw: dict) -> Optional[SkillEntry]:
    """Parse a single skill entry from raw dict."""
    try:
        return SkillEntry(
            name=str(raw.get("name", "")).strip(),
            proficiency=str(raw.get("proficiency", "beginner")).strip().lower(),
            endorsements=int(raw.get("endorsements", 0)),
            duration_months=int(raw.get("duration_months", 0)),
        )
    except (TypeError, ValueError):
        return None


def _parse_signals(raw: dict) -> Optional[Signals]:
    """Parse the redrob_signals object."""
    try:
        salary = raw.get("expected_salary_range_inr_lpa", {})
        return Signals(
            profile_completeness_score=float(raw.get("profile_completeness_score", 0)),
            signup_date=_parse_date(raw.get("signup_date")) or date(2025, 1, 1),
            last_active_date=_parse_date(raw.get("last_active_date")) or date(2025, 1, 1),
            open_to_work_flag=bool(raw.get("open_to_work_flag", False)),
            profile_views_received_30d=int(raw.get("profile_views_received_30d", 0)),
            applications_submitted_30d=int(raw.get("applications_submitted_30d", 0)),
            recruiter_response_rate=float(raw.get("recruiter_response_rate", 0)),
            avg_response_time_hours=float(raw.get("avg_response_time_hours", 0)),
            skill_assessment_scores=raw.get("skill_assessment_scores", {}),
            connection_count=int(raw.get("connection_count", 0)),
            endorsements_received=int(raw.get("endorsements_received", 0)),
            notice_period_days=int(raw.get("notice_period_days", 0)),
            salary_min_lpa=float(salary.get("min", 0)),
            salary_max_lpa=float(salary.get("max", 0)),
            preferred_work_mode=str(raw.get("preferred_work_mode", "hybrid")).strip().lower(),
            willing_to_relocate=bool(raw.get("willing_to_relocate", False)),
            github_activity_score=float(raw.get("github_activity_score", -1)),
            search_appearance_30d=int(raw.get("search_appearance_30d", 0)),
            saved_by_recruiters_30d=int(raw.get("saved_by_recruiters_30d", 0)),
            interview_completion_rate=float(raw.get("interview_completion_rate", 0)),
            offer_acceptance_rate=float(raw.get("offer_acceptance_rate", -1)),
            verified_email=bool(raw.get("verified_email", False)),
            verified_phone=bool(raw.get("verified_phone", False)),
            linkedin_connected=bool(raw.get("linkedin_connected", False)),
        )
    except (TypeError, ValueError):
        return None


def parse_candidate(raw: dict) -> Optional[Candidate]:
    """
    Parse a raw JSON dict into a Candidate dataclass.

    Returns None if the record is malformed (missing required fields).
    This is the single entry point for converting raw data → pipeline objects.
    """
    try:
        cid = raw.get("candidate_id", "")
        if not cid or not isinstance(cid, str):
            return None

        profile = raw.get("profile", {})
        if not profile:
            return None

        # Parse signals
        signals_raw = raw.get("redrob_signals", {})
        signals = _parse_signals(signals_raw)
        if signals is None:
            return None

        # Parse career history
        career = []
        for entry_raw in raw.get("career_history", []):
            entry = _parse_career_entry(entry_raw)
            if entry is not None:
                career.append(entry)

        # Sort career by start_date ascending (needed for title-chaser, overlap checks)
        career.sort(key=lambda e: e.start_date)

        # Parse education
        education = []
        for edu_raw in raw.get("education", []):
            edu = _parse_education_entry(edu_raw)
            if edu is not None:
                education.append(edu)

        # Parse skills
        skills = []
        for skill_raw in raw.get("skills", []):
            skill = _parse_skill_entry(skill_raw)
            if skill is not None:
                skills.append(skill)

        return Candidate(
            candidate_id=cid.strip(),
            anonymized_name=str(profile.get("anonymized_name", "")).strip(),
            headline=str(profile.get("headline", "")).strip(),
            summary=str(profile.get("summary", "")).strip(),
            location=str(profile.get("location", "")).strip(),
            country=str(profile.get("country", "")).strip(),
            years_of_experience=float(profile.get("years_of_experience", 0)),
            current_title=str(profile.get("current_title", "")).strip(),
            current_company=str(profile.get("current_company", "")).strip(),
            current_company_size=str(profile.get("current_company_size", "")).strip(),
            current_industry=str(profile.get("current_industry", "")).strip(),
            career_history=career,
            education=education,
            skills=skills,
            signals=signals,
        )

    except Exception:
        return None
