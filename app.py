import math
import streamlit as st

st.set_page_config(page_title="LCSLarry Multi-Esports Sharp Engine", page_icon="🏦", layout="wide")
st.title("🏦 LCSLarry Multi-Esports Sharp Engine (CS2, LoL, Dota 2, Valorant)")
st.caption("Live 2026 Analytics: Screenshot Board Parser & Discrepancy Scanner ⚠️")

st.markdown("---")
uploaded_file = st.file_uploader("Upload PrizePicks Esports Board Screenshot", type=["png", "jpg", "jpeg"])

# Starts completely empty - no old or mock players cached
picks_board = []

if uploaded_file is not None:
    st.success("Screenshot uploaded successfully!")
    
    # NOTE: When your live OCR parser script extracts the players from your 
    # uploaded image, append them to the picks_board list dynamically like this:
    # 
    # picks_board.append({
    #     "player": "ExtractedPlayerName", 
    #     "game": "CS2", 
    #     "team": "TeamName", 
    #     "match": "TeamA vs TeamB", 
    #     "line": 25.5, 
    #     "mu": 28.0, 
    #     "side": "OVER", 
    #     "prob": 0.62, 
    #     "edge": 0.07
    # })
    
    # Left empty intentionally until your custom extraction logic hooks into uploaded_file
    st.info("Awaiting dynamic OCR extraction mapping for this screenshot...")
else:
    st.warning("⚠️ No active board loaded. Upload a screenshot above to run real-time analysis.")

if picks_board:
    st.markdown("### 🔥 Live Scans & Discrepancy Results")
    for b in picks_board:
        is_coin_flip = b['prob'] < 0.55 or b['edge'] < 0.03
        
        if is_coin_flip:
            hammer_tag = "⚠️ WARNING: COIN FLIP (PASS) ⚠️"
        elif b['side'] == 'OVER':
            hammer_tag = "🔨 HAMMER MORE 🔨"
        else:
            hammer_tag = "🔨 HAMMER LESS 🔨"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{b['player']}** [{b['game']}] ({b['team']})  \n*{b['match']}*  \n**{hammer_tag}**")
            with col2:
                st.markdown(f"**Side:** `{b['side']}` | **Line:** {b['line']}  \n*Model Mu:* {b['mu']}")
            with col3:
                st.metric(label="Win Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}% Edge")
            st.markdown("---")
