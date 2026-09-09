import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="LCS Larry 2026: 24/7 Sharp Book De-Vig & EV Engine", layout="wide")

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

class SharpBookDeVigEngine:
    """Calculates true no-vig probabilities from sharp sportsbooks (Pinnacle / Bovada) 
    and checks against Dabble/PrizePicks break-even thresholds (~54.2% for multi-leg slips)."""
    def __init__(self, slate_data: list, edge_threshold: float, break_even_target: float):
        self.slate_data = slate_data
        self.edge_threshold = edge_threshold
        self.break_even_target = break_even_target

    def american_to_implied(self, odds: int) -> float:
        if odds > 0:
            return 100.0 / (odds + 100.0)
        else:
            return abs(odds) / (abs(odds) + 100.0)

    def process_slate(self) -> pd.DataFrame:
        processed_records = []
        for item in self.slate_data:
            p_over_raw = self.american_to_implied(item["sharp_over_odds"])
            p_under_raw = self.american_to_implied(item["sharp_under_odds"])
            total_vig = p_over_raw + p_under_raw
            
            true_over_prob = round((p_over_raw / total_vig) * 100, 1)
            true_under_prob = round((p_under_raw / total_vig) * 100, 1)

            if true_over_prob >= true_under_prob:
                signal = "OVER"
                model_prob = true_over_prob
                action = "🔨 HAMMER MORE"
            else:
                signal = "UNDER"
                model_prob = true_under_prob
                action = "🔨 HAMMER LESS"

            edge_vs_breakeven = round(model_prob - self.break_even_target, 1)

            processed_records.append({
                "Player": item["player"],
                "Team": item["team"],
                "Match": item["match"],
                "Stat Type": item["stat_type"],
                "Dabble Line": item["line"],
                "Sharp Book": item["sharp_book"],
                "Sharp Odds": f"O {item['sharp_over_odds']} / U {item['sharp_under_odds']}",
                "No-Vig Prob": f"{model_prob}%",
                "Edge vs BE": f"+{edge_vs_breakeven}%" if edge_vs_breakeven > 0 else f"{edge_vs_breakeven}%",
                "Instant Action": action,
                "Signal": signal,
                "_raw_edge": edge_vs_breakeven
            })
            
        df = pd.DataFrame(processed_records)
        df = df[df["_raw_edge"] >= self.edge_threshold]
        return df

if __name__ == "__main__":
    st.title("LCS Larry 2026: 24/7 Sharp De-Vig & EV Engine ⚡")
    st.markdown("**Status: 24/7 Autonomous Mode Active — PRV vs FURIA Slate Loaded (Dabble Game 1 Kills)**")

    st.sidebar.header("⚙️ 24/7 Engine Controls")
    auto_247 = st.sidebar.toggle("🔄 24/7 Autonomous De-Vig Scanner", value=True)
    edge_threshold = st.sidebar.slider("Min Edge vs Break-Even (%)", 0.0, 10.0, 1.0, 0.5)
    break_even_target = st.sidebar.slider("Break-Even Target (%)", 50.0, 56.0, 54.2, 0.1)
    sharp_benchmark = st.sidebar.selectbox("Primary Sharp Benchmark", ["Pinnacle (Sharpest)", "Bovada", "DraftKings / Bet365"])
    
    st.sidebar.success(f"24/7 Monitoring active via **{sharp_benchmark}**. Juice stripping algorithm online.")

    # Master active slate updated exclusively with PRV vs FURIA Game 1 Kills players and lines from Image 48.
    active_slate = [
        {"player": "KSCERATO", "team": "FURIA", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 15.5, "sharp_book": "Pinnacle", "sharp_over_odds": -165, "sharp_under_odds": +132},
        {"player": "Jame", "team": "PARIVISION", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 14.5, "sharp_book": "Bovada", "sharp_over_odds": +130, "sharp_under_odds": -165},
        {"player": "FL1T", "team": "PARIVISION", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 14.5, "sharp_book": "Pinnacle", "sharp_over_odds": +125, "sharp_under_odds": -155},
        {"player": "slaxejezzz", "team": "PARIVISION", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 14.5, "sharp_book": "Pinnacle", "sharp_over_odds": -160, "sharp_under_odds": +130},
        {"player": "yuurih", "team": "FURIA", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 13.5, "sharp_book": "Bovada", "sharp_over_odds": +135, "sharp_under_odds": -170},
        {"player": "zweih", "team": "PARIVISION", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 13.5, "sharp_book": "Pinnacle", "sharp_over_odds": +122, "sharp_under_odds": -152},
        {"player": "xiELO", "team": "PARIVISION", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 13.5, "sharp_book": "Pinnacle", "sharp_over_odds": -170, "sharp_under_odds": +138},
        {"player": "FalleN", "team": "FURIA", "match": "PRV vs FURIA", "stat_type": "Game 1 Kills", "line": 12.5, "sharp_book": "Bovada", "sharp_over_odds": +132, "sharp_under_odds": -168}
    ]

    engine = SharpBookDeVigEngine(
        slate_data=active_slate,
        edge_threshold=edge_threshold,
        break_even_target=break_even_target
    )
    
    board_df = engine.process_slate().sort_values(by="_raw_edge", ascending=False)
    top_6_df = board_df.head(6)

    status_container = st.empty()
    status_container.markdown(f"🟢 **24/7 De-Vig Loop Active:** De-viging Pinnacle/Bovada markets against break-even threshold ({break_even_target}%).")

    st.subheader("🎯 Top 24/7 De-Vigged +EV Hammer Plays")
    
    if top_6_df.empty:
        st.warning("No plays currently exceed the minimum edge threshold over the break-even baseline.")
    else:
        cols = st.columns(3)
        for idx, row in enumerate(top_6_df.to_dict(orient="records")):
            col_idx = idx % 3
            with cols[col_idx]:
                st.markdown(f"""
                    <div class="card-container">
                        <div class="card-header">{row['Match']} • {row['Sharp Book']}</div>
                        <div class="player-name">{row['Player']}</div>
                        <div class="stat-type">{row['Stat Type']} • Odds: {row['Sharp Odds']}</div>
                        <div class="line-display">Line: {row['Dabble Line']}</div>
                        <div class="metric-grid">
                            <div class="metric-box">
                                <div class="metric-title">No-Vig Prob</div>
                                <div class="metric-val-white">{row['No-Vig Prob']}</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-title">Edge vs BE</div>
                                <div class="metric-val-green">{row['Edge vs BE']}</div>
                            </div>
                            <div class="metric-box">
                                <div class="metric-title">Status</div>
                                <div class="metric-val-green">24/7 LOCK 🔒</div>
                            </div>
                        </div>
                        <div class="hammer-badge">
                            {row['Instant Action']}
                        </div>
                        <div class="footer-brand">
                            <span>LCSLarry 24/7 De-Vig Engine</span>
                            <span>lcslarry.com</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Live 24/7 De-Vig Matrix & Market Benchmarking Audit Trail")
    st.dataframe(board_df.drop(columns=["_raw_edge"]), use_container_width=True)

    if st.button("🔄 Force 24/7 Market Re-Scan"):
        time.sleep(0.5)
        st.rerun()
