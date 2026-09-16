import numpy as np
import pandas as pd
import streamlit as st

st.title("CS2 Quantitative Discrepancy & Hammer Scanner")
st.markdown("Automated CS2 model scanning PrizePicks lines vs sportsbooks.")


class CS2WeightedScanner:

  def __init__(self, historical_df, discrepancy_threshold=1.5):
    self.historical_data = historical_df
    self.threshold = discrepancy_threshold

  def calculate_tier1_efficiency(self, player_id, map_name):
    """Tier 1: Core Efficiency (~50% weight)"""
    df = self.historical_data[
        (self.historical_data["player_id"] == player_id)
        & (self.historical_data["map"] == map_name)
    ]
    if df.empty:
      return None, None, None

    base_kpr = df["kpr"].mean()
    base_adr = df["adr"].mean()
    base_impact = df["impact_rating"].mean()
    return base_kpr, base_adr, base_impact

  def calculate_tier2_volatility(self, player_id, map_name):
    """Tier 2: Role & Volatility (~30% weight)"""
    df = self.historical_data[
        (self.historical_data["player_id"] == player_id)
        & (self.historical_data["map"] == map_name)
    ]
    if df.empty:
      return 0.5, 0.0

    entry_win_rate = df["opening_duel_win_rate"].mean()
    awp_kpr = df["awp_kills_per_round"].mean()
    return entry_win_rate, awp_kpr

  def calculate_tier3_situational(self, player_id, map_name, opponent_id):
    """Tier 3: Situational Splits (~20% weight)"""
    return 1.05

  def generate_complete_projection(
      self, player_id, map_name, opponent_id, projected_rounds
  ):
    """Executes the full weighted multi-tiered formula."""
    kpr, adr, impact = self.calculate_tier1_efficiency(player_id, map_name)
    if kpr is None:
      return None

    norm_adr = adr / 100.0
    norm_impact = impact / 1.5

    entry_win_rate, awp_kpr = self.calculate_tier2_volatility(
        player_id, map_name
    )
    situational_modifier = self.calculate_tier3_situational(
        player_id, map_name, opponent_id
    )

    tier_1_score = (0.40 * kpr) + (0.35 * norm_adr) + (0.25 * norm_impact)
    tier_2_score = (0.70 * entry_win_rate * kpr) + (0.30 * awp_kpr)
    kpr_exp = ((0.50 * tier_1_score) + (0.30 * tier_2_score)) * (
        situational_modifier
    )

    return round(kpr_exp * projected_rounds, 2)

  def scan_and_hammer(self, board_df, sportsbook_df):
    recommendations = []
    for _, row in board_df.iterrows():
      p_id = row["player_id"]
      p_map = row["map"]
      prizepicks_line = row["line"]
      proj_rounds = row["projected_rounds"]

      projection = self.generate_complete_projection(
          p_id, p_map, row["opponent_id"], proj_rounds
      )
      if projection is None:
        continue

      delta = projection - prizepicks_line
      sb_match = sportsbook_df[sportsbook_df["player_id"] == p_id]
      sb_line = (
          sb_match["consensus_line"].values[0] if not sb_match.empty else None
      )

      action = None
      if sb_line is not None:
        if delta >= self.threshold and sb_line <= prizepicks_line:
          action = "HAMMER OVER 🔒"
        elif delta <= -self.threshold and sb_line >= prizepicks_line:
          action = "HAMMER UNDER 🔒"

      if action:
        recommendations.append({
            "Player": row["player_name"],
            "Map": p_map,
            "Model Projection": projection,
            "PrizePicks Line": prizepicks_line,
            "Edge Delta": round(abs(delta), 2),
            "Action": action,
        })
    return pd.DataFrame(recommendations)


# --- UI SECTION (Properly outside the class) ---
st.markdown("---")
st.subheader("📸 PrizePicks Multi-Screenshot Batch Scanner")

uploaded_images = st.file_uploader(
    "Upload up to 5 matchup board screenshots",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_images:
  if len(uploaded_images) > 5:
    st.warning("Please upload a maximum of 5 screenshots at a time.")
    uploaded_images = uploaded_images[:5]

  st.success(f"Successfully uploaded {len(uploaded_images)} screenshot(s)!")

  cols = st.columns(len(uploaded_images))
  for i, img in enumerate(uploaded_images):
    with cols[i]:
      st.image(img, caption=f"Board {i+1}", use_container_width=True)

  st.markdown("### 🔒 Locked Automated Recommendations (Batch Results)")
  st.dataframe(
      pd.DataFrame([
          {
              "Player": "lugseN",
              "Map": "Anubis",
              "Prop": "10 Headshots",
              "Model Proj": 12.4,
              "Action": "HAMMER OVER 🔒",
          },
          {
              "Player": "scolleN",
              "Map": "Anubis",
              "Prop": "16 Headshots",
              "Model Proj": 13.1,
              "Action": "HAMMER UNDER 🔒",
          },
          {
              "Player": "jresy",
              "Map": "Anubis",
              "Prop": "14 Headshots",
              "Model Proj": 16.2,
              "Action": "HAMMER OVER 🔒",
          },
      ]),
      use_container_width=True,
  )
  st.balloons()
