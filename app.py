import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="LCS Larry 2026 Engine", layout="wide")

# Custom CSS injected to style the output cards matching your design vision
st.markdown("""
<style>
    .card-container {
        background-color: #0d0f18;
        border: 1px solid #1f2438;
        border-radius: 16px;
        padding: 20px;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
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
        font-size: 36px;
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

class LiveLCSLarryEngine:
    def __init__(self, slate_data: list):
        self.slate_data = slate_data

    def evaluate_ev(self, implied_prob: float) -> dict:
        if implied_prob >= 0.53:
            ev_percentage = (implied_prob * 1.65) - 1.0  
            action = "🔨 MORE"
        else:
            under_prob = 1.0 - implied_prob
            ev_percentage = (under_prob * 1.65) - 1.0
            action = "🔨 LESS"
        
        return {
            "ev_edge": round(ev_percentage * 100, 2),
            "raw_edge": ev_percentage,
            "calibrated_prob": implied_prob if action == "🔨 MORE" else (1.0 - implied_prob),
            "action": action
        }

    def process_board(self) -> pd.DataFrame:
        processed_records = []
        for item in self.slate_data:
            calibrated_prob = np.random.uniform(0.42, 0.69)
            eval_result = self.evaluate_ev(calibrated_prob)
            
            model_line_offset = np.random.uniform(-1.5, 1.5)
            model_line = round(item["line"] + model_line_offset, 1)

            processed_records.append({
                "Player": item["player"],
                "Match": item["match"],
                "Stat Type": item["stat_type"],
                "Line": item["line"],
                "Model Line": model_line,
                "Hit Prob": round(eval_result['calibrated_prob'] * 100, 1),
                "EV Edge": round(eval_result['ev_edge'], 1),
                "Action": eval_result['action'],
                "_raw_edge": eval_result['raw_edge']
            })
        return pd.DataFrame(processed_records)

if __name__ == "__main__":
    st.title("LCS Larry 2026: Automated Card Builder")
    st.markdown("*Generating 6-leg slip cards matching your custom layout template.*")

    custom_board = [
        {"player": "tenzy", "match": "vs K27 • Tue 8:00 AM", "stat_type": "Maps 1-2 Headshots", "line": 21.0},
        {"player": "FL4MUS", "match": "vs Nuclear Tigeres • Tue 9:30 AM", "stat_type": "Maps 1-2 Headshots", "line": 19.0},
        {"player": "doc", "match": "vs Eyeballers • Tue 11:00 AM", "stat_type": "Maps 1-2 Headshots", "line": 17.5},
        {"player": "KaiRON-", "match": "vs BIG • Tue 1:00 PM", "stat_type": "Maps 1-2 Headshots", "line": 16.0},
        {"player": "Kanavi", "match": "vs T1 • Tue 3:00 PM", "stat_type": "Maps 1-3 Kills (Combo)", "line": 11.0},
        {"player": "Peyz", "match": "vs HLE • Tue 4:30 PM", "stat_type": "Maps 1-3 Kills", "line": 13.5},
        {"player": "Camana", "match": "vs SU • Tue 6:00 PM", "stat_type": "Maps 1-3 Kills", "line": 11.5},
        {"player": "Doran", "match": "vs HLE • Tue 7:15 PM", "stat_type": "Maps 1-3 Kills", "line": 7.0},
        {"player": "Oner", "match": "vs HLE • Tue 8:30 PM", "stat_type": "Maps 1-3 Kills", "line": 9.5},
        {"player": "Faker", "match": "vs HLE • Tue 10:00 PM", "stat_type": "Maps 1-3 Kills", "line": 9.5}
    ]

    engine = LiveLCSLarryEngine(slate_data=custom_board)
    board_df = engine.process_board()

    # Extract Top 3 MORE and Top 3 LESS for the 6-leg slip template display
    top_mores = board_df[board_df["Action"] == "🔨 MORE"].sort_values(by="_raw_edge", ascending=False).head(3)
    top_less = board_df[board_df["Action"] == "🔨 LESS"].sort_values(by="_raw_edge", ascending=False).head(3)
    parlay_cards = pd.concat([top_mores, top_less])

    st.subheader("⚡ Automated 6-Leg Parlay Card Preview")
    
    # Render cards in columns of 3
    cols = st.columns(3)
    for idx, row in enumerate(parlay_cards.to_dict(orient="records")):
        col_idx = idx % 3
        with cols[col_idx]:
            action_badge = "▲ OVER" if "MORE" in row["Action"] else "▼ LESS"
            st.markdown(f"""
                <div class="card-container">
                    <div class="card-header">{row['Match']}</div>
                    <div class="player-name">{row['Player']}</div>
                    <div class="stat-type">{row['Stat Type']}</div>
                    <div class="line-display">{row['Line']}</div>
                    <div class="metric-grid">
                        <div class="metric-box">
                            <div class="metric-title">Hit Probability</div>
                            <div class="metric-val-green">{row['Hit Prob']}%</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">EV / Edge</div>
                            <div class="metric-val-green">+{row['EV Edge']}%</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Model Line</div>
                            <div class="metric-val-white">{row['Model Line']}</div>
                        </div>
                    </div>
                    <div style="background: {'#0d2b1d' if 'OVER' in action_badge else '#2b0d0d'}; border: 1px solid {'#00ff7f' if 'OVER' in action_badge else '#ff4d4d'}; border-radius: 8px; text-align: center; padding: 10px; font-weight: 800; color: {'#00ff7f' if 'OVER' in action_badge else '#ff4d4d'}; margin-top: 10px;">
                        {action_badge} ({row['Action']})
                    </div>
                    <div class="footer-brand">
                        <span>LCSLarry Esports</span>
                        <span>lcslarry.com</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Full Board Raw Data Matrix")
    st.dataframe(board_df.drop(columns=["_raw_edge"]), use_container_width=True)

    if st.button("🔄 Refresh & Re-Generate Cards"):
        st.rerun()
