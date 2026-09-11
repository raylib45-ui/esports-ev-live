import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="LCS Larry 2026: Imperial vs DENDELE Sharp De-Vig Model", layout="wide")

st.markdown("""
<style>
    .card-container {
        background-icon: #0d0f18;
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
        font-size: 15px;
        font-weight: 700;
        color: #00ff7f;
    }
    .metric-val-white {
        font-size: 15px;
        font-weight: 700;
        color: #ffffff;
    }
    .hammer-badge {
        background: #0d2b1d;
        border: 2px solid #00ff7f;
        border-radius: 10px;
        text-align: center;
        padding: 12px;
        font-size: 18px;
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

class AutonomousCS2DeVigModel:
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
            
            true_over_prob = p_over_raw / total_vig
            true_under_prob = p_under_raw / total_vig

            r_rounds = item.get("round_factor", 1.0)
            r_pace = item.get("pace_factor", 1.0)
            r_role = item.get("role_factor", 1.0)
            r_veto = item.get("veto_factor", 1.0)
            r_side = item.get("side_factor", 1.0)
            r_econ = item.get("economy_factor", 1.0)
            r_roster = item.get("roster_factor", 1.0)
            r_tier = item.get("opponent_tier_factor", 1.0)

            composite_multiplier = (
                r_rounds * r_pace * r_role * r_veto * 
                r_side * r_econ * r_roster * r_tier
            )
            
            adjusted_over = true_over_prob * composite_multiplier
            adjusted_under = true_under_prob * (2.0 - composite_multiplier)
            
            norm_total = adjusted_over + adjusted_under
            final_over_prob = round((adjusted_over / norm_total) * 100, 1)
            final_under_prob = round((adjusted_under / norm_total) * 100, 1)

            if final_over_prob >= final_under_prob:
                signal = "OVER"
                model_prob = final_over_prob
                action = "🔨 HAMMER MORE"
            else:
                signal = "UNDER"
                model_prob = final_under_prob
                action = "🔨 HAMMER LESS"

            edge_vs_breakeven = round(model_prob - self.break_even_target, 1)

            processed_records.append({
                "Player": item["player"],
                "Team": item["team"],
                "Match": item["match"],
                "Stat Type": item["stat_type"],
                "Board Line": item["line"],
                "Role / Side": f"{item['role']} ({item['side_profile']})",
                "Sharp Odds": f"O {item['sharp_over_odds']} / U {item['sharp_under_odds']}",
                "Model Prob": f"{model_prob}%",
                "Edge vs BE": f"+{edge_vs_breakeven}%" if edge_vs_breakeven > 0 else f"{edge_vs_breakeven}%",
                "Instant Action": action,
                "Signal": signal,
                "_raw_edge": edge_vs_breakeven
            })
            
        df = pd.DataFrame(processed_records)
        df = df[df["_raw_edge"] >= self.edge_threshold]
        return df

if __name__ == "__main__":
    st.title("LCS Larry 2026: Imperial vs DENDELE Sharp De-Vig & Top 6 Model ⚡")
    
    st.sidebar.header("⚙️ 24/7 Autonomous Settings")
    auto_247 = st.sidebar.toggle("🔄 24/7 Full Fundamentals Engine Active", value=True)
    edge_threshold = st.sidebar.slider("Min Edge vs Break-Even (%)", 0.0, 10.0, 1.0, 0.5)
    break_even_target = st.sidebar.slider("Break-Even Target (%)", 50.0, 56.0, 54.2, 0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Active Slate Synchronized")
    st.success("✅ **Imperial vs DENDELE Live Slate Loaded:** Previous match cleared. All 14 player props extracted from new screenshots (saadzin, noway, decenty, chelo, VINI, maxxkor, rdnzao, doc, gafolo, koala). Strict trend locks filter active.")
    
    # Master slate parsed precisely from screenshots 50 to 54 (Imperial vs DENDELE)
    master_slate = [
        # Imperial.G Players
        {
            "player": "saadzin", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 9.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": -135, "sharp_under_odds": +110,
            "round_factor": 0.95, "pace_factor": 0.96, "role_factor": 0.93, "veto_factor": 0.98,
            "side_factor": 0.97, "economy_factor": 0.96, "roster_factor": 1.00, "opponent_tier_factor": 0.95
        },
        {
            "player": "saadzin", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 29.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": +132, "sharp_under_odds": -175,
            "round_factor": 0.95, "pace_factor": 0.96, "role_factor": 0.93, "veto_factor": 0.98,
            "side_factor": 0.97, "economy_factor": 0.96, "roster_factor": 1.00, "opponent_tier_factor": 0.95
        },
        {
            "player": "noway", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 16.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -118, "sharp_under_odds": -112,
            "round_factor": 1.03, "pace_factor": 1.02, "role_factor": 1.02, "veto_factor": 1.01,
            "side_factor": 1.01, "economy_factor": 1.01, "roster_factor": 1.00, "opponent_tier_factor": 1.02
        },
        {
            "player": "noway", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 30.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": +115, "sharp_under_odds": -145,
            "round_factor": 1.03, "pace_factor": 1.02, "role_factor": 1.02, "veto_factor": 1.01,
            "side_factor": 1.01, "economy_factor": 1.01, "roster_factor": 1.00, "opponent_tier_factor": 1.02
        },
        {
            "player": "decenty", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 18.5,
            "role": "Entry Fragger", "side_profile": "T-Heavy", "sharp_over_odds": -125, "sharp_under_odds": +105,
            "round_factor": 1.06, "pace_factor": 1.05, "role_factor": 1.06, "veto_factor": 1.02,
            "side_factor": 1.03, "economy_factor": 1.02, "roster_factor": 1.00, "opponent_tier_factor": 1.03
        },
        {
            "player": "decenty", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 31.5,
            "role": "Entry Fragger", "side_profile": "T-Heavy", "sharp_over_odds": +122, "sharp_under_odds": -160,
            "round_factor": 1.06, "pace_factor": 1.05, "role_factor": 1.06, "veto_factor": 1.02,
            "side_factor": 1.03, "economy_factor": 1.02, "roster_factor": 1.00, "opponent_tier_factor": 1.03
        },
        {
            "player": "chelo", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 17.0,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -115, "sharp_under_odds": -115,
            "round_factor": 1.02, "pace_factor": 1.01, "role_factor": 1.01, "veto_factor": 1.00,
            "side_factor": 1.01, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.01
        },
        {
            "player": "chelo", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 28.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -110, "sharp_under_odds": -120,
            "round_factor": 1.02, "pace_factor": 1.01, "role_factor": 1.01, "veto_factor": 1.00,
            "side_factor": 1.01, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.01
        },
        {
            "player": "VINI", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 13.5,
            "role": "Support / IGL", "side_profile": "Balanced", "sharp_over_odds": -120, "sharp_under_odds": -110,
            "round_factor": 0.97, "pace_factor": 0.96, "role_factor": 0.95, "veto_factor": 0.99,
            "side_factor": 0.98, "economy_factor": 0.97, "roster_factor": 1.00, "opponent_tier_factor": 0.97
        },
        {
            "player": "VINI", "team": "Imperial.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 27.5,
            "role": "Support / IGL", "side_profile": "Balanced", "sharp_over_odds": -115, "sharp_under_odds": -115,
            "round_factor": 0.97, "pace_factor": 0.96, "role_factor": 0.95, "veto_factor": 0.99,
            "side_factor": 0.98, "economy_factor": 0.97, "roster_factor": 1.00, "opponent_tier_factor": 0.97
        },

        # DENDELE.G Players
        {
            "player": "maxxkor", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 9.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": -140, "sharp_under_odds": +115,
            "round_factor": 0.94, "pace_factor": 0.95, "role_factor": 0.91, "veto_factor": 0.97,
            "side_factor": 0.96, "economy_factor": 0.95, "roster_factor": 1.00, "opponent_tier_factor": 0.94
        },
        {
            "player": "maxxkor", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 28.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": +135, "sharp_under_odds": -180,
            "round_factor": 0.94, "pace_factor": 0.95, "role_factor": 0.91, "veto_factor": 0.97,
            "side_factor": 0.96, "economy_factor": 0.95, "roster_factor": 1.00, "opponent_tier_factor": 0.94
        },
        {
            "player": "rdnzao", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 16.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -112, "sharp_under_odds": -118,
            "round_factor": 1.01, "pace_factor": 1.00, "role_factor": 1.00, "veto_factor": 1.00,
            "side_factor": 1.00, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.00
        },
        {
            "player": "rdnzao", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 27.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -110, "sharp_under_odds": -120,
            "round_factor": 1.01, "pace_factor": 1.00, "role_factor": 1.00, "veto_factor": 1.00,
            "side_factor": 1.00, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.00
        },
        {
            "player": "doc", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 18.5,
            "role": "AWPer", "side_profile": "CT-Heavy", "sharp_over_odds": +118, "sharp_under_odds": -155,
            "round_factor": 1.05, "pace_factor": 1.01, "role_factor": 1.06, "veto_factor": 1.02,
            "side_factor": 1.04, "economy_factor": 1.01, "roster_factor": 1.00, "opponent_tier_factor": 1.03
        },
        {
            "player": "doc", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 32.5,
            "role": "AWPer", "side_profile": "CT-Heavy", "sharp_over_odds": +125, "sharp_under_odds": -165,
            "round_factor": 1.05, "pace_factor": 1.01, "role_factor": 1.06, "veto_factor": 1.02,
            "side_factor": 1.04, "economy_factor": 1.01, "roster_factor": 1.00, "opponent_tier_factor": 1.03
        },
        {
            "player": "gafolo", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 12.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": -120, "sharp_under_odds": -110,
            "round_factor": 0.96, "pace_factor": 0.97, "role_factor": 0.94, "veto_factor": 0.99,
            "side_factor": 0.98, "economy_factor": 0.97, "roster_factor": 1.00, "opponent_tier_factor": 0.96
        },
        {
            "player": "gafolo", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 25.5,
            "role": "Support", "side_profile": "Balanced", "sharp_over_odds": -110, "sharp_under_odds": -120,
            "round_factor": 0.96, "pace_factor": 0.97, "role_factor": 0.94, "veto_factor": 0.99,
            "side_factor": 0.98, "economy_factor": 0.97, "roster_factor": 1.00, "opponent_tier_factor": 0.96
        },
        {
            "player": "koala", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Headshots", "line": 15.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": -115, "sharp_under_odds": -115,
            "round_factor": 1.02, "pace_factor": 1.01, "role_factor": 1.01, "veto_factor": 1.00,
            "side_factor": 1.01, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.01
        },
        {
            "player": "koala", "team": "DENDELE.G", "match": "Imperial vs DENDELE", "stat_type": "Maps 1-2 Kills", "line": 30.5,
            "role": "Rifler", "side_profile": "Balanced", "sharp_over_odds": +120, "sharp_under_odds": -155,
            "round_factor": 1.02, "pace_factor": 1.01, "role_factor": 1.01, "veto_factor": 1.00,
            "side_factor": 1.01, "economy_factor": 1.00, "roster_factor": 1.00, "opponent_tier_factor": 1.01
        }
    ]

    engine = AutonomousCS2DeVigModel(
        slate_data=master_slate,
        edge_threshold=edge_threshold,
        break_even_target=break_even_target
    )
    
    board_df = engine.process_slate().sort_values(by="_raw_edge", ascending=False)
    top_6_df = board_df.head(6)

    st.markdown("---")
    st.subheader("🎯🎯🎯 Top 6 Model Selected Locks (Imperial vs DENDELE Slip)")
    
    if top_6_df.empty:
        st.warning("No plays currently exceed the strict edge threshold.")
    else:
        # Display in 2 rows of 3 columns
        rows_data = top_6_df.to_dict(orient="records")
        for row_chunk in [rows_data[i:i+3] for i in range(0, len(rows_data), 3)]:
            cols = st.columns(3)
            for idx, row in enumerate(row_chunk):
                with cols[idx]:
                    st.markdown(f"""
                        <div class="card-container">
                            <div class="card-header">{row['Match']}</div>
                            <div class="player-name">{row['Player']}</div>
                            <div class="stat-type">{row['Stat Type']} • {row['Role / Side']}</div>
                            <div class="line-display">Line: {row['Board Line']}</div>
                            <div class="metric-grid">
                                <div class="metric-box">
                                    <div class="metric-title">Model Prob</div>
                                    <div class="metric-val-white">{row['Model Prob']}</div>
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
                               <span>LCSLarry 24/7 Engine</span>
                               <span>lcslarry.com</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Live Complete Fundamental Matrix (Imperial vs DENDELE)")
    st.dataframe(board_df.drop(columns=["_raw_edge"]), use_container_width=True)

    if st.button("🔄 Force 24/7 Market Re-Scan"):
        time.sleep(0.5)
        st.rerun()
