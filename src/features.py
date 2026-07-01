from datetime import date
try:
    import pyahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False

from src.models import Candidate
from src.ingest import normalize_text
from src.config import (
    BEHAVIORAL_WEIGHTS,
    AVAILABILITY_WEIGHTS,
    ENGAGEMENT_WEIGHTS,
    CREDIBILITY_WEIGHTS,
    WORK_MODE_SCORES,
    LOCATION_PREFERRED,
    LOCATION_ACCEPTABLE,
    LOCATION_OTHER_INDIA_SCORE,
    LOCATION_INTERNATIONAL_RELOCATE_SCORE,
    LOCATION_INTERNATIONAL_NO_RELOCATE_SCORE,
    COMPANY_TYPE_WEIGHTS,
    SERVICES_BLACKLIST,
    PRODUCT_COMPANIES,
    PRODUCT_INDUSTRIES,
    SERVICES_INDUSTRIES,
    parse_company_size,
    compute_exp_fit,
    compute_recency_score,
    compute_notice_score,
    compute_response_time_score,
    compute_github_score,
    temporal_decay,
    EDUCATION_TIER_BONUS,
    DOMAIN_KEYWORDS,
    DOMAIN_SCORES,
    get_skill_tier_weight,
    get_skill_tier_name,
    PROFICIENCY_MULTIPLIERS,
    MAX_NEGATIVE_SKILLS,
    SKILL_STUFFING_THRESHOLD,
    SKILL_STUFFING_PENALTY_RATE,
    SKILL_STUFFING_PENALTY_FLOOR,
    ALL_SERVICES_HARD_CAP,
    SOURCE_WEIGHTS,
)


def get_behavioral_multiplier(score: float) -> float:
    if score >= 0.70:
        return 1.15
    elif score >= 0.50:
        return 1.00
    elif score >= 0.35:
        return 0.85
    elif score >= 0.20:
        return 0.60
    else:
        return 0.35


def compute_behavioral_features(survivors: list[Candidate]) -> None:
    """
    Computes availability_score, engagement_score, credibility_score,
    behavioral_score, and behavioral_multiplier using weights in config.py.
    """
    for cand in survivors:
        # 1. Availability
        recency_val = compute_recency_score((date(2026, 6, 1) - cand.signals.last_active_date).days)
        notice_val = compute_notice_score(cand.signals.notice_period_days)
        otw_val = 1.0 if cand.signals.open_to_work_flag else 0.0
        reloc_val = 1.0 if cand.signals.willing_to_relocate else 0.0
        work_mode_val = WORK_MODE_SCORES.get(cand.signals.preferred_work_mode, 1.0)

        availability = (
            AVAILABILITY_WEIGHTS["recency"] * recency_val +
            AVAILABILITY_WEIGHTS["notice"] * notice_val +
            AVAILABILITY_WEIGHTS["open_to_work"] * otw_val +
            AVAILABILITY_WEIGHTS["relocate"] * reloc_val +
            AVAILABILITY_WEIGHTS["work_mode"] * work_mode_val
        )

        # 2. Engagement
        rr_val = cand.signals.recruiter_response_rate
        icr_val = cand.signals.interview_completion_rate
        resp_time_val = compute_response_time_score(cand.signals.avg_response_time_hours)
        offer_acc_val = cand.signals.offer_acceptance_rate if cand.signals.offer_acceptance_rate >= 0 else 0.0
        apps_val = min(1.0, cand.signals.applications_submitted_30d / 10.0)

        engagement = (
            ENGAGEMENT_WEIGHTS["response_rate"] * rr_val +
            ENGAGEMENT_WEIGHTS["interview_completion"] * icr_val +
            ENGAGEMENT_WEIGHTS["response_time"] * resp_time_val +
            ENGAGEMENT_WEIGHTS["offer_acceptance"] * offer_acc_val +
            ENGAGEMENT_WEIGHTS["applications"] * apps_val
        )

        # 3. Credibility
        github_val = compute_github_score(cand.signals.github_activity_score)
        scores_list = list(cand.signals.skill_assessment_scores.values())
        assessments_val = (sum(scores_list) / len(scores_list) / 100.0) if scores_list else 0.0
        profile_comp_val = cand.signals.profile_completeness_score / 100.0
        verification_val = (0.5 if cand.signals.verified_email else 0.0) + (0.5 if cand.signals.verified_phone else 0.0)
        endorsements_val = min(1.0, cand.signals.endorsements_received / 50.0)
        linkedin_val = 1.0 if cand.signals.linkedin_connected else 0.0

        credibility = (
            CREDIBILITY_WEIGHTS["github"] * github_val +
            CREDIBILITY_WEIGHTS["assessments"] * assessments_val +
            CREDIBILITY_WEIGHTS["profile_comp"] * profile_comp_val +
            CREDIBILITY_WEIGHTS["verification"] * verification_val +
            CREDIBILITY_WEIGHTS["endorsements"] * endorsements_val +
            CREDIBILITY_WEIGHTS["linkedin"] * linkedin_val
        )

        # Behavioral composite
        beh_score = (
            BEHAVIORAL_WEIGHTS["availability"] * availability +
            BEHAVIORAL_WEIGHTS["engagement"] * engagement +
            BEHAVIORAL_WEIGHTS["credibility"] * credibility
        )

        cand.features["availability_score"] = availability
        cand.features["engagement_score"] = engagement
        cand.features["credibility_score"] = credibility
        cand.features["behavioral_score"] = beh_score
        cand.features["behavioral_multiplier"] = get_behavioral_multiplier(beh_score)
        cand.features["platform_cred_score"] = credibility


