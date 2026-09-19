import json
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. PAGE SETUP (MOBILE-OPTIMIZED)
# ==========================================
st.set_page_config(
    page_title="CS2 Prop Scanner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",  # Automatically collapses sidebar on mobile
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
    .css-1r6slb0 {
        padding: 1rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🎯 CS2 Full-Board Prop Scanner")
st.caption(
    "Quantitative engine evaluating CS2 props using Scorpio projections and strict 80%+ consistency filters."
)


# ==========================================
# 2. CORE SCANNER ENGINE LOGIC
# ==========================================
def scan_cs2_props(
    props_df: pd.DataFrame, min_gap: float = 2.5, min_hit_rate: float = 0.80
) -> pd.DataFrame:
    """Evaluates an entire slate of CS2 props (Kills & Headshots):

    1. Projects expected value based on Stat Per Round (KPR/HPR), Expected Rounds, Map Multiplier, and Opponent Adjustments.
    2. Calculates directional hit rates over the last 10 logs.
    3. Requires BOTH a projection gap (>= min_gap) AND high consistency (>= min_hit_rate).
    """
    df = props_df.copy()

    # Allow fallback for legacy 'kpr_l15' column name if present
    if "stat_per_round" not in df.columns and "kpr_l15" in df.columns:
        df["stat_per_round"] = df["kpr_l15"]

    # --- STEP 1: PROJECTION ENGINE ---
    df["projected_stat"] = (
        df["stat_per_round"]
        * df["expected_rounds"]
        * df["map_factor"]
        * df["opponent_adj"]
    )
    df["proj_gap"] = (df["projected_stat"] - df["line"]).round(2)
    df["projected_stat"] = df["projected_stat"].round(2)

    # --- STEP 2: CONSISTENCY AUDIT ---
    def audit_logs(row):
        logs = row["last_10_logs"]

        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except Exception:
                logs = [
                    float(x.strip())
                    for x in logs.replace("[", "")
                    .replace("]", "")
                    .split(",")
                    if x.strip()
                ]

        logs = np.array(logs)
        if len(logs) == 0:
            return pd.Series([0.0, 0.0])

        over_rate = np.sum(logs > row["line"]) / len(logs)
        under_rate = np.sum(logs < row["line"]) / len(logs)
        return pd.Series([over_rate, under_rate])

    df[["over_hit_rate", "under_hit_rate"]] = df.apply(audit_logs, axis=1)

    # --- STEP 3: STRICT BINARY FILTERING ---
    qualify_over = (df["proj_gap"] >= min_gap) & (
        df["over_hit_rate"] >= min_hit_rate
    )
    qualify_under = (df["proj_gap"] <= -min_gap) & (
        df["under_hit_rate"] >= min_hit_rate
    )

    conditions = [qualify_over, qualify_under]
    choices = ["QUALIFIED OVER 🔒", "QUALIFIED UNDER 🔒"]
    df["recommendation"] = np.select(
        conditions, choices, default="PASS (NO EDGE)"
    )

    return df


# ==========================================
# 3. SIDEBAR CONTROLS & INGESTION
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
        "Load Sample Demo Board",
        "Upload CSV Batch File",
        "Fetch Live API / Paste JSON",
    ],
    index=0,
)

board_df = None

