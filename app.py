import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")
st.title("🏦 LCSLarry CS2 Engine - Live Board")

picks_board = [
    {"player": "3gl", "team": "Rare Atom", "match": "3gl vs Lynn Vision", "line": 23.0, "mu": 24.5, "side": "OVER", "prob": 0.61, "edge": 0.065, "prizepicks_line": 23.0, "draftkings_line": 22.5, "bet365_line": 22.5, "ggbet_line": 23.0},
    {"player": "AW", "team": "Magic Esport", "match": "AW vs K27", "line": 29.5, "mu": 27.0, "side": "UNDER", "prob": 0.62, "edge": 0.08, "prizepicks_line": 29.5, "draftkings_line": 30.0, "bet365_line": 30.0, "ggbet_line": 29.5},
    {"player": "Brollan", "team": "Heroic", "match": "Brollan vs 3DMAX", "line": 28.5, "mu": 30.5, "side": "OVER", "prob": 0.63, "edge": 0.07, "prizepicks_line": 28.5, "draftkings_line": 28.0, "bet365_line": 28.0, "ggbet_line": 28.5},
    {"player": "C4LLM3SU3", "team": "Lynn Vision", "match": "C4LLM3SU3 vs Rare Atom", "line": 26.5, "mu": 24.5, "side": "UNDER", "prob": 0.60, "edge": 0.075, "prizepicks_line": 26.5, "draftkings_line": 27.0, "bet365_line": 27.0, "ggbet_line": 26.5},
    {"player": "ChildKing", "team": "Rare Atom", "match": "ChildKing vs Lynn Vision", "line": 27.5, "mu": 29.5, "side": "OVER", "prob": 0.62, "edge": 0.07, "prizepicks_line": 27.5, "draftkings_line": 27.0, "bet365_line": 27.0, "ggbet_line": 27.5},
    {"player": "Chr1zN", "team": "Heroic", "match": "Chr1zN vs 3DMAX", "line": 28.5, "mu": 26.5, "side": "UNDER", "prob": 0.61, "edge": 0.07, "prizepicks_line": 28.5, "draftkings_line": 29.0, "bet365_line": 29.0, "ggbet_line": 28.5},
    {"player": "EmiliaQAQ", "team": "Lynn Vision", "match": "EmiliaQAQ vs Rare Atom", "line": 26.0, "mu": 28.0, "side": "OVER", "prob": 0.62, "edge": 0.07, "prizepicks_line": 26.0, "draftkings_line": 25.5, "bet365_line": 25.5, "ggbet_line": 26.0},
    {"player": "FL4MUS", "team": "GamerLegion", "match": "FL4MUS vs Nuclear Tigeres", "line": 32.0, "mu": 34.5, "side": "OVER", "prob": 0.64, "edge": 0.078, "prizepicks_line": 32.0, "draftkings_line": 31.5, "bet365_line": 31.5, "ggbet_line": 32.0},
    {"player": "Graviti", "team": "3DMAX", "match": "Graviti vs Heroic", "line": 26.0, "mu": 24.0, "side": "UNDER", "prob": 0.60, "edge": 0.075, "prizepicks_line": 26.0, "draftkings_line": 26.5, "bet365_line": 26.5, "ggbet_line": 26.0},
    {"player": "JDC", "team": "BIG", "match": "JDC vs Nemiga Gaming", "line": 30.5, "mu": 32.5, "side": "OVER", "prob": 0.62, "edge": 0.065, "prizepicks_line": 30.5, "draftkings_line": 30.0, "bet365_line": 30.0, "ggbet_line": 30.5},
    {"player": "JW", "team": "Eyeballers", "match": "JW vs DENDELE CS", "line": 27.5, "mu": 25.0, "side": "UNDER", "prob": 0.63, "edge": 0.09, "prizepicks_line": 27.5, "draftkings_line": 28.0, "bet365_line": 28.0, "ggbet_line": 27.5},
    {"player": "JamYoung", "team": "Tyloo", "match": "JamYoung vs Kaleido Gaming", "line": 31.0, "mu": 33.5, "side": "OVER", "prob": 0.63, "edge": 0.08, "prizepicks_line": 31.0, "draftkings_line": 30.5, "bet365_line": 30.5, "ggbet_line": 31.0},
    {"player": "Jee", "team": "Tyloo", "match": "Jee vs Kaleido Gaming", "line": 30.0, "mu": 27.5, "side": "UNDER", "prob": 0.61, "edge": 0.08, "prizepicks_line": 30.0, "draftkings_line": 30.5, "bet365_line": 30.5, "ggbet_line": 30.0},
    {"player": "KRIMZ", "team": "Eyeballers", "match": "KRIMZ vs DENDELE CS", "line": 29.5, "mu": 32.0, "side": "OVER", "prob": 0.64, "edge": 0.08, "prizepicks_line": 29.5, "draftkings_line": 29.0, "bet365_line": 29.0, "ggbet_line": 29.5},
    {"player": "KaiRON-", "team": "Nemiga Gaming", "match": "KaiRON- vs BIG", "line": 29.0, "mu": 31.5, "side": "OVER", "prob": 0.63, "edge": 0.085, "prizepicks_line": 29.0, "draftkings_line": 28.5, "bet365_line": 28.5, "ggbet_line": 29.0},
    {"player": "Kursy", "team": "3DMAX", "match": "Kursy vs Heroic", "line": 29.5, "mu": 27.0, "side": "UNDER", "prob": 0.62, "edge": 0.085, "prizepicks_line": 29.5, "draftkings_line": 30.0, "bet365_line": 30.0, "ggbet_line": 29.5},
    {"player": "L1haNg", "team": "Rare Atom", "match": "L1haNg vs Lynn Vision", "line": 24.0, "mu": 22.0, "side": "UNDER", "prob": 0.60, "edge": 0.08, "prizepicks_line": 24.0, "draftkings_line": 24.5, "bet365_line": 24.5, "ggbet_line": 24.0},
    {"player": "Lucky", "team": "3DMAX", "match": "Lucky vs Heroic", "line": 27.5, "mu": 25.0, "side": "UNDER", "prob": 0.61, "edge": 0.09, "prizepicks_line": 27.5, "draftkings_line": 28.0, "bet365_line": 28.0, "ggbet_line": 27.5},
    {"player": "MITHPUTTINI", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": 31.0, "side": "OVER", "prob": 0.65, "edge": 0.085, "prizepicks_line": 28.5, "draftkings_line": 28.0, "bet365_line": 28.0, "ggbet_line": 28.5},
    {"player": "MaSvAl", "team": "Magic Esport", "match": "MaSvAl vs K27", "line": 29.5, "mu": 27.0, "side": "UNDER", "prob": 0.61, "edge": 0.08, "prizepicks_line": 29.5, "draftkings_line": 30.0, "bet365_line": 30.0, "ggbet_line": 29.5},
    {"player": "Maka", "team": "3DMAX", "match": "Maka vs Heroic", "line": 27.0, "mu": 24.5, "side": "UNDER", "prob": 0.62, "edge": 0.09, "prizepicks_line": 27.0, "draftkings_line": 27.5, "bet365_line": 27.5, "ggbet_line": 27.0},
    {"player": "MartinezSa", "team": "Heroic", "match": "MartinezSa vs 3DMAX", "line": 31.0, "mu": 33.5, "side": "OVER", "prob": 0.63, "edge": 0.08, "prizepicks_line": 31.0, "draftkings_line": 30.5, "bet365_line": 30.5, "ggbet_line": 31.0},
    {"player": "Mercury", "team": "Tyloo", "match": "Mercury vs Kaleido Gaming", "line": 28.0, "mu": 30.5, "side": "OVER", "prob": 0.63, "edge": 0.09, "prizepicks_line": 28.0, "draftkings_line": 27.5, "bet365_line": 27.5, "ggbet_line": 28.0},
    {"player": "Moseyuh", "team": "Tyloo", "match": "Moseyuh vs Kaleido Gaming", "line": 28.5, "mu": 31.0, "side": "OVER", "prob": 0.64, "edge": 0.085, "prizepicks_line": 28.5, "draftkings_line": 28.0, "bet365_line": 28.0, "ggbet_line": 28.5},
    {"player": "REZ", "team": "GamerLegion", "match": "REZ vs Nuclear Tigeres", "line": 31.0, "mu": 33.5, "side": "OVER", "prob": 0.63, "edge": 0.08, "prizepicks_line": 31.0, "draftkings_line": 30.5, "bet365_line": 30.5, "ggbet_line": 31.0},
    {"player": "Ro1f", "team": "Eyeballers", "match": "Ro1f vs DENDELE CS", "line": 27.0, "mu": 24.5, "side": "UNDER", "prob": 0.61, "edge": 0.09, "prizepicks_line": 27.0, "draftkings_line": 27.5, "bet365_line": 27.5, "ggbet_line": 27.0},
    {"player": "Snax", "team": "GamerLegion", "match": "Snax vs Nuclear Tigeres", "line": 25.5, "mu": 23.0, "side": "UNDER", "prob": 0.61, "edge": 0.095, "prizepicks_line": 25.5, "draftkings_line": 26.0, "bet365_line": 26.0, "ggbet_line": 25.5},
    {"player": "Starry", "team": "Lynn Vision", "match": "Starry vs Rare Atom", "line": 31.5, "mu": 34.0, "side": "OVER", "prob": 0.64, "edge": 0.079, "prizepicks_line": 31.5, "draftkings_line": 31.0, "bet365_line": 31.0, "ggbet_line": 31.5},
    {"player": "Summer", "team": "Rare Atom", "match": "Summer vs Lynn Vision", "line": 23.0, "mu": 20.5, "side": "UNDER", "prob": 0.62, "edge": 0.10, "prizepicks_line": 23.0, "draftkings_line": 23.5, "bet365_line": 23.5, "ggbet_line": 23.0},
    {"player": "Tauson", "team": "GamerLegion", "match": "Tauson vs Nuclear Tigeres", "line": 29.0, "mu": 31.5, "side": "OVER", "prob": 0.63, "edge": 0.085, "prizepicks_line": 29.0, "draftkings_line": 28.5, "bet365_line": 28.5, "ggbet_line": 29.0}
]

for b in picks_board:
    pp_diff = b['line'] - b['prizepicks_line']
    dk_diff = b['line'] - b['draftkings_line']
    b365_diff = b['line'] - b['bet365_line']
    gg_diff = b['line'] - b['ggbet_line']
    
    hammer_tag = None
    if b['side'] == 'OVER' and (pp_diff < 0 or dk_diff < 0 or b365_diff < 0 or gg_diff < 0):
        hammer_tag = "🔨 HAMMER MORE"
    elif b['side'] == 'UNDER' and (pp_diff > 0 or dk_diff > 0 or b365_diff > 0 or gg_diff > 0):
        hammer_tag = "🔨 HAMMER LESS"

    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{b['player']}** ({b['team']})  \n*{b['match']}*  \n**{hammer_tag or 'Standard Edge'}**")
        with col2:
            st.markdown(f"**Side:** `{b['side']}` | **Line:** {b['line']}  \n*PP:* {b['prizepicks_line']} | *DK:* {b['draftkings_line']} | *b365:* {b['bet365_line']} | *GG:* {b['ggbet_line']}")
        with col3:
            st.metric(label="Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}%")
        st.markdown("---")
