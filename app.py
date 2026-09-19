import json
import pandas as pd
import numpy as np
import requests
import streamlit as st

# ==========================================
# PAGE SETUP & CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CS2 Full-Board Prop Scanner",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 CS2 Esports Full-Board Prop Scanner")
st.caption("Quantitative edge scanner powered by Scorpio projection models and Capricorn consistency filters.")


# ==========================================
# CORE SCANNER ENGINE LOGIC
# ==========================================
def scan_cs2_props(props_df: pd.DataFrame, min_gap: float = 2.5, min_hit_rate: float = 0.80) -> pd.DataFrame:
    """
    Evaluates an entire slate of CS2 props using strict quantitative filters:
    1. Projects total kills based on KPR, Expected Rounds, Map Factor, and Opponent Adjustments.
    2. Calculates directional hit rates over the last 10 logs.
    3. Requires BOTH a projection gap (>= min_gap) AND high consistency (>= min_hit_rate).
    """
    df = props_df.copy()
    
    # 1. Scorpio Projection Engine
    df['projected_kills'] = (
        df['kpr_l15'] * df['expected_rounds'] * df['map_factor'] * df['opponent_adj']
    )
    df['proj_gap'] = (df['projected_kills'] - df['line']).round(2)
    df['projected_kills'] = df['projected_kills'].round(2)

    # 2. Capricorn Consistency Audit
    def audit_logs(row):
        logs = row['last_10_logs']
        if isinstance(logs, str):
            try:
                logs = json.loads(logs)
            except Exception:
                logs = [float(x.strip()) for x in logs.split(',') if x.strip()]
        
        logs = np.array(logs)
        if len(logs) == 0:
            return pd.Series([0.0, 0.0])
            
        over_rate = np.sum(logs > row['line']) / len(logs)
        under_rate = np.sum(logs < row['line']) / len(logs)
        return pd.Series([over_rate, under_rate])

    df[['over_hit_rate', 'under_hit_rate']] = df.apply(audit_logs, axis=1)

    # 3. Binary Selection Filter (Consistently OVER or Consistently UNDER)
    qualify_over = (df['proj_gap'] >= min_gap) & (df['over_hit_rate'] >= min_hit_rate)
    qualify_under = (df['proj_gap'] <= -min_gap) & (df['under_hit_rate'] >= min_hit_rate)

    conditions = [qualify_over, qualify_under]
    choices = ['QUALIFIED OVER 🔒', 'QUALIFIED UNDER 🔒']
    df['recommendation'] = np.select(conditions, choices, default='PASS (NO EDGE)')

    return df


# ==========================================
# SIDEBAR: DATA INGESTION & CONTROLS
# ==========================================
st.sidebar.header("⚙️ Scanner Controls")

# Parameter Sliders
gap_threshold = st.sidebar.slider("Min Projection Gap (+/- Kills)", 1.0, 5.0, 2.5, 0.5)
hit_rate_threshold = st.sidebar.slider("Min Consistency Hit Rate (%)", 0.60, 0.90, 0.80, 0.05)

st.sidebar.markdown("---")
st.sidebar.header("📥 Full Slate Data Source")

data_source = st.sidebar.radio(
    "Select Ingestion Method:",
    ["Upload CSV Batch File", "Fetch Live API / Paste JSON", "Load Sample Demo Board"]
)

board_df = None

