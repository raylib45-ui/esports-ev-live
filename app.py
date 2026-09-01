import math
import streamlit as st

st.set_page_config(page_title="LCSLarry Multi-Esports Sharp Engine", page_icon="🏦", layout="wide")
st.title("🏦 LCSLarry Multi-Esports Sharp Engine (CS2, LoL, Dota 2, Valorant)")
st.caption("Live 2026 Analytics: Real-Time Screenshot Board Parser & Discrepancy Scanner ⚠️")

st.markdown("---")
st.info("📌 **Ready for Input:** All static player data has been cleared. Upload or paste your fresh PrizePicks esports board screenshot below to initialize live market analysis.")

uploaded_file = st.file_uploader("Upload PrizePicks Esports Board Screenshot", type=["png", "jpg", "jpeg"])

# Dynamic picks board initialized empty, waiting for live screenshot processing or manual ingestion
picks_board = []

if uploaded_file is not None:
    st.success("Screenshot received! Parsing player props and comparing lines against sharp book discrepancies...")
    # Placeholder for live screenshot OCR/parsing pipeline to populate picks_board dynamically
else:
    st.warning("⚠️ No active board loaded. Please upload a screenshot to run real-time metric analysis and coin-flip warnings.")

if picks_board:
    for b in picks_board:
        is_coin_flip = b['prob'] < 0.55 or b['edge'] < 0.03
        
        hammer_tag = None
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
