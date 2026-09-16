import numpy as np
import pandas as pd


class CS2WeightedScanner:

  def __init__(self, historical_df, discrepancy_threshold=1.5):
    self.historical_data = historical_df
    self.threshold = discrepancy_threshold

  def calculate_tier1_efficiency(self, player_id, map_name):
    """Tier 1: Core Efficiency (~50% weight)

    Evaluates raw output independent of match outcomes.
    """
    df = self.historical_data[
        (self.historical_data["player_id"] == player_id)
        & (self.historical_data["map"] == map_name]
    ]
    if df.empty:
      return None, None, None

    base_kpr = df["kpr"].mean()
    base_adr = df["adr"].mean()
    base_impact = df["impact_rating"].mean()
    return base_kpr, base_adr, base_impact

  def calculate_tier2_volatility(self, player_id, map_name):
    """Tier 2: Role & Volatility (~30% weight)

    Measures opening duels and weapon economy dependence (AWP).
    """
    df = self.historical_data[
        (self.historical_data["player_id"] == player_id)
        & (self.historical_data["map"] == map_name]
    ]
    if df.empty:
      return 0.5, 0.0  # Default neutral win rate, zero AWP skew

    entry_win_rate = df["opening_duel_win_rate"].mean()
    awp_kpr = df["awp_kills_per_round"].mean()
    return entry_win_rate, awp_kpr

  def calculate_tier3_situational(self, player_id, map_name, opponent_id):
    """Tier 3: Situational Splits (~20% weight)

    Adjusts for CT/T side dynamics and opponent strength of schedule.
    """
    # Simplified modifier scaling based on opponent defensive tier and map side split
    return 1.05  # Example modifier multiplier (e.g., favorable matchup)

  def generate_projection(
      self, player_id, map_name, opponent_id, projected_rounds
  ):
    """Executes the multi-tiered weighted formula to find Expected Kills."""
    # 1. Tier 1 Metrics
    kpr, adr, impact = self.calculate_tier1_efficiency(player_id, map_name)
    if kpr is None:
      return None

    # Normalize ADR and Impact for formula integration (scaling metrics roughly to KPR scale)
    norm_adr = adr / 100.0
    norm_impact = impact / 1.5

    # 2. Tier 2 Metrics
    entry_win_rate, awp_kpr = self.calculate_tier2_volatility(player_id, map_name)

    # 3. Tier 3 Modifiers
    situational_modifier = self.calculate_tier3_situational(
        player_id, map_name, opponent_id
    )

    # Weighted Formula Combination ( mirroring your images )
    # Tier 1 (50% aggregate influence split across KPR, ADR, Impact)
    tier_1_score = (0.40 * kpr) + (0.35 * norm_adr) + (0.25 * norm_impact)

    # Tier 2 (30% aggregate influence split across Opening Duels and AWP economy)
    tier_2_score = (0.70 * entry_win_rate * kpr) + (0.30 * awp_kpr)

    # Combine Tiers with Tier 3 Situational Modifier applied dynamically
    kpr_exp = ((0.50 * tier_1_score) + (0.30 * tier_2_score)) * (
        situational_modifier
    )

    # Final baseline projection = Expected KPR multiplied by estimated total rounds
    expected_kills = kpr_exp * projected_rounds
    return round(expected_kills, 2)

  def scan_and_hammer(self, board_df, sportsbook_df):
    """Automates lines comparison and enforces STRICT hammer-only over/under logic."""
    recommendations = []

    for _, row in board_df.iterrows():
      p_id = row["player_id"]
      p_map = row["map"]
      prizepicks_line = row["line"]
      proj_rounds = row["projected_rounds"]

      # Run Model Calculation
      projection = self.generate_projection(
          p_id, p_map, row["opponent_id"], proj_rounds
      )
      if projection is None:
        continue

      delta = projection - prizepicks_line

      # Cross-reference major sportsbooks for consensus check
      sb_line = self.get_sportsbook_line(sportsbook_df, p_id)

      action = None
      # Strict automated execution: Only hammer if discrepancy clears threshold
      # AND major sportsbooks agree on the directional movement.
      if delta >= self.line_threshold and sb_line <= prizepicks_line:
        action = "HAMMER OVER 🔒 (Consistent Over)"
      elif delta <= -self.line_threshold and sb_line >= prizepicks_line:
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

  def get_sportsbook_line(self, odds_df, player_id):
    match = odds_df[odds_df["player_id"] == player_id]
    if not match.empty:
      return match["consensus_line"].values[0]
    return np.nan