# --- SOURCE 1: CSV UPLOAD ---
if data_source == "Upload CSV Batch File":
    uploaded_file = st.sidebar.file_uploader("Upload CS2 Slate CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            board_df = raw_df
            st.sidebar.success(f"Successfully loaded {len(board_df)} props from CSV!")
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")

# --- SOURCE 2: LIVE API / JSON ---
elif data_source == "Fetch Live API / Paste JSON":
    api_url = st.sidebar.text_input("API Endpoint URL (Optional)", value="")
    json_text = st.sidebar.text_area("Or Paste Raw JSON Payload:", height=150)
    
    if st.sidebar.button("Fetch & Parse Slate"):
        try:
            if api_url.strip():
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(api_url.strip(), headers=headers, timeout=10)
                data = resp.json()
            else:
                data = json.loads(json_text)
            
            # Extract nested board list if necessary
            if isinstance(data, dict) and 'data' in data:
                data = data['data']
                
            board_df = pd.DataFrame(data)
            st.sidebar.success(f"Parsed {len(board_df)} props from JSON!")
        except Exception as e:
            st.sidebar.error(f"Failed to parse payload: {e}")

# --- SOURCE 3: DEMO BOARD ---
else:
    demo_data = [
        {"player": "b1t", "team": "NAVI", "opponent": "FaZe", "prop_type": "Maps 1-2 Kills", "line": 32.5, "kpr_l15": 0.74, "expected_rounds": 46.0, "map_factor": 1.05, "opponent_adj": 1.00, "last_10_logs": [35, 38, 33, 36, 29, 34, 37, 33, 31, 35]},
        {"player": "apEX", "team": "Vitality", "opponent": "G2", "prop_type": "Map 1 Kills", "line": 14.5, "kpr_l15": 0.52, "expected_rounds": 19.5, "map_factor": 0.95, "opponent_adj": 0.90, "last_10_logs": [11, 12, 10, 13, 16, 12, 9, 11, 14, 10]},
        {"player": "m0NESY", "team": "G2", "opponent": "Vitality", "prop_type": "Map 1 Kills", "line": 18.5, "kpr_l15": 0.85, "expected_rounds": 22.0, "map_factor": 1.00, "opponent_adj": 1.00, "last_10_logs": [19, 14, 22, 12, 20, 15, 21, 13, 18, 17]},
        {"player": "ZywOo", "team": "Vitality", "opponent": "MOUZ", "prop_type": "Maps 1-2 Kills", "line": 36.5, "kpr_l15": 0.88, "expected_rounds": 45.0, "map_factor": 1.08, "opponent_adj": 0.98, "last_10_logs": [38, 41, 37, 39, 35, 40, 38, 37, 42, 39]},
        {"player": "frozen", "team": "FaZe", "opponent": "NAVI", "prop_type": "Map 1 Kills", "line": 16.5, "kpr_l15": 0.68, "expected_rounds": 22.5, "map_factor": 0.92, "opponent_adj": 0.95, "last_10_logs": [14, 13, 15, 12, 18, 14, 15, 13, 16, 12]}
    ]
    board_df = pd.DataFrame(demo_data)


# ==========================================
# MAIN DASHBOARD DISPLAY
# ==========================================
if board_df is not None and not board_df.empty:
    
    # Process the entire board
    processed_df = scan_cs2_props(board_df, min_gap=gap_threshold, min_hit_rate=hit_rate_threshold)
    
    # Qualified Picks Subsets
    qualified_df = processed_df[processed_df['recommendation'] != 'PASS (NO EDGE)']
    overs_df = processed_df[processed_df['recommendation'] == 'QUALIFIED OVER 🔒']
    unders_df = processed_df[processed_df['recommendation'] == 'QUALIFIED UNDER 🔒']
    
    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Board Props", len(processed_df))
    col2.metric("Qualified Locks", len(qualified_df))
    col3.metric("Over Locks 🔒", len(overs_df))
    col4.metric("Under Locks 🔒", len(unders_df))
    
    st.markdown("---")
    
    # View Toggle Tabs
    tab1, tab2 = st.tabs(["🔒 Qualified Plays Only", "📋 Complete Board Audit"])
    
    with tab1:
        st.subheader("High-EV Qualified Picks")
        if qualified_df.empty:
            st.warning("No props on the current board met both strict consistency and projection gap thresholds.")
        else:
            # Table formatting
            display_cols = ['player', 'team', 'opponent', 'prop_type', 'line', 'projected_kills', 'proj_gap', 'over_hit_rate', 'under_hit_rate', 'recommendation']
            
            st.dataframe(
                qualified_df[display_cols].style.format({
                    'line': '{:.1f}',
                    'projected_kills': '{:.2f}',
                    'proj_gap': '{:+.2f}',
                    'over_hit_rate': '{:.0%}',
                    'under_hit_rate': '{:.0%}'
                }),
                use_container_width=True
            )
            
            # Download button for qualified plays
            csv_data = qualified_df[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Qualified Slips CSV",
                data=csv_data,
                file_name="qualified_cs2_locks.csv",
                mime="text/csv"
            )

    with tab2:
        st.subheader("All Scanned Board Lines")
        st.dataframe(
            processed_df.style.format({
                'line': '{:.1f}',
                'projected_kills': '{:.2f}',
                'proj_gap': '{:+.2f}',
                'over_hit_rate': '{:.0%}',
                'under_hit_rate': '{:.0%}'
            }),
            use_container_width=True
        )

else:
    st.info("👈 Please select a data ingestion method in the sidebar or load the sample board to scan.")
