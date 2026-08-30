import streamlit as st
import math

st.set_page_config(page_title="Esports EV Hub", layout="wide")
st.title("LCS Larry Model - Top 2 CS2 / Top 2 LoL / Top 2 VAL")

TITLE_CFG = {
    "CS2": {"sigma": 4.5, "base": 24, "ot": 28, "blowout": 0.60},
    "LoL": {"sigma": 1.8, "base": 3.0, "ot": 3.2, "blowout": 0.65},
    "VAL": {"sigma": 4.0, "base": 48, "ot": 55, "blowout": 0.60},
}

def calc_prob(line, mu, sigma):
    z = (line - mu) / sigma
    return 0.5 * (1 - math.erf(z / 1.4142))

st.sidebar.header("Add Board Lines")
player = st.sidebar.text_input("Player")
title = st.sidebar.selectbox("Title", ["CS2","LoL","VAL"])
line = st.sidebar.number_input("PrizePicks Line", value=31.5)
mu = st.sidebar.number_input("Your mu base", value=32.1)
winp = st.sidebar.slider("Favorite win prob", 0.4, 0.85, 0.52)
star = st.sidebar.checkbox("Star vs Tier2?")

if "board" not in st.session_state:
    st.session_state.board = []

if st.sidebar.button("Add to Pool"):
    cfg = TITLE_CFG[title]
    exp = cfg["ot"] if 0.48 <= winp <= 0.52 else cfg["base"] * (0.92 if winp >= cfg["blowout"] else 1.0)
    mu_adj = mu * (exp / cfg["base"]) + (3.5 if star else 0)
    prob_over = calc_prob(line, mu_adj, cfg["sigma"])
    lean = "MORE" if prob_over > 0.5 else "LESS"
    prob = prob_over if lean=="MORE" else 1-prob_over
    ev = prob*0.91 - (1-prob)
    st.session_state.board.append({"player":player,"title":title,"line":line,"mu_adj":mu_adj,"lean":lean,"prob":prob,"ev":ev})

if st.session_state.board:
    filtered = sorted([x for x in st.session_state.board if x["prob"]>=0.61 and x["ev"]>=0.09], key=lambda x: x["ev"], reverse=True)
    st.write(f"Pooled: {len(st.session_state.board)} | Edges: {len(filtered)}")
    for r in filtered[:6]:
        st.code(f"{r['player']} {r['line']} {r['lean']} {r['prob']:.1%} EV {r['ev']:.1%}")
    if st.button("Clear"):
        st.session_state.board = []