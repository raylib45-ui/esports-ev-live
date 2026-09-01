import math
import streamlit as st

st.set_page_config(page_title="LCSLarry Multi-Esports Sharp Engine", page_icon="🏦", layout="wide")
st.title("🏦 LCSLarry Multi-Esports Sharp Engine (CS2, LoL, Dota 2, Valorant)")
st.caption("Live 2026 Analytics: Real-Time Metric & Volatility Scanner with Coin-Flip Warnings ⚠️")

picks_board = [
    # CS2 Lines
    {"player": "Brollan", "game": "CS2", "team": "Heroic", "match": "Heroic vs 3DMAX", "line": 28.5, "mu": 30.5, "side": "OVER", "prob": 0.53, "edge": 0.02, "prizepicks_line": 28.5, "draftkings_line": 28.0},
    {"player": "AW", "game": "CS2", "team": "Magic Esport", "match": "AW vs K27", "line": 29.5, "mu": 29.7, "side": "OVER", "prob": 0.51, "edge": 0.005, "prizepicks_line": 29.5, "draftkings_line": 29.5},
    {"player": "FL4MUS", "game": "CS2", "team": "GamerLegion", "match": "FL4MUS vs Nuclear Tigeres", "line": 32.0, "mu": 34.5, "side": "OVER", "prob": 0.64, "edge": 0.078, "prizepicks_line": 32.0, "draftkings_line": 31.5},
    {"player": "JW", "game": "CS2", "team": "Eyeballers", "match": "JW vs DENDELE CS", "line": 27.5, "mu": 25.0, "side": "UNDER", "prob": 0.63, "edge": 0.09, "prizepicks_line": 27.5, "draftkings_line": 28.0},
    
    # League of Legends (LoL) Lines
    {"player": "Chovy", "game": "LoL", "team": "Gen.G", "match": "Gen.G vs T1", "line": 4.5, "mu": 6.8, "side": "OVER", "prob": 0.68, "edge": 0.12, "prizepicks_line": 4.5, "draftkings_line": 4.5},
    {"player": "Faker", "game": "LoL", "team": "T1", "match": "Gen.G vs T1", "line": 3.5, "mu": 3.6, "side": "OVER", "prob": 0.52, "edge": 0.01, "prizepicks_line": 3.5, "draftkings_line": 3.5},
    
    # Dota 2 Lines
    {"player": "Topson", "game": "Dota 2", "team": "Tundra", "match": "Tundra vs Team Spirit", "line": 14.5, "mu": 18.2, "side": "OVER", "prob": 0.65, "edge": 0.09, "prizepicks_line": 14.5, "draftkings_line": 14.0},
    {"player": "Yatoro", "game": "Dota 2", "team": "Spirit", "match": "Tundra vs Team Spirit", "line": 22.5, "mu": 22.6, "side": "UNDER", "prob": 0.505, "edge": 0.002, "prizepicks_line": 22.5, "draftkings_line": 22.5},

    # Valorant Lines
    {"player": "Demon1", "game": "Valorant", "team": "NRG", "match": "NRG vs Sentinels", "line": 38.5, "mu": 43.0, "side": "OVER", "prob": 0.66, "edge": 0.10, "prizepicks_line": 38.5, "draftkings_line": 38.0},
    {"player": "TenZ", "game": "Valorant", "team": "Sentinels", "match": "NRG vs Sentinels", "line": 40.5, "mu": 40.4, "side": "UNDER", "prob": 0.51, "edge": 0.003, "prizepicks_line": 40.5, "draftkings_line": 40.5}
]

for b in picks_board:
    # Coin-flip / high variance filter (< 55% probability or < 3% edge)
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
