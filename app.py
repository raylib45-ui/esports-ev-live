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


uploaded_file = st.file_uploader("Upload Historical CS2 Match CSV", type=["csv"])
if uploaded_file is not None:
  df = pd.read_csv(uploaded_file)
  st.success("Dataset loaded successfully!")
  st.dataframe(df.head())
