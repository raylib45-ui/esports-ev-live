import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="LCS Larry 2026", layout="wide")

class Engine:
    def __init__(self, data):
        self.data = data

    def process(self):
        res = []
        for i in self.data:
            sharp = round(i["line"] + np.random.choice([-1.0, -0.5, 0.5, 1.0]), 1)
            diff = sharp - i["line"]
            action = "🔨 MORE" if diff > 0 else "🔨 LESS"
            prob = round(np.random.uniform(0.55, 0.68) * 100, 1)
            ev = round((prob/100 * 1.65 - 1) * 100, 1)
            res.append({
                "Player": i["p"], "Match": i["m"], "Stat": i["s"],
                "PP Line": i["line"], "Sharp": sharp, "Hit%": prob, "EV%": ev, "Action": action
            })
        return pd.DataFrame(res)

if __name__ == "__main__":
    st.title("LCS Larry 2026: Quick Board")

    board = [
        {"p": "KaiRON-", "m": "vs HOTU", "s": "MAP 3 Kills", "line": 14.5},
        {"p": "Xant3r", "m": "vs HOTU", "s": "MAP 3 Kills", "line": 12.5},
        {"p": "demente", "m": "vs NOVAQ", "s": "MAPS 1-2 Kills", "line": 30.0},
        {"p": "dukefissura", "m": "vs NOVAQ", "s": "MAPS 1-2 Kills", "line": 27.5},
        {"p": "forkyz", "m": "vs NOVAQ", "s": "MAPS 1-2 Kills", "line": 28.5},
        {"p": "her1tage", "m": "vs NOVAQ", "s": "MAPS 1-2 Kills", "line": 27.5},
        {"p": "khaN", "m": "vs HOTU", "s": "MAP 3 Kills", "line": 15.0},
        {"p": "noni", "m": "vs NOVAQ", "s": "MAPS 1-2 Kills", "line": 28.5},
        {"p": "robo", "m": "vs HOTU", "s": "MAP 3 Kills", "line": 13.0},
        {"p": "syph0", "m": "vs HOTU", "s": "MAP 3 Kills", "line": 13.5},
        {"p": "dwushka", "m": "vs Nemiga", "s": "MAP 3 Kills", "line": 15.0},
        {"p": "frontales", "m": "vs Nemiga", "s": "MAP 3 Kills", "line": 15.5},
        {"p": "kadeO", "m": "vs Nemiga", "s": "MAP 3 Kills", "line": 13.0},
        {"p": "mizu", "m": "vs Nemiga", "s": "MAP 3 Kills", "line": 16.0},
        {"p": "n0rb3r7", "m": "vs Nemiga", "s": "MAP 3 Kills", "line": 15.0}
    ]

    df = Engine(board).process()
    st.dataframe(df, use_container_width=True)
