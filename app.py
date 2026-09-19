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
    initial_sidebar_state="collapsed",  # Automatically collapses sidebar on mobile so dashboard displays instantly
)

# Custom CSS styling for metric cards and tags
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
    "Quantitative engine evaluating CS2 props using Scorpio projections and strict Capricorn 80%+ consistency filters."
)


# ==========================================
# 2. CORE SCANNER ENGINE LOGIC
# ==========================================
def scan_cs2_props(
    props_df: pd.DataFrame, min_gap: float = 2.5, min_hit_rate: float = 0.80
) -> pd.DataFrame:
    """Evaluates an entire slate of CS2 props:

    1. Projects total kills based on KPR, Expected Rounds, Map Factor, and Opponent Adjustments.
    2. Calculates directional hit rates over the last 10 logs.
    3. Requires BOTH a projection gap (>= min_gap) AND high consistency (>= min_hit_rate).
    """
    df = props_df.copy()

    # --- STEP 1: SCORPIO PROJECTION ENGINE ---
    # Formula: (KPR * Expected Rounds) * Map Multiplier * Opponent Adjustment
    df["projected_kills"] = (
        df["kpr_l15"]
        * df["expected_rounds"]
        * df["map_factor"]
        * df["opponent_adj"]
    )
    df["proj_gap"] = (df["projected_kills"] - df["line"]).round(2)
    df["projected_kills"] = df["projected_kills"].round(2)

    # --- STEP 2: CAPRICORN CONSISTENCY AUDIT ---
    def audit_logs(row):
        logs = row["last_10_logs"]

        # Parse stringified lists or comma-separated numbers if uploaded via CSV/JSON
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
    # Must meet BOTH the gap threshold AND the 80%+ consistency rule in one direction
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
    "Min Projection Gap (+/- Kills)", 1.0, 5.0, 2.5, 0.5
)
hit_rate_threshold = st.sidebar.slider(
    "Min Consistency Hit Rate (%)", 0.60, 0.90, 0.80, 0.05
)

st.sidebar.markdown("---")
st.sidebar.header("📥 Board Data Source")

# Default index=0 loads Demo Board immediately so screen is never blank
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

# --- SOURCE 1: DEMO BOARD (DEFAULT) ---
if data_source == "Load Sample Demo Board":
    demo_data = [
        {
            "player": "b1t",
            "team": "NAVI",
            "opponent": "FaZe",
            "prop_type": "Maps 1-2 Kills",
            "line": 32.5,
            "kpr_l15": 0.74,
            "expected_rounds": 46.0,
            "map_factor": 1.05,
            "opponent_adj": 1.00,
            "last_10_logs": [35, 38, 33, 36, 29, 34, 37, 33, 31, 35],
        },
        {
            "player": "apEX",
            "team": "Vitality",
            "opponent": "G2",
            "prop_type": "Map 1 Kills",
            "line": 14.5,
            "kpr_l15": 0.52,
            "expected_rounds": 19.5,
            "map_factor": 0.95,
            "opponent_adj": 0.90,
            "last_10_logs": [11, 12, 10, 13, 16, 12, 9, 11, 14, 10],
        },
        {
            "player": "m0NESY",
            "team": "G2",
            "opponent": "Vitality",
            "prop_type": "Map 1 Kills",
            "line": 18.5,
            "kpr_l15": 0.85,
            "expected_rounds": 22.0,
            "map_factor": 1.00,
            "opponent_adj": 1.00,
            "last_10_logs": [19, 14, 22, 12, 20, 15, 21, 13, 18, 17],
        },
        {
            "player": "ZywOo",
            "team": "Vitality",
            "opponent": "MOUZ",
            "prop_type": "Maps 1-2 Kills",
            "line": 36.5,
            "kpr_l15": 0.88,
            "expected_rounds": 45.0,
            "map_factor": 1.08,
            "opponent_adj": 0.98,
            "last_10_logs": [38, 41, 37, 39, 35, 40, 38, 37, 42, 39],
        },
        {
            "player": "frozen",
            "team": "FaZe",
            "opponent": "NAVI",
            "prop_type": "Map 1 Kills",
            "line": 16.5,
            "kpr_l15": 0.68,
            "expected_rounds": 22.5,
            "map_factor": 0.92,
            "opponent_adj": 0.95,
            "last_10_logs": [14, 13, 15, 12, 18, 14, 15, 13, 16, 12],
        },
        {
            "player": "Lake",
            "team": "M80",
            "opponent": "3DMAX",
            "prop_type": "Maps 1-2 Kills",
            "line": 31.5,
            "kpr_l15": 0.78,
            "expected_rounds": 45.0,
            "map_factor": 1.02,
            "opponent_adj": 1.00,
            "last_10_logs": [34, 38, 32, 36, 29, 37, 35, 33, 31, 36],
        },
        {
            "player": "Graviti",
            "team": "3DMAX",
            "opponent": "M80",
            "prop_type": "Maps 1-2 Kills",
            "line": 26.0,
            "kpr_l15": 0.51,
            "expected_rounds": 44.0,
            "map_factor": 0.98,
            "opponent_adj": 1.00,
            "last_10_logs": [21, 24, 25, 27, 20, 22, 23, 28, 19, 22],
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

    # Execute full board scanner calculations
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
                "projected_kills",
                "proj_gap",
                "over_hit_rate",
                "under_hit_rate",
                "recommendation",
            ]

            # Interactive formatted table
            st.dataframe(
                qualified_df[display_cols].style.format({
                    "line": "{:.1f}",
                    "projected_kills": "{:.2f}",
                    "proj_gap": "{:+.2f}",
                    "over_hit_rate": "{:.0%}",
                    "under_hit_rate": "{:.0%}",
                }),
                use_container_width=True,
            )

            # Export ready-to-bet CSV
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
                "projected_kills": "{:.2f}",
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
