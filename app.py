import json
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. PAGE SETUP & STYLING
# ==========================================
st.set_page_config(
    page_title="CS2 Prop Scanner Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #1e222d;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #2e3545;
    }
    .warning-box {
        background-color: #3b2219;
        border: 1px solid #d97706;
        padding: 12px;
        border-radius: 8px;
        color: #fcd34d;
        margin-bottom: 15px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🎯 CS2 Full-Board Prop Scanner")
st.caption(
    "Quantitative engine evaluating CS2 props using Scorpio projections, overtime risk adjustments, and strict 80%+ consistency filters."
)


# ==========================================
# 2. CORE SCANNER ENGINE WITH ADVANCED RULES
# ==========================================
def scan_cs2_props(
    props_df: pd.DataFrame, min_gap: float = 2.5, min_hit_rate: float = 0.80
) -> pd.DataFrame:
    """Evaluates an entire slate of CS2 props."""
    df = props_df.copy()

    # Normalize column names
    if "stat_per_round" not in df.columns and "kpr_l15" in df.columns:
        df["stat_per_round"] = df["kpr_l15"]

    # Fill default optional columns if missing
    if "adr" not in df.columns:
        df["adr"] = 70.0
    if "assist_rate" not in df.columns:
        df["assist_rate"] = 0.15
    if "first_kills_per_round" not in df.columns:
        df["first_kills_per_round"] = 0.10
    if "match_rating_diff" not in df.columns:
        df["match_rating_diff"] = 0.15

    # --- RULE 1: DATA SCALE SANITY GUARD ---
    def check_log_scale(row):
        logs = row["last_10_logs"]
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except Exception:
                return False

        logs = np.array(logs)
        if len(logs) == 0:
            return False

        is_2map = "1-2" in str(row["prop_type"]) or "Maps 1-2" in str(
            row["prop_type"]
        )
        if is_2map and np.mean(logs) < (row["line"] * 0.68):
            return False
        return True

    df["valid_scale"] = df.apply(check_log_scale, axis=1)

    # --- RULE 2: OVERTIME & MATCH INTENSITY MULTIPLIER ---
    def calc_round_multiplier(row):
        base_rounds = row["expected_rounds"]
        if row["match_rating_diff"] <= 0.16 and "1-2" in str(
            row["prop_type"]
        ):
            return base_rounds * 1.06
        return base_rounds

    df["adj_expected_rounds"] = df.apply(calc_round_multiplier, axis=1)

    # --- RULE 3: PLAYER ROLE MODIFIERS ---
    def calc_role_modifier(row):
        mod = 1.0
        if row["assist_rate"] > 0.25 or row["adr"] < 60.0:
            mod -= 0.08
        if row["first_kills_per_round"] >= 0.15:
            mod += 0.05
        return mod

    df["role_modifier"] = df.apply(calc_role_modifier, axis=1)

    # --- PROJECTION ENGINE ---
    df["projected_stat"] = (
        df["stat_per_round"]
        * df["adj_expected_rounds"]
        * df["map_factor"]
        * df["opponent_adj"]
        * df["role_modifier"]
    )
    df["proj_gap"] = (df["projected_stat"] - df["line"]).round(2)
    df["projected_stat"] = df["projected_stat"].round(2)

    # --- CONSISTENCY AUDIT ---
    def audit_logs(row):
        logs = row["last_10_logs"]
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except Exception:
                logs = []

        logs = np.array(logs)
        if len(logs) == 0:
            return pd.Series([0.0, 0.0])

        over_rate = np.sum(logs > row["line"]) / len(logs)
        under_rate = np.sum(logs < row["line"]) / len(logs)
        return pd.Series([over_rate, under_rate])

    df[["over_hit_rate", "under_hit_rate"]] = df.apply(audit_logs, axis=1)

    # --- STRICT BINARY FILTERING ---
    qualify_over = (
        (df["proj_gap"] >= min_gap)
        & (df["over_hit_rate"] >= min_hit_rate)
        & df["valid_scale"]
    )
    qualify_under = (
        (df["proj_gap"] <= -min_gap)
        & (df["under_hit_rate"] >= min_hit_rate)
        & df["valid_scale"]
    )

    conditions = [
        ~df["valid_scale"],
        qualify_over,
        qualify_under,
    ]
    choices = [
        "PASS (DATA MISMATCH)",
        "QUALIFIED OVER 🔒",
        "QUALIFIED UNDER 🔒",
    ]
    df["recommendation"] = np.select(
        conditions, choices, default="PASS (NO EDGE)"
    )

    return df


# ==========================================
# 3. SAME-MATCH CORRELATION CHECKER
# ==========================================
def audit_correlation(qualified_df: pd.DataFrame):
    warnings = []
    if qualified_df.empty:
        return warnings

    matches = qualified_df["match_id"].unique()
    for match in matches:
        sub = qualified_df[qualified_df["match_id"] == match]
        has_overs = (sub["recommendation"] == "QUALIFIED OVER 🔒").any()
        has_unders = (sub["recommendation"] == "QUALIFIED UNDER 🔒").any()

        if has_overs and has_unders:
            players_over = sub[sub["recommendation"] == "QUALIFIED OVER 🔒"][
                "player"
            ].tolist()
            players_under = sub[sub["recommendation"] == "QUALIFIED UNDER 🔒"][
                "player"
            ].tolist()
            warnings.append(
                f"⚠️ **Negative Correlation Warning in {match}**: You have Overs on ({', '.join(players_over)}) "
                f"and Unders on ({', '.join(players_under)}). Overtime or extended rounds will force the Unders to lose."
            )
    return warnings


# ==========================================
# 4. SIDEBAR CONTROLS & DATA SOURCES
# ==========================================
st.sidebar.header("⚙️ Scanner Settings")

gap_threshold = st.sidebar.slider(
    "Min Projection Gap (+/- Stat)", 1.0, 5.0, 2.5, 0.5
)
hit_rate_threshold = st.sidebar.slider(
    "Min Consistency Hit Rate (%)", 0.60, 0.90, 0.80, 0.05
)

st.sidebar.markdown("---")
st.sidebar.header("📥 Board Data Source")

data_source = st.sidebar.radio(
    "Select Ingestion Method:",
    [
        "Load MOUZ vs FURIA & Full Slate",
        "Upload CSV Batch File",
        "Fetch Live API / Paste JSON",
    ],
    index=0,
)

board_df = None

if data_source == "Load MOUZ vs FURIA & Full Slate":
    demo_data = [
        {
            "match_id": "MOUZ_FURIA",
            "player": "KSCERATO",
            "team": "FURIA",
            "opponent": "MOUZ",
            "prop_type": "Maps 1-2 Kills",
            "line": 31.5,
            "stat_per_round": 0.82,
            "expected_rounds": 44.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "adr": 97.5,
            "assist_rate": 0.12,
            "first_kills_per_round": 0.11,
            "match_rating_diff": 0.16,
            "last_10_logs": [35, 42, 33, 38, 36, 40, 32, 45, 34, 39],
        },
        {
            "match_id": "MOUZ_FURIA",
            "player": "molodoy",
            "team": "FURIA",
            "opponent": "MOUZ",
            "prop_type": "Maps 1-2 Kills",
            "line": 32.5,
            "stat_per_round": 0.68,
            "expected_rounds": 44.0,
            "map_factor": 1.00,
            "opponent_adj": 0.98,
            "adr": 69.9,
            "assist_rate": 0.14,
            "first_kills_per_round": 0.10,
            "match_rating_diff": 0.16,
            "last_10_logs": [28, 31, 29, 30, 27, 32, 30, 28, 31, 29],
        },
        {
            "match_id": "MOUZ_FURIA",
            "player": "PR",
            "team": "MOUZ",
            "opponent": "FURIA",
            "prop_type": "Maps 1-2 Kills",
            "line": 27.5,
            "stat_per_round": 0.58,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "adr": 55.7,
            "assist_rate": 0.28,
            "first_kills_per_round": 0.08,
            "match_rating_diff": 0.16,
            "last_10_logs": [22, 25, 23, 26, 21, 24, 25, 23, 20, 24],
        },
        {
            "match_id": "MOUZ_FURIA",
            "player": "Spinx",
            "team": "MOUZ",
            "opponent": "FURIA",
            "prop_type": "Maps 1-2 Headshots",
            "line": 16.5,
            "stat_per_round": 0.45,
            "expected_rounds": 44.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "adr": 73.5,
            "assist_rate": 0.15,
            "first_kills_per_round": 0.12,
            "match_rating_diff": 0.16,
            "last_10_logs": [19, 21, 18, 22, 17, 20, 19, 23, 18, 21],
        },
        {
            "match_id": "MOUZ_FURIA",
            "player": "torzsi",
            "team": "MOUZ",
            "opponent": "FURIA",
            "prop_type": "Maps 1-2 Kills",
            "line": 30.5,
            "stat_per_round": 0.62,
            "expected_rounds": 44.0,
            "map_factor": 0.98,
            "opponent_adj": 0.98,
            "adr": 58.9,
            "assist_rate": 0.22,
            "first_kills_per_round": 0.09,
            "match_rating_diff": 0.16,
            "last_10_logs": [26, 28, 25, 29, 27, 28, 24, 29, 26, 28],
        },
        {
            "match_id": "MOUZ_FURIA",
            "player": "xertioN",
            "team": "MOUZ",
            "opponent": "FURIA",
            "prop_type": "Maps 1-2 Kills",
            "line": 31.5,
            "stat_per_round": 0.74,
            "expected_rounds": 44.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "adr": 68.4,
            "assist_rate": 0.12,
            "first_kills_per_round": 0.18,
            "match_rating_diff": 0.16,
            "last_10_logs": [33, 36, 32, 38, 35, 34, 37, 32, 36, 39],
        },
    ]
    board_df = pd.DataFrame(demo_data)

elif data_source == "Upload CSV Batch File":
    uploaded_file = st.sidebar.file_uploader(
        "Upload CS2 Slate CSV", type=["csv"]
    )
    if uploaded_file is not None:
        try:
            board_df = pd.read_csv(uploaded_file)
            st.sidebar.success(
                f"Loaded {len(board_df)} props from uploaded CSV!"
            )
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")

elif data_source == "Fetch Live API / Paste JSON":
    api_url = st.sidebar.text_input("API Endpoint URL (Optional)", value="")
    json_text = st.sidebar.text_area("Or Paste Raw JSON Payload:", height=120)

    if st.sidebar.button("Fetch & Parse Slate"):
        try:
            if api_url.strip():
                resp = requests.get(
                    api_url.strip(),
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                data = resp.json()
            else:
                data = json.loads(json_text)

            if isinstance(data, dict) and "data" in data:
                data = data["data"]

            board_df = pd.DataFrame(data)
            st.sidebar.success(f"Parsed {len(board_df)} props successfully!")
        except Exception as e:
            st.sidebar.error(f"JSON/API parsing error: {e}")


# ==========================================
# 5. DASHBOARD DISPLAY & CORRELATION AUDIT
# ==========================================
if board_df is not None and not board_df.empty:

    processed_df = scan_cs2_props(
        board_df, min_gap=gap_threshold, min_hit_rate=hit_rate_threshold
    )

    qualified_df = processed_df[
        processed_df["recommendation"].str.contains("QUALIFIED")
    ]
    overs_df = processed_df[
        processed_df["recommendation"] == "QUALIFIED OVER 🔒"
    ]
    unders_df = processed_df[
        processed_df["recommendation"] == "QUALIFIED UNDER 🔒"
    ]

    # Metrics Overview
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned Board Props", len(processed_df))
    c2.metric("Qualified Locks 🔒", len(qualified_df))
    c3.metric("Over Locks", len(overs_df))
    c4.metric("Under Locks", len(unders_df))

    st.markdown("---")

    # Audit Same-Match Correlation Warnings
    correlation_warnings = audit_correlation(qualified_df)
    if correlation_warnings:
        for warn in correlation_warnings:
            st.markdown(
                f'<div class="warning-box">{warn}</div>', unsafe_allow_html=True
            )

    tab1, tab2 = st.tabs(["🔒 Qualified Locks Only", "📋 Complete Slate Audit"])

    with tab1:
        st.subheader("High-EV Actionable Picks")
        if qualified_df.empty:
            st.warning(
                "No props on this slate passed both the projection gap and 80%+ consistency rules."
            )
        else:
            display_cols = [
                "player",
                "team",
                "opponent",
                "prop_type",
                "line",
                "projected_stat",
                "proj_gap",
                "over_hit_rate",
                "under_hit_rate",
                "recommendation",
            ]

            st.dataframe(
                qualified_df[display_cols].style.format({
                    "line": "{:.1f}",
                    "projected_stat": "{:.2f}",
                    "proj_gap": "{:+.2f}",
                    "over_hit_rate": "{:.0%}",
                    "under_hit_rate": "{:.0%}",
                }),
                use_container_width=True,
            )

            csv_export = (
                qualified_df[display_cols].to_csv(index=False).encode("utf-8")
            )
            st.download_button(
                label="📥 Download Qualified Locks CSV",
                data=csv_export,
                file_name="cs2_qualified_locks.csv",
                mime="text/csv",
            )

    with tab2:
        st.subheader("Full Slate Audit Trail")
        st.dataframe(
            processed_df.style.format({
                "line": "{:.1f}",
                "projected_stat": "{:.2f}",
                "proj_gap": "{:+.2f}",
                "over_hit_rate": "{:.0%}",
                "under_hit_rate": "{:.0%}",
            }),
            use_container_width=True,
        )
else:
    st.info(
        "👈 Open the sidebar to select a data source or upload custom CSVs."
    )