def classify_company(company_name: str, industry: str, size_str: str, title: str) -> str:
    co = company_name.lower().strip()
    ind = industry.lower().strip()
    t = title.lower().strip()

    # 1. Services Blacklist
    is_blacklist = False
    for s in SERVICES_BLACKLIST:
        if s in co:
            is_blacklist = True
            break

    if is_blacklist or ind in SERVICES_INDUSTRIES:
        is_ml = any(x in t for x in ["ml", "machine learning", "ai", "nlp", "data scientist", "deep learning"])
        if is_ml:
            return "SERVICES_ML"
        return "SERVICES_OTHER"

    # 2. Product Companies
    is_product = False
    for p in PRODUCT_COMPANIES:
        if p in co:
            is_product = True
            break
    if is_product or ind in PRODUCT_INDUSTRIES:
        size = parse_company_size(size_str)
        if size <= 200:
            return "PRODUCT_STARTUP"
        elif size <= 5000:
            return "PRODUCT_SCALEUP"
        else:
            return "PRODUCT_ENTERPRISE"

    return "UNKNOWN"


def compute_tabular_features(survivors: list[Candidate], lookups: dict) -> None:
    """
    Computes exp_fit_score, company_type_score, location_score,
    title_chaser_penalty, edu_bonus, recency_score.
    """
    for cand in survivors:
        # Experience fit
        cand.features["exp_fit_score"] = compute_exp_fit(cand.years_of_experience)

        # Location score
        loc = cand.location.lower().strip()
        country = cand.country.lower().strip()
        if loc in LOCATION_PREFERRED:
            loc_score = 1.0
        elif loc in LOCATION_ACCEPTABLE:
            loc_score = 0.9
        elif country in {"india", "in"}:
            loc_score = LOCATION_OTHER_INDIA_SCORE
        else:
            if cand.signals.willing_to_relocate:
                loc_score = LOCATION_INTERNATIONAL_RELOCATE_SCORE
            else:
                loc_score = LOCATION_INTERNATIONAL_NO_RELOCATE_SCORE
        cand.features["location_score"] = loc_score

        # Company type score
        total_duration = 0
        weighted_score_sum = 0.0
        all_services = True

        for entry in cand.career_history:
            dur = entry.duration_months
            cls = classify_company(entry.company, entry.industry, entry.company_size, entry.title)
            score = COMPANY_TYPE_WEIGHTS[cls]
            weighted_score_sum += score * dur
            total_duration += dur
            if cls not in {"SERVICES_ML", "SERVICES_OTHER"}:
                all_services = False

        if total_duration > 0:
            comp_score = weighted_score_sum / total_duration
        else:
            cls = classify_company(cand.current_company, cand.current_industry, cand.current_company_size, cand.current_title)
            comp_score = COMPANY_TYPE_WEIGHTS[cls]
            if cls not in {"SERVICES_ML", "SERVICES_OTHER"}:
                all_services = False

        if all_services:
            comp_score = min(comp_score, 0.30)
        # CRITICAL FIX: Normalize to [0, 1] — raw range is 0.5-3.0
        cand.features["company_type_score"] = comp_score / 3.0

        # Title chaser penalty
        short_stints = sum(1 for entry in cand.career_history if entry.duration_months <= 18)
        cand.features["title_chaser_penalty"] = 0.20 if short_stints >= 3 else 0.0

        # Education tier bonus
        edu_bonus = 0.0
        if cand.education:
            edu_bonus = max(EDUCATION_TIER_BONUS.get(edu.tier.lower().strip(), 0.0) for edu in cand.education)
        cand.features["edu_bonus"] = edu_bonus

        # Recency score
        cand.features["recency_score"] = compute_recency_score((date(2026, 6, 1) - cand.signals.last_active_date).days)

        # Title relevance score — JD is for Senior AI Engineer
        # Candidates with ML/AI/NLP/Data Science titles fit better
        title_lower = cand.current_title.lower()
        headline_lower = cand.headline.lower() if cand.headline else ""

        # Strong ML/AI title keywords
        ml_title_keywords = [
            "machine learning", "ml ", "ml,", "deep learning", "ai ", "ai,",
            "artificial intelligence", "nlp", "natural language",
            "data scientist", "data science", "applied scientist",
            "research scientist", "search engineer", "ranking",
            "recommendation", "retrieval", "embedding",
            "computer vision",  # still ML even if wrong domain
        ]
        # Adjacent engineering titles
        adjacent_keywords = [
            "software engineer", "swe", "backend engineer",
            "platform engineer", "infrastructure", "devops",
            "full stack", "fullstack", "data engineer",
            "analytics engineer", "staff engineer", "principal engineer",
        ]
        # Non-relevant titles
        non_relevant_keywords = [
            "frontend", "front-end", "front end", "ui ",
            ".net", "dotnet", "java developer", "php",
            "cloud engineer", "network engineer", "qa ",
            "test engineer", "quality assurance",
            "project manager", "product manager", "scrum",
            "business analyst", "hr ", "marketing",
            "sales", "accountant", "content writer",
            "graphic designer", "mechanical", "civil",
            "customer support", "operations manager",
        ]

        combined_title = title_lower + " " + headline_lower

        if any(kw in combined_title for kw in ml_title_keywords):
            title_rel = 1.0
        elif any(kw in combined_title for kw in adjacent_keywords):
            title_rel = 0.7
        elif any(kw in combined_title for kw in non_relevant_keywords):
            title_rel = 0.25
        else:
            title_rel = 0.5  # Unknown titles get moderate score

        cand.features["title_relevance"] = title_rel


