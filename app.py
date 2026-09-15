import numpy as np
import pandas as pd
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="CS2 Quantitative Projection Model", page_icon="📊", layout="wide"
)

st.title("🎯 CS2 Quantitative Matchup & Prop Projection Engine")
st.markdown("### Active Board Scans | Multiple Matchups")

# ==========================================
# 1. NEW MATCH CONFIGURATIONS & BOARD LINES
# ==========================================
match_board_data = {
    # SPARTA vs BAKS
    "glowling": {"team": "SPARTA", "opp": "BAKS", "line": 32.0, "base_kpr": 0.78},
    "Eltan": {"team": "SPARTA", "opp": "BAKS", "line": 31.0, "base_kpr": 0.75},
    "TRAVIS": {"team": "SPARTA", "opp": "BAKS", "line": 30.5, "base_kpr": 0.73},
    "interz": {"team": "SPARTA", "opp": "BAKS", "line": 25.5, "base_kpr": 0.62},
    "NickelBack": {
        "team": "SPARTA",
        "opp": "BAKS",
        "line": 25.5,
        "base_kpr": 0.61,
    },
    "whisper": {"team": "BAKS", "opp": "SPARTA", "line": 30.0, "base_kpr": 0.72},
    "turbo": {"team": "BAKS", "opp": "SPARTA", "line": 28.5, "base_kpr": 0.68},
    "Norwi": {"team": "BAKS", "opp": "SPARTA", "line": 27.5, "base_kpr": 0.66},
    "danistzz": {"team": "BAKS", "opp": "SPARTA", "line": 27.5, "base_kpr": 0.65},
    "xDENISZERA": {
        "team": "BAKS",
        "opp": "SPARTA",
        "line": 27.0,
        "base_kpr": 0.64,
    },
    # ex-Zero Tenacity vs Teletubisie
    "Dragon": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 30.5,
        "base_kpr": 0.74,
    },
    "VLDN": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 29.5,
        "base_kpr": 0.71,
    },
    "Kind0": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 28.5,
        "base_kpr": 0.69,
    },
    "brutmonster": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 29.5,
        "base_kpr": 0.70,
    },
    "Cjoffo": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 30.5,
        "base_kpr": 0.73,
    },
    # ALKA vs Turma do Pagode
    "bnc": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 28.5,
        "base_kpr": 0.68,
    },
    "cerolzin": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 27.5,
        "base_kpr": 0.66,
    },
    "puni": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 24.5,
        "base_kpr": 0.58,
    },
    "vinaabEAST": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 28.5,
        "base_kpr": 0.68,
    },
    "proSHOW": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 31.5,
        "base_kpr": 0.76,
    },
    "WOOD7": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 25.5,
        "base_kpr": 0.61,
    },
    "naitte": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 31.5,
        "base_kpr": 0.75,
    },
    "ksloks": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 31.5,
        "base_kpr": 0.75,
    },
    "Tuurtle": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 31.0,
        "base_kpr": 0.74,
    },
    # QUAZAR vs ex-RUSTEC
    "Ne1XXX": {
        "team": "QUAZAR",
        "opp": "ex-RUSTEC",
        "line": 31.5,
        "base_kpr": 0.76,
    },
    "kalori": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 30.5, "base_kpr": 0.73},
    "gehji": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 30.5, "base_kpr": 0.73},
    "Porya": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 29.5, "base_kpr": 0.70},
    "newt": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 28.5, "base_kpr": 0.68},
    "yiksrezo": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 32.5,
        "base_kpr": 0.79,
    },
    "youka": {"team": "ex-RUSTEC", "opp": "QUAZAR", "line": 32.5, "base_kpr": 0.78},
    "KIRO": {"team": "ex-RUSTEC", "opp": "QUAZAR", "line": 29.5, "base_kpr": 0.71},
    "Brilliance": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 26.5,
        "base_kpr": 0.63,
    },
    "jakekeS": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 26.5,
        "base_kpr": 0.63,
    },
    # UPGRADE vs PCIFIC
    "pleynnn": {"team": "UPGRADE", "opp": "PCIFIC", "line": 32.5, "base_kpr": 0.79},
    "dezl3bio": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 30.5,
        "base_kpr": 0.73,
    },
    "SquEzxc": {"team": "UPGRADE", "opp": "PCIFIC", "line": 29.5, "base_kpr": 0.71},
    "tw1sterzaza": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 29.0,
        "base_kpr": 0.69,
    },
    "DAN9ARMATURA": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 27.0,
        "base_kpr": 0.64,
    },
    "lugseN": {"team": "PCIFIC", "opp": "UPGRADE", "line": 30.0, "base_kpr": 0.72},
    "jresy": {"team": "PCIFIC", "opp": "UPGRADE", "line": 28.5, "base_kpr": 0.68},
    "scolleN": {"team": "PCIFIC", "opp": "UPGRADE", "line": 27.5, "base_kpr": 0.66},
    "oyesil": {"team": "PCIFIC", "opp": "UPGRADE", "line": 25.0, "base_kpr": 0.59},
    # ENCE vs Honved
    "joeski": {"team": "ENCE", "opp": "Honved", "line": 28.5, "base_kpr": 0.68},
    "Schwarz": {"team": "ENCE", "opp": "Honved", "line": 28.5, "base_kpr": 0.68},
    "teme": {"team": "ENCE", "opp": "Honved", "line": 27.5, "base_kpr": 0.66},
    "millert": {"team": "ENCE", "opp": "Honved", "line": 28.5, "base_kpr": 0.68},
    "HENU": {"team": "ENCE", "opp": "Honved", "line": 30.5, "base_kpr": 0.73},
    # Bounty Hunters vs Yawara
    "pepe": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 28.5,
        "base_kpr": 0.68,
    },
    "urban0": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 28.5,
        "base_kpr": 0.68,
    },
    "ponter": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 27.5,
        "base_kpr": 0.66,
    },
    "zock": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 29.5,
        "base_kpr": 0.71,
    },
    "KAISER": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 28.5,
        "base_kpr": 0.68,
    },
}