# --- SOURCE 1: FULL DEMO BOARD (ALL PROPS FROM SLATE) ---
if data_source == "Load Sample Demo Board":
    demo_data = [
        # ex-Zero Tenacity vs PCIFIC
        {
            "player": "Dragon",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Kills",
            "line": 30.5,
            "stat_per_round": 0.76,
            "expected_rounds": 45.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "last_10_logs": [34, 38, 32, 35, 31, 36, 33, 37, 32, 36],
        },
        {
            "player": "Dragon",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Headshots",
            "line": 15.5,
            "stat_per_round": 0.42,
            "expected_rounds": 45.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "last_10_logs": [18, 20, 16, 19, 17, 21, 18, 19, 16, 20],
        },
        {
            "player": "Kind0",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Kills",
            "line": 28.5,
            "stat_per_round": 0.70,
            "expected_rounds": 44.0,
            "map_factor": 1.00,
            "opponent_adj": 1.00,
            "last_10_logs": [30, 29, 31, 27, 32, 30, 29, 33, 28, 31],
        },
        {
            "player": "Kind0",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Headshots",
            "line": 13.5,
            "stat_per_round": 0.35,
            "expected_rounds": 44.0,
            "map_factor": 1.00,
            "opponent_adj": 1.00,
            "last_10_logs": [15, 14, 16, 12, 15, 14, 17, 13, 15, 16],
        },
        {
            "player": "brutmonster",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Kills",
            "line": 29.5,
            "stat_per_round": 0.71,
            "expected_rounds": 44.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "last_10_logs": [31, 33, 30, 32, 28, 34, 31, 30, 32, 33],
        },
        {
            "player": "brutmonster",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Headshots",
            "line": 10.5,
            "stat_per_round": 0.20,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 1.00,
            "last_10_logs": [7, 8, 9, 10, 6, 8, 9, 11, 7, 8],
        },
        {
            "player": "Cjoffo",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Kills",
            "line": 30.5,
            "stat_per_round": 0.75,
            "expected_rounds": 45.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "last_10_logs": [36, 32, 38, 31, 34, 37, 33, 35, 29, 36],
        },
        {
            "player": "Cjoffo",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Headshots",
            "line": 18.5,
            "stat_per_round": 0.44,
            "expected_rounds": 45.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "last_10_logs": [21, 19, 22, 20, 19, 23, 18, 21, 20, 22],
        },
        {
            "player": "emi",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Kills",
            "line": 25.0,
            "stat_per_round": 0.48,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [18, 20, 22, 19, 23, 21, 24, 17, 19, 20],
        },
        {
            "player": "emi",
            "team": "ex-Zero Tenacity",
            "opponent": "PCIFIC",
            "prop_type": "Maps 1-2 Headshots",
            "line": 12.5,
            "stat_per_round": 0.22,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [8, 9, 10, 7, 11, 9, 12, 8, 10, 9],
        },
        # PCIFIC vs ex-Zero Tenacity
        {
            "player": "jresy",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Kills",
            "line": 27.5,
            "stat_per_round": 0.72,
            "expected_rounds": 45.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "last_10_logs": [31, 29, 34, 30, 28, 32, 35, 29, 33, 31],
        },
        {
            "player": "jresy",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Headshots",
            "line": 13.5,
            "stat_per_round": 0.38,
            "expected_rounds": 45.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "last_10_logs": [16, 15, 18, 14, 17, 15, 19, 16, 14, 17],
        },
        {
            "player": "l0gicman",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Kills",
            "line": 23.5,
            "stat_per_round": 0.44,
            "expected_rounds": 43.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [17, 19, 18, 20, 16, 21, 18, 19, 17, 22],
        },
        {
            "player": "l0gicman",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Headshots",
            "line": 16.0,
            "stat_per_round": 0.25,
            "expected_rounds": 43.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [9, 11, 10, 12, 8, 13, 10, 11, 9, 12],
        },
        {
            "player": "lugseN",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Kills",
            "line": 28.0,
            "stat_per_round": 0.72,
            "expected_rounds": 44.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "last_10_logs": [31, 30, 33, 29, 34, 32, 30, 35, 29, 32],
        },
        {
            "player": "lugseN",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Headshots",
            "line": 9.0,
            "stat_per_round": 0.18,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [6, 5, 7, 8, 6, 7, 5, 8, 6, 7],
        },
        {
            "player": "oyesil",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Kills",
            "line": 23.5,
            "stat_per_round": 0.45,
            "expected_rounds": 43.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [18, 20, 17, 19, 21, 18, 16, 20, 19, 22],
        },
        {
            "player": "oyesil",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Headshots",
            "line": 15.0,
            "stat_per_round": 0.24,
            "expected_rounds": 43.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [8, 10, 9, 11, 12, 9, 10, 8, 11, 10],
        },
        {
            "player": "scolleN",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Kills",
            "line": 26.5,
            "stat_per_round": 0.52,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [21, 22, 19, 23, 20, 24, 18, 22, 21, 25],
        },
        {
            "player": "scolleN",
            "team": "PCIFIC",
            "opponent": "ex-Zero Tenacity",
            "prop_type": "Maps 1-2 Headshots",
            "line": 16.0,
            "stat_per_round": 0.28,
            "expected_rounds": 44.0,
            "map_factor": 0.95,
            "opponent_adj": 0.95,
            "last_10_logs": [10, 12, 11, 13, 9, 14, 11, 12, 10, 13],
        },
    ]
    board_df = pd.DataFrame(demo_data)

# --- SOURCE 2: CSV UPLOAD ---
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
            st.sidebar.error(f"Error reading CSV file: {e}")

# --- SOURCE 3: LIVE API / JSON ---
elif data_source == "Fetch Live API / Paste JSON":
    api_url = st.sidebar.text_input("API Endpoint URL (Optional)", value="")
    json_text = st.sidebar.text_area("Or Paste Raw JSON Payload:", height=120)

    if st.sidebar.button("Fetch & Parse Slate"):
        try:
            if api_url.strip():
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(
                    api_url.strip(), headers=headers, timeout=10
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
# 4. MAIN DASHBOARD RENDER
# ==========================================
if board_df is not None and not board_df.empty:

    processed_df = scan_cs2_props(
        board_df, min_gap=gap_threshold, min_hit_rate=hit_rate_threshold
    )

    qualified_df = processed_df[
        processed_df["recommendation"] != "PASS (NO EDGE)"
    ]
    overs_df = processed_df[
        processed_df["recommendation"] == "QUALIFIED OVER 🔒"
    ]
    unders_df = processed_df[
        processed_df["recommendation"] == "QUALIFIED UNDER 🔒"
    ]

    # Metric Header Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned Board Props", len(processed_df))
    c2.metric("Qualified Locks 🔒", len(qualified_df))
    c3.metric("Over Locks", len(overs_df))
    c4.metric("Under Locks", len(unders_df))

    st.markdown("---")

    # Tab views
    tab1, tab2 = st.tabs(["🔒 Qualified Locks Only", "📋 Complete Board Audit"])

    with tab1:
        st.subheader("High-EV Actionable Locks")
        if qualified_df.empty:
            st.warning(
                "No props on this slate passed both the strict projection gap and 80%+ consistency rules."
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
        st.subheader("Complete Board Audit Trail")
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
        "👈 Sidebar menu auto-closed on mobile. Tap the icon in the top left to open controls or upload custom CSVs."
    )
