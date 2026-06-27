"""
dashboard.py — Streamlit dashboard for the Redrob Candidate Ranking Engine.

Interactive sandbox with:
  • Run Engine tab — process demo/uploaded candidates through full pipeline
  • Results tab — ranked candidates with deep-dive feature breakdowns
  • Ask the Engine tab — interactive Q&A for judges to query candidates
  • Analytics tab — visual charts and distributions
  • Architecture tab — full system documentation

Satisfies Section 10.5 sandbox requirement.
Deploy to Streamlit Cloud or HuggingFace Spaces.
"""
import io
import json
import time
import sys
import csv as csv_mod
import math
from pathlib import Path
from datetime import date
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Redrob AI Ranking Engine — ForgeScaler",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    padding: 2.5rem 2rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(102,126,234,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }
  .hero h1 { font-size: 2rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; position: relative; }
  .hero p  { color: rgba(255,255,255,0.7); margin: 0.4rem 0 0; font-size: 1rem; position: relative; }
  .hero .team-badge {
    display: inline-block;
    background: linear-gradient(135deg, #43e97b, #38f9d7);
    color: #0f0c29;
    font-weight: 600;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    margin-top: 0.5rem;
    position: relative;
  }

  .metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    color: white;
    text-align: center;
    transition: transform 0.2s;
  }
  .metric-card:hover { transform: translateY(-2px); }
  .metric-card .val { font-size: 2rem; font-weight: 700; }
  .metric-card .lbl { font-size: 0.8rem; opacity: 0.85; margin-top: 0.2rem; }

  .metric-card-green {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    color: #0f0c29;
    text-align: center;
  }
  .metric-card-green .val { font-size: 2rem; font-weight: 700; }
  .metric-card-green .lbl { font-size: 0.8rem; opacity: 0.85; margin-top: 0.2rem; }

  .metric-card-amber {
    background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    color: #333;
    text-align: center;
  }
  .metric-card-amber .val { font-size: 2rem; font-weight: 700; }
  .metric-card-amber .lbl { font-size: 0.8rem; opacity: 0.85; margin-top: 0.2rem; }

  .rank-badge {
    display: inline-block;
    background: linear-gradient(135deg, #f6d365, #fda085);
    color: #333;
    font-weight: 700;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.85rem;
  }
  .rank-badge.top3 {
    background: linear-gradient(135deg, #43e97b, #38f9d7);
  }
  .rank-badge.top10 {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
  }

  .candidate-row {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s, transform 0.2s;
  }
  .candidate-row:hover {
    border-color: rgba(102,126,234,0.5);
    transform: translateX(4px);
  }

  .score-bar-bg {
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    height: 6px;
    margin-top: 0.4rem;
  }
  .score-bar-fill {
    height: 6px;
    border-radius: 4px;
    transition: width 0.5s ease;
  }
  .score-bar-green { background: linear-gradient(90deg, #43e97b, #38f9d7); }
  .score-bar-blue { background: linear-gradient(90deg, #667eea, #764ba2); }
  .score-bar-amber { background: linear-gradient(90deg, #f6d365, #fda085); }

  .tag {
    display: inline-block;
    background: rgba(102,126,234,0.2);
    border: 1px solid rgba(102,126,234,0.4);
    color: #a8b4ff;
    padding: 0.15rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    margin-right: 0.3rem;
    margin-bottom: 0.2rem;
  }
  .tag-green {
    background: rgba(67,233,123,0.15);
    border-color: rgba(67,233,123,0.4);
    color: #43e97b;
  }
  .tag-amber {
    background: rgba(246,211,101,0.15);
    border-color: rgba(246,211,101,0.4);
    color: #f6d365;
  }
  .tag-red {
    background: rgba(255,99,99,0.15);
    border-color: rgba(255,99,99,0.4);
    color: #ff6363;
  }

  .qa-answer {
    background: rgba(102,126,234,0.08);
    border-left: 3px solid #667eea;
    padding: 1rem 1.2rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
  }

  .comparison-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 1.2rem;
  }

  .stage-bar {
    display: flex;
    align-items: center;
    margin: 0.3rem 0;
  }
  .stage-label { width: 200px; font-size: 0.85rem; color: #aaa; }
  .stage-time { width: 60px; text-align: right; font-size: 0.85rem; color: #43e97b; font-weight: 600; }

  footer { visibility: hidden; }
  .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎯 Redrob AI Candidate Ranking Engine</h1>
  <p>Senior AI Engineer · Hybrid Rule-Based + Feature-Weighted Pipeline · CPU-Only · <5 min on 100K candidates</p>
  <div class="team-badge">Team ForgeScaler</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Engine Configuration")

    st.markdown("**How to use:**")
    st.markdown("""
    1. Go to **Run Engine** tab
    2. Select data source (demo or upload)
    3. Click **Run Ranking Engine**
    4. Explore results, ask questions, view analytics
    """)

    st.divider()
    st.markdown("**📊 Full Pipeline Benchmark**")
    st.markdown("""
    <small style='color:#888'>Measured on 100,000 candidates (465 MB)</small>
    """, unsafe_allow_html=True)

    benchmark_stages = [
        ("Bootstrap", "0.03s", 0.03),
        ("Ingestion", "10.5s", 10.46),
        ("Early Elimination", "0.8s", 0.84),
        ("Behavioral Features", "0.1s", 0.13),
        ("Tabular Features", "0.6s", 0.57),
        ("Semantic NLP", "14.3s", 14.26),
        ("Honeypot Detection", "0.2s", 0.19),
        ("Scoring", "0.1s", 0.09),
        ("Output", "0.04s", 0.04),
    ]
    total_bench = sum(t for _, _, t in benchmark_stages)
    for name, t_str, t_val in benchmark_stages:
        pct = t_val / total_bench * 100
        st.markdown(f"""
        <div class="stage-bar">
          <span class="stage-label">{name}</span>
          <span class="stage-time">{t_str}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:0.5rem; padding:0.5rem; background:rgba(67,233,123,0.1); border-radius:8px; text-align:center">
      <strong style="color:#43e97b">Total: {total_bench:.1f}s</strong>
      <span style="color:#888; font-size:0.8rem"> / 300s budget</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**Scoring Formula**")
    st.code("""final_score =
  technical_score
  × title_relevance   # 0.25–1.0
  × behavioral_mult   # 0.35–1.15
  + edu_bonus + micro_bonuses

technical_score =
  0.35 × career_nlp
  0.15 × skill_depth
  0.12 × company_type
  0.10 × domain
  0.08 × exp_fit
  0.07 × recency
  0.05 × location
  0.05 × platform_cred""", language="text")


# ── Helper: Run pipeline ──────────────────────────────────────────────────────
def run_pipeline(candidates_data, data_source_label):
    """Run the full ranking pipeline on a list of candidate dicts.
    Returns (rows, elapsed, n_input, n_survivors, n_eliminated, hp_count, stage_times)."""
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.ingest import build_lookups
    from src.models import parse_candidate
    from src.filters import early_eliminate, honeypot_full_pass
    from src.features import (
        compute_behavioral_features,
        compute_tabular_features,
        compute_semantic_features,
    )
    from src.scorer import compute_scores
    from src.output import select_top_100, _generate_reasoning

    stage_times = []
    t0 = time.perf_counter()

    # Stage 0
    t_s = time.perf_counter()
    lookups = build_lookups()
    stage_times.append(("Bootstrap", time.perf_counter() - t_s))

    # Stage 1 — Parse candidates
    t_s = time.perf_counter()
    candidates = [c for raw in candidates_data if (c := parse_candidate(raw)) is not None]
    stage_times.append(("Ingestion & Parse", time.perf_counter() - t_s))

    if not candidates:
        return None, 0, 0, 0, 0, 0, stage_times

    # Stage 2
    t_s = time.perf_counter()
    survivors, eliminated = early_eliminate(candidates, lookups)
    stage_times.append(("Early Elimination", time.perf_counter() - t_s))

    if not survivors:
        return None, time.perf_counter() - t0, len(candidates), 0, len(eliminated), 0, stage_times

    # Stage 3a
    t_s = time.perf_counter()
    compute_behavioral_features(survivors)
    stage_times.append(("Behavioral Features", time.perf_counter() - t_s))

    # Stage 3b
    t_s = time.perf_counter()
    compute_tabular_features(survivors, lookups)
    stage_times.append(("Tabular Features", time.perf_counter() - t_s))

    # Stage 3c
    t_s = time.perf_counter()
    compute_semantic_features(survivors, lookups, n_workers=1)
    stage_times.append(("Semantic NLP", time.perf_counter() - t_s))

    # Stage 4
    t_s = time.perf_counter()
    honeypot_full_pass(survivors)
    hp_count = sum(1 for c in survivors if c.honeypot_flag)
    stage_times.append(("Honeypot Detection", time.perf_counter() - t_s))

    # Stage 5
    t_s = time.perf_counter()
    compute_scores(survivors)
    stage_times.append(("Scoring", time.perf_counter() - t_s))

    # Stage 6
    t_s = time.perf_counter()
    top_n = min(100, len(survivors))
    top_100 = select_top_100(survivors)[:top_n]
    stage_times.append(("Selection & Guardrails", time.perf_counter() - t_s))

    # Stage 7 — Build rows
    t_s = time.perf_counter()
    max_score = max((c.final_score for c in top_100), default=1.0)
    if max_score <= 0:
        max_score = 1.0
    rows = []
    for i, c in enumerate(top_100):
        rank = i + 1
        c.rank = rank
        sc = round(max(0.0, min(1.0, c.final_score / max_score)), 4)

        # Collect skill tiers for display
        from src.config import get_skill_tier_name
        skill_tiers = {}
        for s in c.skills:
            tier = get_skill_tier_name(s.name)
            if tier not in skill_tiers:
                skill_tiers[tier] = []
            skill_tiers[tier].append(s.name)

        rows.append({
            "rank": rank,
            "candidate_id": c.candidate_id,
            "score": sc,
            "raw_score": c.final_score,
            "title": c.current_title,
            "company": c.current_company,
            "yoe": c.years_of_experience,
            "location": c.location,
            "country": c.country,
            "honeypot": c.honeypot_flag,
            "honeypot_confidence": c.honeypot_confidence,
            "hard_disqualify": c.hard_disqualify,
            "reasoning": _generate_reasoning(c, rank),
            "features": dict(c.features),
            "signals": {
                "recruiter_response_rate": c.signals.recruiter_response_rate,
                "notice_period_days": c.signals.notice_period_days,
                "github_activity_score": c.signals.github_activity_score,
                "open_to_work": c.signals.open_to_work_flag,
                "willing_to_relocate": c.signals.willing_to_relocate,
                "profile_completeness": c.signals.profile_completeness_score,
                "search_appearance_30d": c.signals.search_appearance_30d,
                "saved_by_recruiters_30d": c.signals.saved_by_recruiters_30d,
                "preferred_work_mode": c.signals.preferred_work_mode,
                "interview_completion_rate": c.signals.interview_completion_rate,
                "avg_response_time_hours": c.signals.avg_response_time_hours,
            },
            "skill_tiers": skill_tiers,
            "headline": c.headline,
            "summary": c.summary,
        })
    stage_times.append(("Output Generation", time.perf_counter() - t_s))

    elapsed = time.perf_counter() - t0
    return rows, elapsed, len(candidates), len(survivors), len(eliminated), hp_count, stage_times


# ── Main content ──────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Run Engine",
    "📊 Results",
    "❓ Ask the Engine",
    "📈 Analytics",
    "🏗️ Architecture",
])

with tab1:
    st.markdown("### Input Candidates")

    st.info("""
    **About the data sources:**
    - **Demo dataset (50 candidates)**: Curated subset from the actual 100K pipeline run — includes top-ranked candidates, mid-range, honeypots, and eliminated candidates to demonstrate the engine's full capability.
    - **Upload JSONL/JSON**: Upload your own candidate data in the same format as `candidates.jsonl` or `sample_candidates.json`.
    """)

    input_mode = st.radio(
        "Input source",
        ["Use demo dataset (50 curated candidates)", "Upload JSONL/JSON file"],
        horizontal=True,
    )

    uploaded_file = None
    if input_mode == "Upload JSONL/JSON file":
        uploaded_file = st.file_uploader(
            "Upload candidates file (JSONL or JSON array, ≤100 candidates recommended for sandbox)",
            type=["jsonl", "json"],
            help="Plain-text JSONL file (one JSON object per line) or JSON array file.",
        )

    st.divider()
    run_col, info_col = st.columns([2, 3])

    with run_col:
        run_btn = st.button("▶ Run Ranking Engine", type="primary", use_container_width=True)

    with info_col:
        st.markdown("""
        <div style="background:rgba(102,126,234,0.1); border:1px solid rgba(102,126,234,0.3); border-radius:8px; padding:0.8rem 1rem; font-size:0.9rem">
            🕐 <strong>Demo: ~1-2s</strong> · <strong>Full 100K: ~27s</strong> on CPU<br>
            <span style="color:#888">No GPU, no API calls, no network access</span>
        </div>
        """, unsafe_allow_html=True)

    if run_btn:
        project_root = Path(__file__).resolve().parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        try:
            progress = st.progress(0, text="Starting pipeline...")

            # Load input data
            progress.progress(5, "Loading candidate data...")
            candidates_data = []

            if input_mode == "Use demo dataset (50 curated candidates)":
                demo_path = project_root / "demo_candidates.jsonl"
                if not demo_path.exists():
                    # Fallback to sample_candidates.json
                    sample_path = project_root / ".." / "India_runs_data_and_ai_challenge" / "sample_candidates.json"
                    if not sample_path.exists():
                        sample_path = project_root / "sample_candidates.json"
                    if sample_path.exists():
                        with open(sample_path, "r", encoding="utf-8") as f:
                            candidates_data = json.load(f)
                    else:
                        st.error("No demo data found. Please upload a file.")
                        st.stop()
                else:
                    with open(demo_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line_str = line.strip()
                            if line_str:
                                try:
                                    candidates_data.append(json.loads(line_str))
                                except json.JSONDecodeError:
                                    pass
            else:
                if uploaded_file is None:
                    st.warning("Please upload a file first.")
                    st.stop()
                content = uploaded_file.read().decode("utf-8")
                # Try JSON array first, then JSONL
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        candidates_data = parsed
                    else:
                        candidates_data = [parsed]
                except json.JSONDecodeError:
                    # Try JSONL
                    for line in content.splitlines():
                        line_str = line.strip()
                        if line_str:
                            try:
                                candidates_data.append(json.loads(line_str))
                            except json.JSONDecodeError:
                                pass

            if not candidates_data:
                st.error("No valid candidate data found in the input.")
                st.stop()

            progress.progress(15, f"Processing {len(candidates_data)} candidates...")

            rows, elapsed, n_input, n_survivors, n_eliminated, hp_count, stage_times = run_pipeline(
                candidates_data, input_mode
            )

            if rows is None or len(rows) == 0:
                progress.progress(100, "Pipeline complete — no candidates survived filtering.")
                st.warning("No candidates survived the pipeline. This can happen if all candidates are below the quality threshold (YOE < 2, no tech skills, or honeypot flagged).")
                # Store empty results to prevent slider errors
                st.session_state["results"] = []
                st.session_state["elapsed"] = elapsed
                st.session_state["n_input"] = n_input
                st.session_state["n_survivors"] = n_survivors
                st.session_state["n_eliminated"] = n_eliminated
                st.session_state["hp_count"] = hp_count
                st.session_state["stage_times"] = stage_times
                st.stop()

            progress.progress(100, f"Done in {elapsed:.2f}s!")

            st.session_state["results"] = rows
            st.session_state["elapsed"] = elapsed
            st.session_state["n_input"] = n_input
            st.session_state["n_survivors"] = n_survivors
            st.session_state["n_eliminated"] = n_eliminated
            st.session_state["hp_count"] = hp_count
            st.session_state["stage_times"] = stage_times

            st.success(f"✅ Pipeline complete in {elapsed:.2f}s — ranked {len(rows)} candidates")
            st.rerun()

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            import traceback
            st.code(traceback.format_exc())


with tab2:
    if "results" not in st.session_state or not st.session_state["results"]:
        st.info("Run the engine first (go to the **Run Engine** tab).")
    else:
        rows = st.session_state["results"]
        elapsed = st.session_state["elapsed"]
        n_in = st.session_state["n_input"]
        n_surv = st.session_state["n_survivors"]
        n_elim = st.session_state["n_eliminated"]
        hp = st.session_state["hp_count"]
        stage_times = st.session_state.get("stage_times", [])

        # Metrics row
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        with m1:
            st.markdown(f"""<div class="metric-card"><div class="val">{n_in}</div><div class="lbl">Input Candidates</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="metric-card-green"><div class="val">{n_surv}</div><div class="lbl">Survivors</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="metric-card"><div class="val">{n_elim}</div><div class="lbl">Eliminated</div></div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""<div class="metric-card-amber"><div class="val">{hp}</div><div class="lbl">Honeypots</div></div>""", unsafe_allow_html=True)
        with m5:
            st.markdown(f"""<div class="metric-card"><div class="val">{len(rows)}</div><div class="lbl">Ranked</div></div>""", unsafe_allow_html=True)
        with m6:
            st.markdown(f"""<div class="metric-card-green"><div class="val">{elapsed:.2f}s</div><div class="lbl">Runtime</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Per-stage timing breakdown
        if stage_times:
            with st.expander("⏱️ Per-Stage Timing Breakdown", expanded=False):
                total_t = sum(t for _, t in stage_times)
                for name, t in stage_times:
                    pct = (t / total_t * 100) if total_t > 0 else 0
                    st.markdown(f"""
                    <div style="display:flex; align-items:center; margin:0.2rem 0">
                      <span style="width:180px; font-size:0.85rem; color:#ccc">{name}</span>
                      <div style="flex:1; background:rgba(255,255,255,0.08); border-radius:4px; height:12px; margin:0 0.5rem">
                        <div style="width:{pct}%; background:linear-gradient(90deg,#667eea,#764ba2); height:12px; border-radius:4px"></div>
                      </div>
                      <span style="width:60px; text-align:right; font-size:0.85rem; color:#43e97b; font-weight:600">{t:.3f}s</span>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="text-align:center; margin-top:0.5rem; color:#888; font-size:0.85rem">
                    Demo total: <strong style="color:#43e97b">{total_t:.2f}s</strong> ·
                    100K benchmark: <strong style="color:#667eea">~27s</strong> /
                    <span>300s budget</span>
                </div>
                """, unsafe_allow_html=True)

        # Download CSV
        csv_out = io.StringIO()
        writer = csv_mod.writer(csv_out)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for r in rows:
            writer.writerow([r["candidate_id"], r["rank"], f"{r['score']:.4f}", r["reasoning"]])

        st.download_button(
            "⬇️ Download submission.csv",
            data=csv_out.getvalue().encode("utf-8"),
            file_name="submission.csv",
            mime="text/csv",
        )

        st.divider()
        st.markdown("### 🏆 Ranked Candidates")

        # Filter options
        filter_col1, filter_col2 = st.columns([1, 1])
        with filter_col1:
            max_show = max(5, len(rows))
            show_top = st.slider(
                "Show top N candidates",
                min_value=1,
                max_value=max_show,
                value=min(20, max_show),
            )
        with filter_col2:
            show_features = st.checkbox("Show feature breakdown", value=False)

        for r in rows[:show_top]:
            badge_cls = "top3" if r["rank"] <= 3 else ("top10" if r["rank"] <= 10 else "")
            score_pct = int(r["score"] * 100)
            bar_cls = "score-bar-green" if r["rank"] <= 10 else ("score-bar-blue" if r["rank"] <= 30 else "score-bar-amber")

            hp_warn = "⚠️ " if r["honeypot"] else ""

            st.markdown(f"""
<div class="candidate-row">
  <div style="display:flex; justify-content:space-between; align-items:center">
    <div>
      <span class="rank-badge {badge_cls}">#{r['rank']}</span>
      &nbsp;<strong>{hp_warn}{r['candidate_id']}</strong>
      &nbsp;<span style="color:#aaa">·</span>&nbsp;
      <span style="color:#e2e8f0">{r['title']}</span>
      &nbsp;<span style="color:#666">at</span>&nbsp;
      <span style="color:#a8b4ff">{r['company']}</span>
    </div>
    <div style="text-align:right">
      <strong style="color:#43e97b">{r['score']:.4f}</strong>
      <span style="color:#666; font-size:0.8rem"> · {r['yoe']:.1f}yr · {r['location']}</span>
    </div>
  </div>
  <div class="score-bar-bg"><div class="{bar_cls} score-bar-fill" style="width:{score_pct}%"></div></div>
  <div style="color:#9ca3af; font-size:0.82rem; margin-top:0.5rem">{r['reasoning']}</div>
</div>
""", unsafe_allow_html=True)

            if show_features and r.get("features"):
                with st.expander(f"🔍 Feature breakdown — {r['candidate_id']}", expanded=False):
                    feats = r["features"]
                    sigs = r.get("signals", {})

                    f1, f2, f3, f4 = st.columns(4)
                    with f1:
                        st.markdown("**Technical Scores**")
                        st.metric("Career NLP", f"{feats.get('career_nlp_score', 0):.3f}")
                        st.metric("Skill Depth", f"{feats.get('skill_depth_score', 0):.3f}")
                        st.metric("Domain", f"{feats.get('domain_score', 0):.3f}")
                    with f2:
                        st.markdown("**Fit Scores**")
                        st.metric("Exp Fit", f"{feats.get('exp_fit_score', 0):.3f}")
                        st.metric("Company Type", f"{feats.get('company_type_score', 0):.3f}")
                        st.metric("Location", f"{feats.get('location_score', 0):.3f}")
                    with f3:
                        st.markdown("**Behavioral**")
                        st.metric("Behavioral", f"{feats.get('behavioral_score', 0):.3f}")
                        st.metric("Multiplier", f"{feats.get('behavioral_multiplier', 1):.2f}×")
                        st.metric("Title Relevance", f"{feats.get('title_relevance', 0):.2f}")
                    with f4:
                        st.markdown("**Signals**")
                        st.metric("Response Rate", f"{sigs.get('recruiter_response_rate', 0):.0%}")
                        st.metric("Notice Period", f"{sigs.get('notice_period_days', 0)}d")
                        gh = sigs.get('github_activity_score', -1)
                        st.metric("GitHub", f"{gh:.0f}" if gh >= 0 else "N/A")

                    # Skill tier tags
                    skill_tiers = r.get("skill_tiers", {})
                    if skill_tiers:
                        st.markdown("**Skills by Tier:**")
                        tier_labels = {"A": "🟢 Tier A (Core)", "B": "🔵 Tier B (Strong)", "C": "🟡 Tier C (NLP/ML)", "D": "⚪ Tier D (Infra)", "NEG": "🔴 Negative"}
                        for tier_key in ["A", "B", "C", "D", "NEG"]:
                            if tier_key in skill_tiers:
                                tag_class = {"A": "tag-green", "B": "tag", "C": "tag-amber", "D": "tag", "NEG": "tag-red"}.get(tier_key, "tag")
                                skills_html = " ".join(f'<span class="{tag_class}">{s}</span>' for s in skill_tiers[tier_key])
                                st.markdown(f"{tier_labels.get(tier_key, tier_key)}: {skills_html}", unsafe_allow_html=True)


with tab3:
    st.markdown("### ❓ Ask the Engine")
    st.markdown("Interact with the ranking engine — query candidates, compare them, understand decisions.")

    if "results" not in st.session_state or not st.session_state["results"]:
        st.info("Run the engine first (go to the **Run Engine** tab) to enable Q&A.")
    else:
        rows = st.session_state["results"]
        rows_by_id = {r["candidate_id"]: r for r in rows}

        qa_mode = st.radio(
            "Query type",
            ["🔍 Lookup Candidate", "⚖️ Compare Two Candidates", "🎯 Filter by Criteria", "💡 Explain Scoring Decision"],
            horizontal=True,
        )

        if qa_mode == "🔍 Lookup Candidate":
            cid_options = [f"{r['candidate_id']} — #{r['rank']} {r['title']} at {r['company']}" for r in rows]
            selected = st.selectbox("Select a candidate", cid_options)
            if selected:
                cid = selected.split(" — ")[0]
                r = rows_by_id.get(cid)
                if r:
                    st.markdown(f"""
                    <div class="qa-answer">
                        <h4>{r['candidate_id']} — Rank #{r['rank']}</h4>
                        <p><strong>{r['title']}</strong> at <strong>{r['company']}</strong> · {r['yoe']:.1f} years · {r['location']}, {r['country']}</p>
                        <p><strong>Score:</strong> {r['score']:.4f} (raw: {r['raw_score']:.4f})</p>
                        <p><strong>Reasoning:</strong> {r['reasoning']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    feats = r.get("features", {})
                    st.markdown("#### Feature Breakdown")
                    feat_data = {
                        "Feature": ["Career NLP", "Skill Depth", "Domain", "Exp Fit", "Company Type",
                                   "Location", "Recency", "Platform Cred", "Title Relevance",
                                   "Behavioral Mult", "Edu Bonus"],
                        "Score": [
                            f"{feats.get('career_nlp_score', 0):.3f}",
                            f"{feats.get('skill_depth_score', 0):.3f}",
                            f"{feats.get('domain_score', 0):.3f}",
                            f"{feats.get('exp_fit_score', 0):.3f}",
                            f"{feats.get('company_type_score', 0):.3f}",
                            f"{feats.get('location_score', 0):.3f}",
                            f"{feats.get('recency_score', 0):.3f}",
                            f"{feats.get('platform_cred_score', 0):.3f}",
                            f"{feats.get('title_relevance', 0):.2f}",
                            f"{feats.get('behavioral_multiplier', 1):.2f}×",
                            f"{feats.get('edu_bonus', 0):.3f}",
                        ],
                        "Weight": ["0.35", "0.15", "0.10", "0.08", "0.12", "0.05", "0.07", "0.05",
                                  "mult", "mult", "additive"],
                    }
                    st.table(feat_data)

                    if r.get("honeypot"):
                        st.warning(f"⚠️ Honeypot flagged — confidence: {r.get('honeypot_confidence', 0):.2f}")
                    if r.get("hard_disqualify"):
                        st.error("🚫 Hard disqualified (low response rate + low interview completion)")

        elif qa_mode == "⚖️ Compare Two Candidates":
            cid_options = [f"{r['candidate_id']} — #{r['rank']} {r['title']} at {r['company']}" for r in rows]
            col1, col2 = st.columns(2)
            with col1:
                sel1 = st.selectbox("Candidate A", cid_options, index=0, key="cmp1")
            with col2:
                sel2 = st.selectbox("Candidate B", cid_options, index=min(1, len(cid_options)-1), key="cmp2")

            if sel1 and sel2:
                cid1 = sel1.split(" — ")[0]
                cid2 = sel2.split(" — ")[0]
                r1 = rows_by_id.get(cid1)
                r2 = rows_by_id.get(cid2)

                if r1 and r2:
                    compare_features = [
                        ("Career NLP", "career_nlp_score"),
                        ("Skill Depth", "skill_depth_score"),
                        ("Domain", "domain_score"),
                        ("Exp Fit", "exp_fit_score"),
                        ("Company Type", "company_type_score"),
                        ("Location", "location_score"),
                        ("Title Relevance", "title_relevance"),
                        ("Behavioral Mult", "behavioral_multiplier"),
                    ]

                    st.markdown("#### Side-by-Side Comparison")
                    header_col1, header_col2 = st.columns(2)
                    with header_col1:
                        st.markdown(f"""
                        <div class="comparison-card">
                            <strong>#{r1['rank']}</strong> · {r1['candidate_id']}<br>
                            {r1['title']} at {r1['company']}<br>
                            <span style="color:#43e97b; font-size:1.2rem; font-weight:700">{r1['score']:.4f}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with header_col2:
                        st.markdown(f"""
                        <div class="comparison-card">
                            <strong>#{r2['rank']}</strong> · {r2['candidate_id']}<br>
                            {r2['title']} at {r2['company']}<br>
                            <span style="color:#43e97b; font-size:1.2rem; font-weight:700">{r2['score']:.4f}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    compare_data = {"Feature": [], "Candidate A": [], "Candidate B": [], "Winner": []}
                    for label, key in compare_features:
                        v1 = r1.get("features", {}).get(key, 0)
                        v2 = r2.get("features", {}).get(key, 0)
                        compare_data["Feature"].append(label)
                        compare_data["Candidate A"].append(f"{v1:.3f}")
                        compare_data["Candidate B"].append(f"{v2:.3f}")
                        if v1 > v2:
                            compare_data["Winner"].append("← A")
                        elif v2 > v1:
                            compare_data["Winner"].append("B →")
                        else:
                            compare_data["Winner"].append("Tie")
                    st.table(compare_data)

                    # Explain why A > B or B > A
                    delta = r1["raw_score"] - r2["raw_score"]
                    if delta > 0:
                        st.markdown(f"""
                        <div class="qa-answer">
                            <strong>Why {r1['candidate_id']} ranks higher:</strong><br>
                            Score delta: <strong>{delta:.4f}</strong>. The primary differentiators are the features where A wins above.
                        </div>
                        """, unsafe_allow_html=True)
                    elif delta < 0:
                        st.markdown(f"""
                        <div class="qa-answer">
                            <strong>Why {r2['candidate_id']} ranks higher:</strong><br>
                            Score delta: <strong>{abs(delta):.4f}</strong>. The primary differentiators are the features where B wins above.
                        </div>
                        """, unsafe_allow_html=True)

        elif qa_mode == "🎯 Filter by Criteria":
            st.markdown("Filter ranked candidates by specific criteria:")
            fcol1, fcol2, fcol3 = st.columns(3)
            with fcol1:
                min_score = st.slider("Minimum score", 0.0, 1.0, 0.0, 0.01)
            with fcol2:
                min_yoe = st.slider("Min experience (years)", 0.0, 20.0, 0.0, 0.5)
            with fcol3:
                company_filter = st.text_input("Company contains", "")

            filtered = [r for r in rows
                       if r["score"] >= min_score
                       and r["yoe"] >= min_yoe
                       and (not company_filter or company_filter.lower() in r["company"].lower())]

            st.markdown(f"**{len(filtered)}** candidates match your criteria:")
            for r in filtered[:20]:
                st.markdown(f"#{r['rank']} **{r['candidate_id']}** · {r['title']} at {r['company']} · {r['score']:.4f} · {r['yoe']:.1f}yr")

        elif qa_mode == "💡 Explain Scoring Decision":
            st.markdown("""
            **How does the engine decide rankings?**

            The engine uses a **multi-signal scoring formula** designed to match the JD's explicit requirements:
            """)

            st.markdown("""
            <div class="qa-answer">
                <strong>1. Anti-Gaming Strategy (Critical)</strong><br>
                The JD explicitly warns: <em>"The right answer is NOT find candidates whose skills section contains the most AI keywords."</em><br><br>
                Our defense: <strong>title_relevance multiplier</strong> — candidates with non-ML titles (Frontend Engineer, Accountant, Project Manager) get 0.25× regardless of how many AI keywords they list. A "Project Manager at Wipro" listing FAISS, Pinecone, and LLMs still scores low because the title doesn't match.<br><br>
                <strong>2. Production over Research</strong><br>
                Career text is scanned for production phrases ("deployed", "shipped", "real-time serving") with <strong>temporal decay</strong> — recent production experience (2024) counts more than old (2019).<br><br>
                <strong>3. Services Company Penalty</strong><br>
                All-services careers (TCS, Infosys, Wipro entire career) are capped at 0.30 company_type_score. But if someone did ML at Infosys, they get 1.2× (SERVICES_ML) instead of 0.5× (SERVICES_OTHER).<br><br>
                <strong>4. Honeypot Detection</strong><br>
                10 rules detect impossible profiles: salary min > max, YOE exceeding career span, overlapping tenures, fixture company names (Dunder Mifflin, Initech), etc.
            </div>
            """, unsafe_allow_html=True)


with tab4:
    st.markdown("### 📈 Analytics Dashboard")

    if "results" not in st.session_state or not st.session_state["results"]:
        st.info("Run the engine first to see analytics.")
    else:
        rows = st.session_state["results"]

        # Score distribution
        st.markdown("#### Score Distribution")
        scores = [r["score"] for r in rows]
        # Create a simple text-based histogram
        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        hist = [0] * (len(bins) - 1)
        for s in scores:
            for i in range(len(bins) - 1):
                if bins[i] <= s < bins[i+1] or (i == len(bins)-2 and s == bins[i+1]):
                    hist[i] += 1
                    break

        for i in range(len(hist)):
            bar_width = int(hist[i] / max(max(hist), 1) * 100)
            label = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
            st.markdown(f"""
            <div style="display:flex; align-items:center; margin:0.3rem 0">
              <span style="width:80px; font-size:0.85rem; color:#aaa">{label}</span>
              <div style="flex:1; background:rgba(255,255,255,0.05); border-radius:4px; height:20px; margin:0 0.5rem">
                <div style="width:{bar_width}%; background:linear-gradient(90deg,#667eea,#764ba2); height:20px; border-radius:4px; display:flex; align-items:center; padding-left:0.5rem">
                  <span style="color:white; font-size:0.75rem; font-weight:600">{hist[i]}</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Feature averages for top 10 vs rest
        st.markdown("#### Top 10 vs Rest — Feature Averages")
        top10 = rows[:10]
        rest = rows[10:]

        feature_keys = [
            ("Career NLP", "career_nlp_score"),
            ("Skill Depth", "skill_depth_score"),
            ("Domain", "domain_score"),
            ("Exp Fit", "exp_fit_score"),
            ("Company Type", "company_type_score"),
            ("Title Relevance", "title_relevance"),
        ]

        if rest:
            avg_data = {"Feature": [], "Top 10 Avg": [], "Rest Avg": [], "Delta": []}
            for label, key in feature_keys:
                avg_top = sum(r["features"].get(key, 0) for r in top10) / len(top10) if top10 else 0
                avg_rest = sum(r["features"].get(key, 0) for r in rest) / len(rest) if rest else 0
                avg_data["Feature"].append(label)
                avg_data["Top 10 Avg"].append(f"{avg_top:.3f}")
                avg_data["Rest Avg"].append(f"{avg_rest:.3f}")
                avg_data["Delta"].append(f"+{avg_top - avg_rest:.3f}" if avg_top > avg_rest else f"{avg_top - avg_rest:.3f}")
            st.table(avg_data)

        st.divider()

        # Company type breakdown
        st.markdown("#### Company Distribution")
        companies = {}
        for r in rows:
            co = r["company"]
            companies[co] = companies.get(co, 0) + 1
        sorted_companies = sorted(companies.items(), key=lambda x: -x[1])
        for co, count in sorted_companies[:15]:
            bar_w = int(count / max(max(companies.values()), 1) * 100)
            st.markdown(f"""
            <div style="display:flex; align-items:center; margin:0.2rem 0">
              <span style="width:180px; font-size:0.85rem; color:#a8b4ff">{co}</span>
              <div style="flex:1; background:rgba(255,255,255,0.05); border-radius:4px; height:16px; margin:0 0.5rem">
                <div style="width:{bar_w}%; background:linear-gradient(90deg,#43e97b,#38f9d7); height:16px; border-radius:4px"></div>
              </div>
              <span style="width:30px; text-align:right; font-size:0.85rem; color:#43e97b">{count}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Location distribution
        st.markdown("#### Location Distribution")
        locations = {}
        for r in rows:
            loc = r["location"]
            locations[loc] = locations.get(loc, 0) + 1
        sorted_locs = sorted(locations.items(), key=lambda x: -x[1])
        for loc, count in sorted_locs[:10]:
            bar_w = int(count / max(max(locations.values()), 1) * 100)
            st.markdown(f"""
            <div style="display:flex; align-items:center; margin:0.2rem 0">
              <span style="width:180px; font-size:0.85rem; color:#ccc">{loc}</span>
              <div style="flex:1; background:rgba(255,255,255,0.05); border-radius:4px; height:16px; margin:0 0.5rem">
                <div style="width:{bar_w}%; background:linear-gradient(90deg,#f6d365,#fda085); height:16px; border-radius:4px"></div>
              </div>
              <span style="width:30px; text-align:right; font-size:0.85rem; color:#f6d365">{count}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Honeypot summary
        st.markdown("#### Honeypot Detection Summary")
        hp_flagged = [r for r in rows if r["honeypot"]]
        hp_clean = [r for r in rows if not r["honeypot"]]
        hpc1, hpc2 = st.columns(2)
        with hpc1:
            st.markdown(f"""
            <div class="metric-card-green">
              <div class="val">{len(hp_clean)}</div>
              <div class="lbl">Clean Candidates</div>
            </div>
            """, unsafe_allow_html=True)
        with hpc2:
            st.markdown(f"""
            <div class="metric-card-amber">
              <div class="val">{len(hp_flagged)}</div>
              <div class="lbl">Honeypot Flagged</div>
            </div>
            """, unsafe_allow_html=True)

        if hp_flagged:
            st.markdown("**Flagged candidates:**")
            for r in hp_flagged:
                st.markdown(f"- ⚠️ #{r['rank']} **{r['candidate_id']}** · {r['title']} at {r['company']} · confidence: {r.get('honeypot_confidence', 0):.2f}")


with tab5:
    st.markdown("""
## System Architecture

### Pipeline Overview
```
candidates.jsonl (100K profiles, ~465 MB)
        │
        ▼ Stage 0: Bootstrap (0.05s)
   Aho-Corasick automaton from 80+ production NLP phrases
   (falls back to compiled regex if pyahocorasick unavailable)

        ▼ Stage 1: Ingestion (17s)
   Stream-parse → typed Candidate dataclasses, robust error handling

        ▼ Stage 2: Early Elimination (1s)
   YOE < 2 | zero tech skills | HP01/02/05/06 ≥ 0.6 confidence
   → 30,927 survivors (69,073 eliminated)

        ▼ Stage 3: Feature Extraction (21s total)
   Behavioral: availability × engagement × credibility
   Tabular: exp_fit, company_type, location, title_relevance, edu_bonus
   Semantic: career_nlp (w/ temporal decay), skill_depth, domain

        ▼ Stage 4: Honeypot Full Pass (0.3s)
   HP03 overlapping tenures | HP04 edu/career | HP07 perfect+abandoned
   HP08 all-assessments-perfect | HP09 instant-response | HP10 fixture names

        ▼ Stage 5: Scoring (0.1s)
   final = technical × title_relevance × behavioral_mult + edu_bonus

        ▼ Stage 6–7: Output (0.1s)
   Sort → guardrails → normalize → tie-break → per-candidate reasoning
```

### Anti-Gaming Strategy

> **The JD explicitly warns:** *"The right answer is NOT find candidates whose skills section contains the most AI keywords. That's a trap we've explicitly built into the dataset."*

Our multi-layered defense:

| Defense Layer | What It Catches | How It Works |
|---|---|---|
| **Title Relevance Multiplier** | Keyword stuffers with wrong titles | Non-ML titles → 0.25× score regardless of skills |
| **Skill Stuffing Penalty** | Candidates listing 40+ skills | Progressive penalty above threshold |
| **Career NLP with Temporal Decay** | No production evidence | Must have deployment phrases in career text |
| **All-Services Career Cap** | Consulting-only background | Entire career at TCS/Wipro/etc → capped at 0.30 |
| **Honeypot Detection** | Impossible profiles | 10 rules catch salary inversions, impossible tenures, fixture companies |

### Skill Tier Taxonomy
| Tier | Weight | Examples |
|------|--------|---------|
| A | 3.0 | FAISS, Pinecone, Weaviate, Qdrant, OpenSearch, Learning to Rank |
| B | 2.5 | PyTorch, LLM Fine-tuning, Sentence Transformers, BM25 |
| C | 2.0 | NLP, ML, Deep Learning, Information Retrieval |
| D | 1.5 | Python, Docker, SQL, AWS |
| E | 0.5 | Communication, Leadership |
| NEG | -2.0 | OpenCV, YOLO, Speech Recognition, Robotics |

### Honeypot Detection (10 Rules)
| Rule | Signal | Confidence |
|------|--------|-----------|
| HP01 | salary_min > salary_max | 0.80 |
| HP02 | YOE > career span + 0.1 | 0.70 |
| HP03 | Overlapping tenures > 90 days | 0.60 |
| HP04 | Job start before education start | 0.30 |
| HP05 | YOE > years since graduation | 0.80 |
| HP06 | Entry duration > calendar span + 2 months | 0.90 |
| HP07 | Perfect completeness + abandoned profile | 0.40 |
| HP08 | All assessments ≥ 90 | 0.50 |
| HP09 | Avg response time < 0.1 hours | 0.40 |
| HP10 | Fixture company names (Dunder Mifflin, Initech, etc.) | 0.10 |

### Compute Constraints Compliance

| Constraint | Limit | Actual |
|-----------|-------|--------|
| Runtime | ≤ 5 min | ~27s ✅ |
| Memory | ≤ 16 GB | ~2-3 GB ✅ |
| Compute | CPU only | Pure Python ✅ |
| Network | None | No API calls ✅ |
| GPU | None | Not used ✅ |
""")
