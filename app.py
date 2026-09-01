import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")
st.title("🏦 LCSLarry CS2 Engine")

picks_board = [
    {"player": "MITHPUTTINI", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": 29.0, "side": "OVER", "prob": 0.62, "edge": 0.05, "prizepicks_line": 29.0, "draftkings_line": 28.5, "bet365_line": 28.5, "ggbet_line": 29.0},
    {"player": "balencyy", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 31.5, "mu": 32.0, "side": "OVER", "prob": 0.61, "edge": 0.045, "prizepicks_line": 32.0, "draftkings_line": 31.5, "bet365_line": 31.5, "ggbet_line": 32.0},
    {"player": "s1lent", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": 24.0, "side": "UNDER", "prob": 0.64, "edge": 0.06, "prizepicks_line": 28.0, "draftkings_line": 28.5, "bet365_line": 28.5, "ggbet_line": 28.0},
    {"player": "souz4h", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": 29.0, "side": "OVER", "prob": 0.60, "edge": 0.04, "prizepicks_line": 29.0, "draftkings_line": 28.5, "bet365_line": 28.5, "ggbet_line": 29.0},
    {"player": "yeda", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 27.5, "mu": 23.0, "side": "UNDER", "prob": 0.63, "edge": 0.055, "prizepicks_line": 27.0, "draftkings_line": 27.5, "bet365_line": 27.5, "ggbet_line": 27.0}
]

for b in picks_board:
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{b['player']}** ({b['team']})  \n*{b['match']}*")
        with col2:
            st.markdown(f"**Side:** `{b['side']}` | **Line:** {b['line']}")
        with col3:
            st.metric(label="Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}%")
        st.markdown("---")
