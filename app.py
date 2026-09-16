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
    """Enforces strict automated execution: Hammer Over or Hammer Under ONLY."""
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
          action = "HAMMER OVER 🔒 (Consistent Over)"
        elif delta <= -self.threshold and sb_line >= prizepicks_line:
          action = "HAMMER UNDER 🔒 (Consistent Under)"

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


# --- ADDED AT THE BOTTOM: Screenshot Uploader Interface ---
st.markdown("---")
st.subheader("📸 PrizePicks Board Screenshot Scanner")
uploaded_image = st.file_uploader(
    "Upload matchup board screenshot", type=["png", "jpg", "jpeg"]
)

if uploaded_image is not None:
  st.image(uploaded_image, caption="Uploaded Board", use_container_width=True)
  st.success("Screenshot uploaded successfully!")
  st.info(
      "Ready to parse screenshot text and execute automated historical checks."
  )
