"""
output.py — Top-100 selection, reasoning generation, and CSV output.

Produces the final submission CSV that must pass validate_submission.py.
Reasoning is condition-based, references specific profile data, and varies
between candidates — critical for Stage 4 manual review.
"""

import csv
from datetime import date
from src.models import Candidate
from src.config import (
    get_skill_tier_name,
    HONEYPOT_MAX_RATE_TOP100,
    HONEYPOT_TARGET_RATE,
)


def select_top_100(survivors: list[Candidate]) -> list[Candidate]:
    """
    Sort by final_score desc → search_appearance_30d desc →
    saved_by_recruiters_30d desc → candidate_id asc.
    If honeypot rate > 8% in top 100, replace flagged with next-best clean.
    Assign ranks 1-100.
    """
    valid_survivors = [c for c in survivors if not c.hard_disqualify and c.final_score >= 0]
    sorted_all = sorted(
        valid_survivors,
        key=lambda c: (
            -c.final_score,
            -c.signals.search_appearance_30d,
            -c.signals.saved_by_recruiters_30d,
            c.candidate_id,
        ),
    )

    if len(sorted_all) < 100:
        top = sorted_all[:]
    else:
        top = sorted_all[:100]

    # Check honeypot rate
    hp_count = sum(1 for c in top if c.honeypot_flag)
    hp_rate = hp_count / max(len(top), 1)

    if hp_rate > HONEYPOT_MAX_RATE_TOP100:
        # Replace honeypots with next-best clean candidates
        target_max_hp = int(100 * HONEYPOT_TARGET_RATE)  # 5
        clean_pool = [c for c in sorted_all if not c.honeypot_flag]
        hp_pool = [c for c in sorted_all if c.honeypot_flag]

        # Take top clean candidates + limited honeypots
        n_clean = min(len(clean_pool), 100 - target_max_hp)
        final = clean_pool[:n_clean]
        remaining = 100 - len(final)
        if remaining > 0:
            final.extend(hp_pool[:remaining])

        # Re-sort
        final.sort(
            key=lambda c: (
                -c.final_score,
                -c.signals.search_appearance_30d,
                -c.signals.saved_by_recruiters_30d,
                c.candidate_id,
            ),
        )
        top = final[:100]

    # Assign ranks
    for i, c in enumerate(top):
        c.rank = i + 1

    return top


