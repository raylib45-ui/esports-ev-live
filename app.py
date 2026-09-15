import numpy as np
import pandas as pd

# ==========================================
# 1. MATCH CONFIGURATION & HISTORICAL DATA
# ==========================================
TEAM_FAV = "Nemiga"
TEAM_UNDERDOG = "BET-M"

# Active Lineups & Past 3-Month Rolling KPR / DPR / Map Stats
match_data = {
    "Nemiga": {
        "players": ["KaiR0N-", "khaN", "robo", "syph0", "Xant3r"],
        "kpr": [0.80, 0.73, 0.72, 0.69, 0.74],
        "dpr": [0.70, 0.71, 0.68, 0.67, 0.72],
        "map_win_rates": {
            "Mirage": 0.83,
            "Anubis": 0.75,
            "Dust2": 0.60,
            "Nuke": 0.64,
            "Ancient": 0.50,
        },
        "form_ranking": 39,
    },
    "BET-M": {
        "players": ["z1Nny", "synyx", "executor", "Raijin", "bluewh1te"],
        "kpr": [0.65, 0.64, 0.63, 0.66, 0.60],
        "dpr": [0.76, 0.77, 0.78, 0.75, 0.81],
        "map_win_rates": {
            "Mirage": 0.56,
            "Anubis": 0.67,
            "Dust2": 0.38,
            "Nuke": 0.54,
            "Ancient": 0.09,
        },
        "form_ranking": 77,
    },
}

# ==========================================
# 2. PROJECTION ENGINE (SIMULATION MODEL)
# ==========================================


class CS2PropModel:

  def __init__(self, data, target_maps=2, sims=10000):
    self.data = data
    self.target_maps = target_maps
    self.sims = sims

  def simulate_match_rounds(self):
    # Simulate average total rounds for a Bo3 match expected to sweep 2-0
    fav_wr = self.data[TEAM_FAV]["map_win_rates"]["Mirage"]
    dog_wr = self.data[TEAM_UNDERDOG]["map_win_rates"]["Dust2"]

    # Variance modifier based on rank disparity (Rank 39 vs 77)
    rank_diff_factor = (
        self.data[TEAM_UNDERDOG]["form_ranking"]
        - self.data[TEAM_FAV]["form_ranking"]
    )
    expected_rounds_map = np.random.normal(
        loc=21.5 - (rank_diff_factor * 0.03), scale=2.2, size=self.sims
    )
    return np.clip(expected_rounds_map * self.target_maps, 36, 52)

  def evaluate_props(self, player_lines):
    simulated_total_rounds = self.simulate_match_rounds()
    results = []

    for team_name, roster_dict in self.data.items():
      for i, player in enumerate(roster_dict["players"]):
        if player not in player_lines:
          continue

        line_value = player_lines[player]
        base_kpr = roster_dict["kpr"][i]

        # Monte Carlo simulation of player kills across series length
        player_sim_kills = np.array([
            np.random.poisson(base_kpr * r) for r in simulated_total_rounds
        ])

        # Strict Under/Over Filtering Rule Applied
        prob_under = np.mean(player_sim_kills < line_value)
        prob_over = np.mean(player_sim_kills > line_value)

        if prob_under >= 0.57:
          recommendation = "LESS (LOCK 🔒)"
          model_prob = prob_under
          proj_kills = np.mean(player_sim_kills)
        elif prob_over >= 0.57:
          recommendation = "MORE (LOCK 🔒)"
          model_prob = prob_over
          proj_kills = np.mean(player_sim_kills)
        else:
          recommendation = "PASS (High Variance)"
          model_prob = max(prob_under, prob_over)
          proj_kills = np.mean(player_sim_kills)

        results.append({
            "Team": team_name,
            "Player": player,
            "Line": line_value,
            "Proj Kills": round(proj_kills, 1),
            "Pick": recommendation,
            "Confidence": f"{round(model_prob * 100, 1)}%",
        })

    return pd.DataFrame(results)


# ==========================================
# 3. EXECUTION & OUTPUT GENERATION
# ==========================================
if __name__ == "__main__":
  # Current board lines pulled from the matchup screenshots
  active_board_lines = {
      "KaiR0N-": 33.5,
      "khaN": 31.5,
      "robo": 28.5,
      "syph0": 28.0,
      "Xant3r": 27.5,
      "z1Nny": 27.0,
      "synyx": 27.0,
      "executor": 29.0,
      "Raijin": 27.0,
      "bluewh1te": 25.0,
  }

  model = CS2PropModel(match_data)
  df_output = model.evaluate_props(active_board_lines)

  print("=== CS2 QUANTITATIVE PROJECTION MODEL OUTPUT ===")
  print(
      df_output.to_string(
          index=False, columns=["Team", "Player", "Line", "Proj Kills", "Pick", "Confidence"]
      )
  )