# ==========================================
# 2. SIMULATION & EVALUATION LOGIC
# ==========================================


class MultiMatchPropModel:

  def __init__(self, board_data, sims=5000):
    self.board_data = board_data
    self.sims = sims

  def evaluate_props(self):
    results = []

    for player, info in self.board_data.items():
      line_value = info["line"]
      base_kpr = info["base_kpr"]

      # Simulate standard series total rounds (~40 rounds for a 2-map series)
      simulated_total_rounds = np.random.normal(
          loc=40.0, scale=3.5, size=self.sims
      )
      simulated_total_rounds = np.clip(simulated_total_rounds, 26, 54)

      player_sim_kills = np.array([
          np.random.poisson(base_kpr * r) for r in simulated_total_rounds
      ])

      prob_under = np.mean(player_sim_kills < line_value)
      prob_over = np.mean(player_sim_kills > line_value)

      # Strict Under/Over Filtering Rule Applied (Consistently under or over only)
      if prob_under >= 0.58:
        recommendation = "LESS (LOCK 🔒)"
        model_prob = prob_under
      elif prob_over >= 0.58:
        recommendation = "MORE (LOCK 🔒)"
        model_prob = prob_over
      else:
        recommendation = "PASS (Variance Too High)"
        model_prob = max(prob_under, prob_over)

      proj_kills = np.mean(player_sim_kills)

      results.append({
          "Team": info["team"],
          "Opponent": info["opp"],
          "Player": player,
          "Line": line_value,
          "Proj Kills": round(proj_kills, 1),
          "Discrepancy": round(proj_kills - line_value, 1),
          "Pick": recommendation,
          "Confidence": f"{round(model_prob * 100, 1)}%",
      })

    df = pd.DataFrame(results)
    df["Abs_Edge"] = df["Discrepancy"].abs()
    df = df.sort_values(by="Abs_Edge", ascending=False).drop(
        columns=["Abs_Edge"]
    )
    return df


# ==========================================
# 3. RENDER STREAMLIT INTERFACE
# ==========================================
model = MultiMatchPropModel(match_board_data)
df_output = model.evaluate_props()

st.success(
    "Successfully loaded all new players and cleared previous rosters!"
)
st.dataframe(df_output, use_container_width=True)
