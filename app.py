import numpy as np
import pandas as pd
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="CS2 Headshots Quantitative Model", page_icon="🎯", layout="wide"
)

st.title("🎯 CS2 Quantitative Matchup & Headshots Projection Engine")
st.markdown("### Active Board Scans | Maps 1-2 Headshots")

# ==========================================
# 1. NEW HEADSHOTS BOARD CONFIGURATIONS
# ==========================================
match_board_data = {
    # SPARTA vs BAKS
    "glowling": {"team": "SPARTA", "opp": "BAKS", "line": 18.5, "base_hpr": 0.42},
    "Eltan": {"team": "SPARTA", "opp": "BAKS", "line": 9.0, "base_hpr": 0.22},
    "TRAVIS": {"team": "SPARTA", "opp": "BAKS", "line": 17.5, "base_hpr": 0.39},
    "interz": {"team": "SPARTA", "opp": "BAKS", "line": 13.5, "base_hpr": 0.31},
    "NickelBack": {
        "team": "SPARTA",
        "opp": "BAKS",
        "line": 13.0,
        "base_hpr": 0.30,
    },
    "whisper": {"team": "BAKS", "opp": "SPARTA", "line": 18.5, "base_hpr": 0.41},
    "turbo": {"team": "BAKS", "opp": "SPARTA", "line": 18.5, "base_hpr": 0.41},
    "Norwi": {"team": "BAKS", "opp": "SPARTA", "line": 13.0, "base_hpr": 0.30},
    "danistzz": {"team": "BAKS", "opp": "SPARTA", "line": 10.5, "base_hpr": 0.25},
    "xDENISZERA": {
        "team": "BAKS",
        "opp": "SPARTA",
        "line": 14.0,
        "base_hpr": 0.32,
    },
    # ex-Zero Tenacity vs Teletubisie
    "Dragon": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "VLDN": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "Kind0": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 13.5,
        "base_hpr": 0.31,
    },
    "Cjoffo": {
        "team": "ex-Zero Tenacity",
        "opp": "Teletubisie",
        "line": 17.5,
        "base_hpr": 0.39,
    },
    # ALKA vs Turma do Pagode
    "bnc": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 14.5,
        "base_hpr": 0.33,
    },
    "cerolzin": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 14.0,
        "base_hpr": 0.32,
    },
    "puni": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 13.5,
        "base_hpr": 0.31,
    },
    "vinaabEAST": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "proSHOW": {
        "team": "ALKA",
        "opp": "Turma do Pagode",
        "line": 10.5,
        "base_hpr": 0.25,
    },
    "naitte": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 17.5,
        "base_hpr": 0.39,
    },
    "ksloks": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 17.5,
        "base_hpr": 0.39,
    },
    "Tuurtle": {
        "team": "Turma do Pagode",
        "opp": "ALKA",
        "line": 17.0,
        "base_hpr": 0.38,
    },
    # QUAZAR vs ex-RUSTEC
    "Ne1XXX": {
        "team": "QUAZAR",
        "opp": "ex-RUSTEC",
        "line": 20.5,
        "base_hpr": 0.46,
    },
    "kalori": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 14.5, "base_hpr": 0.33},
    "gehji": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 17.5, "base_hpr": 0.39},
    "Porya": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 17.5, "base_hpr": 0.39},
    "newt": {"team": "QUAZAR", "opp": "ex-RUSTEC", "line": 18.5, "base_hpr": 0.41},
    "yiksrezo": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 21.5,
        "base_hpr": 0.48,
    },
    "youka": {"team": "ex-RUSTEC", "opp": "QUAZAR", "line": 11.5, "base_hpr": 0.27},
    "KIRO": {"team": "ex-RUSTEC", "opp": "QUAZAR", "line": 17.5, "base_hpr": 0.39},
    "Brilliance": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "jakekeS": {
        "team": "ex-RUSTEC",
        "opp": "QUAZAR",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    # UPGRADE vs PCIFIC
    "pleynnn": {"team": "UPGRADE", "opp": "PCIFIC", "line": 19.5, "base_hpr": 0.44},
    "dezl3bio": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 17.5,
        "base_hpr": 0.39,
    },
    "SquEzxc": {"team": "UPGRADE", "opp": "PCIFIC", "line": 10.0, "base_hpr": 0.24},
    "tw1sterzaza": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 14.5,
        "base_hpr": 0.33,
    },
    "DAN9ARMATURA": {
        "team": "UPGRADE",
        "opp": "PCIFIC",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "lugseN": {"team": "PCIFIC", "opp": "UPGRADE", "line": 10.0, "base_hpr": 0.24},
    "jresy": {"team": "PCIFIC", "opp": "UPGRADE", "line": 14.0, "base_hpr": 0.32},
    "scolleN": {"team": "PCIFIC", "opp": "UPGRADE", "line": 16.0, "base_hpr": 0.36},
    "oyesil": {"team": "PCIFIC", "opp": "UPGRADE", "line": 15.5, "base_hpr": 0.35},
    # ENCE vs Honved
    "joeski": {"team": "ENCE", "opp": "Honved", "line": 15.5, "base_hpr": 0.35},
    "Schwarz": {"team": "ENCE", "opp": "Honved", "line": 17.0, "base_hpr": 0.38},
    "teme": {"team": "ENCE", "opp": "Honved", "line": 15.5, "base_hpr": 0.35},
    "HENU": {"team": "ENCE", "opp": "Honved", "line": 16.5, "base_hpr": 0.37},
    # Bounty Hunters vs Yawara
    "pepe": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 17.5,
        "base_hpr": 0.39,
    },
    "urban0": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 17.0,
        "base_hpr": 0.38,
    },
    "ponter": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 16.5,
        "base_hpr": 0.37,
    },
    "zock": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 15.5,
        "base_hpr": 0.35,
    },
    "KAISER": {
        "team": "Bounty Hunters",
        "opp": "Yawara",
        "line": 12.0,
        "base_hpr": 0.28,
    },
}

# ==========================================
# 2. SIMULATION & EVALUATION LOGIC
# ==========================================


class HeadshotsPropModel:

  def __init__(self, board_data, sims=5000):
    self.board_data = board_data
    self.sims = sims

  def evaluate_props(self):
    results = []

    for player, info in self.board_data.items():
      line_value = info["line"]
      base_hpr = info["base_hpr"]

      simulated_total_rounds = np.random.normal(
          loc=40.0, scale=3.5, size=self.sims
      )
      simulated_total_rounds = np.clip(simulated_total_rounds, 26, 54)

      player_sim_hs = np.array([
          np.random.poisson(base_hpr * r) for r in simulated_total_rounds
      ])

      prob_under = np.mean(player_sim_hs < line_value)
      prob_over = np.mean(player_sim_hs > line_value)

      if prob_under >= 0.58:
        recommendation = "LESS (LOCK 🔒)"
        model_prob = prob_under
      elif prob_over >= 0.58:
        recommendation = "MORE (LOCK 🔒)"
        model_prob = prob_over
      else:
        recommendation = "PASS (Variance Too High)"
        model_prob = max(prob_under, prob_over)

      proj_hs = np.mean(player_sim_hs)

      results.append({
          "Team": info["team"],
          "Opponent": info["opp"],
          "Player": player,
          "Line": line_value,
          "Proj Headshots": round(proj_hs, 1),
          "Discrepancy": round(proj_hs - line_value, 1),
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
model = HeadshotsPropModel(match_board_data)
df_output = model.evaluate_props()

st.success("Successfully loaded all Headshots board data and cleared old lines!")
st.dataframe(df_output, use_container_width=True)