def count_matches(text: str, scanner) -> int:
    if not text:
        return 0
    if HAS_AHOCORASICK:
        count = 0
        text_low = text.lower()
        for _ in scanner.iter(text_low):
            count += 1
        return count
    else:
        return len(scanner.findall(text))


def compute_semantic_features(survivors: list[Candidate], lookups: dict, n_workers: int) -> None:
    """
    Computes career_nlp_score (source-weighted), skill_depth_score, domain_score.
    """
    for cand in survivors:
        # Career NLP score — source-weighted with temporal decay
        prod_weighted = 0.0
        res_weighted = 0.0

        # Source 1: Career descriptions (weight 1.0) + titles (weight 0.85)
        for entry in cand.career_history:
            normalized_desc = normalize_text(entry.description)
            normalized_title = normalize_text(entry.title)
            decay = temporal_decay(entry.years_ago)
            prod_hits_desc = count_matches(normalized_desc, lookups["production_scanner"])
            prod_hits_title = count_matches(normalized_title, lookups["production_scanner"])
            res_hits = count_matches(normalized_desc, lookups["research_scanner"])
            prod_weighted += (prod_hits_desc * SOURCE_WEIGHTS["career_descriptions"]
                            + prod_hits_title * SOURCE_WEIGHTS["current_title"]) * decay
            res_weighted += res_hits * decay

        # Source 2: Headline (weight 0.45)
        headline_prod = count_matches(normalize_text(cand.headline), lookups["production_scanner"])
        prod_weighted += headline_prod * SOURCE_WEIGHTS["headline"]

        # Source 3: Summary (weight 0.45)
        summary_prod = count_matches(normalize_text(cand.summary), lookups["production_scanner"])
        prod_weighted += summary_prod * SOURCE_WEIGHTS["summary"]

        cand.features["career_nlp_score"] = min(1.0, prod_weighted * 0.15 + res_weighted * 0.04)

        # Skill depth score
        pos_score = 0.0
        neg_penalty = 0.0
        neg_count = 0

        for s in cand.skills:
            tier = get_skill_tier_name(s.name)
            weight = get_skill_tier_weight(s.name)
            mult = PROFICIENCY_MULTIPLIERS.get(s.proficiency.lower().strip(), 1.0)

            if tier == "NEG":
                if neg_count < MAX_NEGATIVE_SKILLS:
                    neg_penalty += weight * mult
                    neg_count += 1
            else:
                pos_score += weight * mult

        stuffing_multiplier = 1.0
        num_skills = len(cand.skills)
        if num_skills > SKILL_STUFFING_THRESHOLD:
            over = num_skills - SKILL_STUFFING_THRESHOLD
            stuffing_multiplier = max(SKILL_STUFFING_PENALTY_FLOOR, 1.0 - over * SKILL_STUFFING_PENALTY_RATE)

        # Normalize to 0-1 range — neg_penalty is negative, so adding reduces score
        raw_skill_depth = max(0.0, pos_score + neg_penalty) * stuffing_multiplier
        cand.features["skill_depth_score"] = min(1.0, raw_skill_depth / 15.0)

        # Domain score
        votes = {domain: 0 for domain in DOMAIN_KEYWORDS}
        for s in cand.skills:
            s_low = s.name.lower().strip()
            for domain, keywords in DOMAIN_KEYWORDS.items():
                if s_low in keywords:
                    votes[domain] += 1

        for entry in cand.career_history:
            desc_low = entry.description.lower()
            for domain, keywords in DOMAIN_KEYWORDS.items():
                for kw in keywords:
                    if kw in desc_low:
                        votes[domain] += 1

        primary_domain = "NOT_TECH"
        max_votes = 0
        for domain, count in votes.items():
            if count > max_votes:
                max_votes = count
                primary_domain = domain

        base_score = DOMAIN_SCORES.get(primary_domain, 0.0)
        has_nlp_ir_signal = (votes.get("NLP_IR", 0) > 0)
        has_production_evidence = cand.features.get("career_nlp_score", 0.0) > 0.2

        if primary_domain == "GENERAL_ML" and has_nlp_ir_signal:
            domain_score = 0.75
        elif primary_domain in {"CV", "SPEECH"} and has_nlp_ir_signal:
            domain_score = 0.55
        elif primary_domain == "DATA_ENG" and has_production_evidence:
            domain_score = 0.60
        else:
            domain_score = base_score

        cand.features["domain_score"] = domain_score
