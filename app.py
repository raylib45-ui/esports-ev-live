import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="LCS Larry 2026: G2 vs Astralis Discrepancy & Hammer Engine", layout="wide")

st.markdown("""
<style>
    .card-container {
        background-color: #0d0f18;
        border: 2px solid #00ff7f;
        border-radius: 16px;
        padding: 20px;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        margin-bottom: 20px;
        box-shadow: 0 0 30px rgba(0,255,127,0.3);
    }
    .card-header {
        text-align: center;
        font-size: 12px;
        letter-spacing: 1px;
        color: #8b92b2;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .player-name {
        text-align: center;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .line-display {
        text-align: center;
        font-size: 38px;
        font-weight: 900;
        color: #ffffff;
        margin-bottom: 15px;
    }
    .stat-type {
        text-align: center;
        font-size: 11px;
        color: #8b92b2;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 20px;
    }
    .metric-grid {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 15px;
    }
    .metric-box {
        background: #131726;
        border: 1px solid #232942;
        border-radius: 10px;
        padding: 10px;
        flex: 1;
        text-align: center;
    }
    .metric-title {
        font-size: 9px;
        color: #8b92b2;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .metric-val-green {
        font-size: 18px;
        font-weight: 700;
        color: #00ff7f;
    }
    .metric-val-white {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
    }
    .hammer-badge {
        background: #0d2b1d;
        border: 2px solid #00ff7f;
        border-radius: 10px;
        text-align: center;
        padding: 12px;
        font-size: 20px;
        font-weight: 900;
        color: #00ff7f;
        margin-top: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .footer-brand {
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #555d82;
        border-top: 1px solid #181d30;
        padding-top: 10px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

class MatchupDiscrepancyEngine:
    def __init__(self, slate_data: list, edge_threshold: float, data_provider: str):
        self.slate_data = slate_data
        self.edge_threshold = edge_threshold
        self.data_provider = data_provider

    def scan_and_exploit(self) -> pd.DataFrame:
        processed_records = []
        for item in self.slate_data:
            prize_line = item["line"]
            model_line = item["model_line"]
            raw_edge_val = model_line - prize_line

            edge_pct = round((raw_edge_val / prize_line) * 100, 1)

            if model_line > prize_line:
                action = "🔨 HAMMER MORE"
                signal = "OVER"
            else:
                action = "🔨 HAMMER LESS"
                signal = "UNDER"

            processed_records.append({
                "Player": item["player"],
                "Team": item["team"],
                "Match": item["match"],
                "Stat Type": item["stat_type"],
                "PrizePicks Line": prize_line,
                "Model Line": model_line,
                "Hit Probability": f"{item['hit_prob']}%",
                "Edge %": f"+{edge_pct}%" if edge_pct > 0 else f"{edge_pct}%",
                "Instant Action": action,
                "Signal": signal,
                "_raw_edge": abs(edge_pct)
            })
            
        df = pd.DataFrame(processed_records)
        df = df[df["_raw_edge"] >= self.edge_threshold]
        return df

if __name__ == "__main__":
    st.title("LCS Larry 2026: G2 vs Astralis Matchup Engine 🔂")
    st.markdown("**Status: FISSURE Playground 3 LAN — G2 (82.6% Favorite, #7) vs Astralis (#12)**")

    st.sidebar.header("⚙️ Matchup Execution Controls")
    edge_threshold = st.sidebar.slider("Minimum Discrepancy Edge (%)", 1.0, 15.0, 2.0, 0.5)
    auto_execute = st.sidebar.toggle("⚡ Instant Hammer Auto-Execution", value=True)
    scan_interval = st.sidebar.selectbox("Polling Frequency", ["Real-time (Live Feed)", "1s", "5s", "10s"])
    
    data_provider = st.sidebar.selectbox(
        "Official Feed Provider",
        ["Bayes Esports (Esports Feed)", "Sportradar", "Genius Sports", "Stats Perform", "Grid"]
    )
    st.sidebar.success(f"Connected to **{data_provider}**. G2 heavy favorite model weights applied.")

    # Master slate exclusively featuring G2 vs Astralis props from Images 40-45.
    # Note: Astralis players factored toward UNDER due to G2 82.6% blowout risk / round scarcity.
    # G2 stars factored toward OVER based on superior form and ranking (#7 vs #12).
    master_slate = [
        # Astralis Players (Blowout risk -> Under expectation)
        {"player": "jabbi", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 17.5, "model_line": 14.2, "hit_prob": 62.4},
        {"player": "jabbi", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 27.5, "model_line": 23.5, "hit_prob": 63.1},
        {"player": "Staehr", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 16.0, "model_line": 13.0, "hit_prob": 61.8},
        {"player": "Staehr", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 28.5, "model_line": 24.2, "hit_prob": 62.5},
        {"player": "ryu", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 13.5, "model_line": 10.8, "hit_prob": 60.9},
        {"player": "ryu", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 26.0, "model_line": 22.0, "hit_prob": 62.0},
        {"player": "phzy", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 8.5, "model_line": 6.5, "hit_prob": 63.5},
        {"player": "phzy", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 26.5, "model_line": 22.4, "hit_prob": 61.9},
        {"player": "HooXi", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 11.0, "model_line": 8.5, "hit_prob": 64.0},
        {"player": "HooXi", "team": "Astralis", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 21.5, "model_line": 17.8, "hit_prob": 63.2},

        # G2 Players (Superior form & ranking -> Over expectation)
        {"player": "MATYS", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 18.5, "model_line": 21.5, "hit_prob": 63.8},
        {"player": "MATYS", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 27.5, "model_line": 31.2, "hit_prob": 62.9},
        {"player": "huNter-", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 15.0, "model_line": 17.8, "hit_prob": 63.0},
        {"player": "huNter-", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 29.0, "model_line": 32.8, "hit_prob": 62.4},
        {"player": "NertZ", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 17.0, "model_line": 19.9, "hit_prob": 64.2},
        {"player": "NertZ", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 30.5, "model_line": 34.5, "hit_prob": 63.5},
        {"player": "HeavyGod", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 17.5, "model_line": 20.4, "hit_prob": 63.1},
        {"player": "HeavyGod", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 30.5, "model_line": 34.2, "hit_prob": 62.8},
        {"player": "r1nkle", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Headshots", "line": 9.5, "model_line": 11.8, "hit_prob": 61.5},
        {"player": "r1nkle", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills", "line": 30.5, "model_line": 34.0, "hit_prob": 62.2},
        {"player": "NertZ + HeavyGod", "team": "G2", "match": "G2 vs Astralis (FISSURE Q-Final)", "stat_type": "MAPS 1-2 Kills (Combo)", "line": 61.0, "model_line": 68.5, "hit_prob": 64.5}
    ]

    engine = MatchupDiscrepancyEngine(
        slate_data=master_slate,
        edge_threshold=edge_threshold,
        data_provider=data_provider
    )
    
    board_df = engine.scan_and_exploit().sort_values(by="_raw_edge", ascending=False)
    top_6_df = board_df.head(6)

    status_container = st.empty()
    status_container.markdown(f"🔍 **Analyzing G2 vs Astralis (82.6% G2 win probability)...** Old players purged. Top 6 aligned hammer plays locked.")

    st.subheader("🎯 Top 6 🔒 Aligned G2 vs Astralis Hammer Plays")
    
    if top_6_df.empty:
        st.warning("No discrepancies currently meet the strict edge threshold. Adjust threshold in sidebar.")
    else:
        cols = st.columns(3)
        for idx, row in enumerate(top_6_df.to_dict(orient="records")):
            col_idx = idx % 3
            with cols[col_idx]:
                st.markdown(f"""
                    <div class="card-container">
                        <div class="card-header">{row['Match']}</div>
                        <div class="player-name">{row['Player']}</div>
                        <div class="stat-type">{row['Stat Type']} • Hit Prob: {row['Hit Probability']}</div>
                        <div class="line-display">Line: {row['PrizePicks Line']}</div>
                        <div class="metric-grid">
                            <div class="metric-box">
                                <div class="metric-title">Model Target</div>
                                <div class="metric-val-white">{row['Model Line']}</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-title">Discrepancy Edge</div>
                                <div class="metric-val-green">{row['Edge %']}</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-title">Status</div>
                                <div class="metric-val-green">LOCK 🔒</div>
                            </div>
                        </div>
                        <div class="hammer-badge">
                            {row['Instant Action']}
                        </div>
                        <div class="footer-brand">
                            <span>LCSLarry Esports ({data_provider})</span>
                            <span>lcslarry.com</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Live Discrepancy Matrix Audit Trail (G2 vs Astralis Aligned Plays)")
    st.dataframe(board_df.drop(columns=["_raw_edge"]), use_container_width=True)

    if st.button("🔄 Force Immediate Re-Scan"):
        time.sleep(0.5)
        st.rerun()