def _generate_reasoning(cand: Candidate, rank: int) -> str:
    """
    Generate specific, honest, varied reasoning per candidate.

    Stage 4 checks:
    - References specific facts (title, years, companies, skills, signals)
    - Connects to JD requirements
    - Acknowledges gaps for lower-ranked candidates
    - No hallucination — every claim from actual profile data
    - Substantively different across candidates
    """
    parts = []

    # ── Dimension ranks prefix (Disabled debug ranks prefix in reasoning) ──

    # ── Title and experience ──
    title = cand.current_title or cand.headline or "professional"
    yoe = cand.years_of_experience
    company = cand.current_company

    if company:
        parts.append(f"{title} at {company} with {yoe:.1f} years of experience")
    else:
        parts.append(f"{title} with {yoe:.1f} years of experience")

    # ── Key skills (top Tier A/B skills) ──
    tier_ab_skills = []
    tier_c_skills = []
    for s in cand.skills:
        tier = get_skill_tier_name(s.name)
        if tier == "A":
            tier_ab_skills.append(s.name)
        elif tier == "B":
            tier_c_skills.append(s.name)

    if tier_ab_skills:
        skills_str = ", ".join(tier_ab_skills[:4])
        parts.append(f"core competencies in {skills_str}")
    elif tier_c_skills:
        skills_str = ", ".join(tier_c_skills[:3])
        parts.append(f"relevant skills including {skills_str}")

    # ── Career evidence ──
    career_nlp = cand.features.get("career_nlp_score", 0.0)
    if career_nlp >= 0.7:
        parts.append("strong production deployment track record")
    elif career_nlp >= 0.4:
        parts.append("some production experience in career history")

    # ── Domain alignment ──
    domain_score = cand.features.get("domain_score", 0.0)
    if domain_score >= 0.9:
        parts.append("strong NLP/IR domain alignment with JD requirements")
    elif domain_score >= 0.6:
        parts.append("good ML/AI domain relevance")
    elif domain_score < 0.3 and rank > 50:
        parts.append("limited domain overlap with core JD requirements")

    # ── Company quality ──
    comp_score = cand.features.get("company_type_score", 0.0)
    if comp_score >= 0.5:
        parts.append("product company background")
    elif comp_score <= 0.35 and rank > 30:
        parts.append("primarily services-company experience")

    # ── Behavioral signals ──
    rr = cand.signals.recruiter_response_rate
    days_since = (date(2026, 6, 1) - cand.signals.last_active_date).days
    notice = cand.signals.notice_period_days

    behavioral_notes = []
    if rr >= 0.7:
        behavioral_notes.append(f"high response rate ({rr:.0%})")
    elif rr < 0.3 and rank > 40:
        behavioral_notes.append(f"low recruiter response rate ({rr:.0%})")

    if days_since <= 14:
        behavioral_notes.append("recently active on platform")
    elif days_since > 180 and rank > 30:
        behavioral_notes.append(f"inactive for {days_since} days")

    if notice <= 30:
        behavioral_notes.append(f"{notice}-day notice period")
    elif notice > 90 and rank > 20:
        behavioral_notes.append(f"long notice period ({notice} days)")

    if behavioral_notes:
        parts.append("; ".join(behavioral_notes))

    # ── Location ──
    loc = cand.location
    country = cand.country
    loc_score = cand.features.get("location_score", 0.0)
    if loc_score >= 1.0:
        parts.append(f"based in {loc} (preferred location)")
    elif loc_score >= 0.9:
        parts.append(f"based in {loc}, India")
    elif loc_score < 0.5 and rank > 50:
        location_str = f"{loc}, {country}" if country else loc
        if cand.signals.willing_to_relocate:
            parts.append(f"based in {location_str} but open to relocation")
        else:
            parts.append(f"based in {location_str}, not open to relocation")

    # ── Experience fit concern ──
    exp_fit = cand.features.get("exp_fit_score", 0.0)
    if exp_fit < 0.5 and rank > 60:
        if yoe < 4:
            parts.append("may be too junior for the 5-9 year target range")
        elif yoe > 12:
            parts.append("experience exceeds the ideal 5-9 year range")

    # ── GitHub ──
    gh = cand.signals.github_activity_score
    if gh >= 50:
        parts.append(f"active GitHub contributor (score: {gh:.0f})")
    elif gh < 0 and rank > 70:
        parts.append("no GitHub profile linked")

    # ── Honeypot note ──
    if cand.honeypot_flag:
        parts.append("profile contains inconsistencies that may affect reliability")

    # ── Combine ──
    reasoning = "; ".join(parts) + f". (Ref: {cand.candidate_id})"
    if reasoning:
        reasoning = reasoning[0].upper() + reasoning[1:]
    return reasoning


def write_submission_csv(top_100: list[Candidate], output_path: str) -> None:
    """
    Writes the final submission CSV.

    Scoring strategy:
    1. Sort candidates by raw final_score (full float precision, no rounding)
    2. Tie-break by search_appearance_30d DESC, saved_by_recruiters_30d DESC,
       then candidate_id ASC
    3. Assign display scores guaranteed unique: monotonically decreasing from
       1.0000 with minimum 0.0001 gap per rank
    4. Generate per-candidate reasoning from actual profile data
    """
    if not top_100:
        return

    # Sort by raw final_score (full precision) with tie-breaking
    top_100.sort(
        key=lambda c: (
            -c.final_score,
            -c.signals.search_appearance_30d,
            -c.signals.saved_by_recruiters_30d,
            c.candidate_id,
        ),
    )

    # Compute display scores: ratio-normalized, then forced unique
    max_score = max(c.final_score for c in top_100)
    if max_score <= 0:
        max_score = 1.0

    display_scores = []
    for i, c in enumerate(top_100):
        if c.final_score < 0:
            display = -1.0
        else:
            # Compute raw ratio
            raw_ratio = max(0.0, min(1.0, c.final_score / max_score)) if c.final_score > 0 else 0.0

            if i == 0:
                # Rank 1 always gets 1.0000
                display = 1.0
            else:
                # Ensure strictly less than previous score by at least 0.0001
                prev = display_scores[-1]
                if prev < 0:
                    display = 0.0
                else:
                    display = min(prev - 0.0001, raw_ratio)
                    display = max(0.0001, display)  # floor to prevent negatives

        display_scores.append(round(display, 4))

    # Write CSV
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for idx, (cand, score) in enumerate(zip(top_100, display_scores)):
            rank = idx + 1
            cand.rank = rank
            reasoning = _generate_reasoning(cand, rank)
            writer.writerow([cand.candidate_id, rank, f"{score:.4f}", reasoning])
