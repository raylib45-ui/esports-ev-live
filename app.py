import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")

st.title("🏦 LCSLarry Esports Model - CS2 Cache Patch Edition")
st.caption("Premier Season 5 - Maps 1-2 Kills Live Dabble Board Scanner")

# --- CONFIG ---
SIGMA_BASE = 4.5  # MAPS 1-2 Kills
SIGMA_CACHE = 4.8  # high variance on Cache
MIN_EDGE_PCT = 0.06  # >6% discrepancy
MIN_PROB = 0.61  # >61% bucket (no 54-56% forcing)
MAX_PER_TEAM = 1
MAX_PER_MATCH = 2  # if Cache in pool, treat as 1
MAX_PER_MATCH_CACHE = 1

PATCH = {
    "mid_duels": 1.5,
    "self_boost_A": 0.8,
    "ebox_checkers": 1.0,
    "post_plant_smoke_molly": 1.5,
    "awp_save_buff": 1.0,
    "exit_frag_nerf": -0.5,
}

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def apply_cache_patch(mu, role, maps_likely):
    adj = PATCH.get("post_plant_smoke_molly", 1.5)
    if role in ["entry", "rifler_star"]:
        adj += PATCH.get("mid_duels", 1.5)
    if role in ["anchor_A", "awp"]:
        adj += PATCH.get("self_boost_A", 0.8) + PATCH.get("awp_save_buff", 1.0)
    if role == "anchor_B":
        adj += PATCH.get("ebox_checkers", 1.0)
    if "Cache" in maps_likely:
        adj += 0.5
    return mu + adj

def calc_prob(mu, line, sigma, side="OVER"):
    z = (line - mu) / sigma
    prob_over = 1 - norm_cdf(z)
    prob_under = norm_cdf(z)
    return prob_over if side == "OVER" else prob_under

def calc_edge(mu, line, sigma, side="OVER"):
    if line <= 0:
        return 0.0, 0.0
    prob = calc_prob(mu, line, sigma, side)
    if side == "OVER":
        gap_pct = (mu - line) / line
    else:
        gap_pct = (line - mu) / line
    return gap_pct, prob

def filter_picks(picks):
    valid = []
    for p in picks:
        sigma = SIGMA_CACHE if "Cache" in p["maps_likely"] else SIGMA_BASE
        gap_over, prob_over = calc_edge(p["mu"], p["line"], sigma, "OVER")
        gap_under, prob_under = calc_edge(p["mu"], p["line"], sigma, "UNDER")

        if gap_over >= MIN_EDGE_PCT and prob_over >= MIN_PROB:
            p["side"] = "OVER"
            p["prob"] = prob_over
            p["edge"] = gap_over
            p["sigma"] = sigma
            valid.append(p)
        elif gap_under >= MIN_EDGE_PCT and prob_under >= MIN_PROB:
            p["side"] = "UNDER"
            p["prob"] = prob_under
            p["edge"] = gap_under
            p["sigma"] = sigma
            valid.append(p)

    valid.sort(key=lambda x: (x["edge"] * x["prob"]), reverse=True)

    selected = []
    team_count = {}
    match_count = {}

    for p in valid:
        t = p["team"]
        m = p["match"]
        if team_count.get(t, 0) >= MAX_PER_TEAM:
            continue
        max_match = MAX_PER_MATCH_CACHE if "Cache" in p["maps_likely"] else MAX_PER_MATCH
        if match_count.get(m, 0) >= max_match:
            continue
        selected.append(p)
        team_count[t] = team_count.get(t, 0) + 1
        match_count[m] = match_count.get(m, 0) + 1
        if len(selected) == 6:
            break
    return selected

# Complete Live Dabble Board (Parsed from screenshots)
picks_board = [
    # Match: Borracheiros vs ALKA
    {"player": "zock9", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 28.5, "mu": apply_cache_patch(33.0, "entry", ["Cache", "Anubis"]), "role": "entry", "maps_likely": ["Cache", "Anubis"]},
    {"player": "neozix", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 26.5, "mu": apply_cache_patch(30.0, "support", ["Cache", "Inferno"]), "role": "support", "maps_likely": ["Cache", "Inferno"]},
    {"player": "trindade", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 28.5, "mu": apply_cache_patch(32.5, "anchor_A", ["Cache", "Mirage"]), "role": "anchor_A", "maps_likely": ["Cache", "Mirage"]},
    {"player": "Lacerda", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 26.5, "mu": apply_cache_patch(31.0, "entry", ["Cache", "Dust2"]), "role": "entry", "maps_likely": ["Cache", "Dust2"]},
    {"player": "puni", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 25.5, "mu": apply_cache_patch(29.5, "rifler_star", ["Cache", "Nuke"]), "role": "rifler_star", "maps_likely": ["Cache", "Nuke"]},
    {"player": "proSHOW", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 30.5, "mu": apply_cache_patch(35.0, "entry", ["Cache", "Anubis"]), "role": "entry", "maps_likely": ["Cache", "Anubis"]},
    {"player": "vinaabEAST", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 29.5, "mu": apply_cache_patch(34.0, "anchor_B", ["Cache", "Inferno"]), "role": "anchor_B", "maps_likely": ["Cache", "Inferno"]},
    {"player": "cerolzin", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 27.5, "mu": apply_cache_patch(31.5, "rifler_star", ["Cache", "Mirage"]), "role": "rifler_star", "maps_likely": ["Cache", "Mirage"]},
    {"player": "bnc", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 29.5, "mu": apply_cache_patch(34.0, "entry", ["Cache", "Dust2"]), "role": "entry", "maps_likely": ["Cache", "Dust2"]},

    # Match: Nuclear TigerES vs Color
    {"player": "z1k4", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 32.0, "mu": apply_cache_patch(36.5, "entry", ["Dust2", "Mirage"]), "role": "entry", "maps_likely": ["Dust2", "Mirage"]},
    {"player": "flouzer", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 31.0, "mu": apply_cache_patch(35.5, "rifler_star", ["Dust2", "Ancient"]), "role": "rifler_star", "maps_likely": ["Dust2", "Ancient"]},
    {"player": "ayuki", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 30.0, "mu": apply_cache_patch(25.5, "support", ["Dust2", "Mirage"]), "role": "support", "maps_likely": ["Dust2", "Mirage"]}, # Under lean
    {"player": "m1QUSE", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(34.0, "entry", ["Dust2", "Inferno"]), "role": "entry", "maps_likely": ["Dust2", "Inferno"]},
    {"player": "senka", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 25.5, "mu": apply_cache_patch(30.0, "support", ["Dust2", "Nuke"]), "role": "support", "maps_likely": ["Dust2", "Nuke"]},
    {"player": "lattykk", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 31.5, "mu": apply_cache_patch(36.0, "rifler_star", ["Mirage", "Dust2"]), "role": "rifler_star", "maps_likely": ["Mirage", "Dust2"]},
    {"player": "cronuss", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(25.0, "support", ["Mirage", "Anubis"]), "role": "support", "maps_likely": ["Mirage", "Anubis"]}, # Under lean
    {"player": "Ryujin", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(34.0, "entry", ["Mirage", "Inferno"]), "role": "entry", "maps_likely": ["Mirage", "Inferno"]},
    {"player": "oz1k", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 26.5, "mu": apply_cache_patch(30.5, "anchor_A", ["Mirage", "Nuke"]), "role": "anchor_A", "maps_likely": ["Mirage", "Nuke"]},
    {"player": "reyoz", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 26.0, "mu": apply_cache_patch(22.0, "support", ["Mirage", "Dust2"]), "role": "support", "maps_likely": ["Mirage", "Dust2"]}, # Under lean

    # Match: Grêmio vs paiN Academy
    {"player": "MITHPUTTINI", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(33.0, "entry", ["Inferno", "Mirage"]), "role": "entry", "maps_likely": ["Inferno", "Mirage"]},
    {"player": "yeda", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 27.5, "mu": apply_cache_patch(32.0, "rifler_star", ["Inferno", "Dust2"]), "role": "rifler_star", "maps_likely": ["Inferno", "Dust2"]},
    {"player": "balencyy", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 31.5, "mu": apply_cache_patch(36.0, "anchor_B", ["Inferno", "Cache"]), "role": "anchor_B", "maps_likely": ["Inferno", "Cache"]},
    {"player": "s1lent", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(33.0, "support", ["Inferno", "Anubis"]), "role": "support", "maps_likely": ["Inferno", "Anubis"]},
    {"player": "souz4h", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(33.0, "entry", ["Inferno", "Nuke"]), "role": "entry", "maps_likely": ["Inferno", "Nuke"]},

    # Match: Tyloo vs Kaleido Gaming
    {"player": "Moseyuh", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.5, "mu": apply_cache_patch(33.0, "entry", ["Ancient", "Anubis"]), "role": "entry", "maps_likely": ["Ancient", "Anubis"]},
    {"player": "Jee", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 30.0, "mu": apply_cache_patch(35.0, "awp", ["Ancient", "Mirage"]), "role": "awp", "maps_likely": ["Ancient", "Mirage"]},
    {"player": "Zero", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.5, "mu": apply_cache_patch(33.0, "support", ["Ancient", "Inferno"]), "role": "support", "maps_likely": ["Ancient", "Inferno"]},
    {"player": "JamYoung", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 31.0, "mu": apply_cache_patch(36.5, "rifler_star", ["Ancient", "Dust2"]), "role": "rifler_star", "maps_likely": ["Ancient", "Dust2"]},
    {"player": "Mercury", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.0, "mu": apply_cache_patch(32.5, "entry", ["Ancient", "Nuke"]), "role": "entry", "maps_likely": ["Ancient", "Nuke"]},

    # Match: Rare Atom vs Lynn Vision
    {"player": "ChildKing", "team": "Rare Atom", "match": "Rare Atom vs Lynn Vision", "line": 27.5, "mu": apply_cache_patch(32.0, "rifler_star", ["Anubis", "Inferno"]), "role": "rifler_star", "maps_likely": ["Anubis", "Inferno"]}
]

best6 = filter_picks(picks_board)

st.subheader("🔥 Top Filtered Portal Cards")

if not best6:
    st.info("No picks met the strict model criteria for this slate.")
else:
    for b in best6:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{b['player']}** ({b['team']})  \n*Match:* {b['match']}")
            with col2:
                st.markdown(f"**Side:** `{b['side']}`  \n**Line:** {b['line']}")
            with col3:
                st.metric(label="Model Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}% Edge")
            st.markdown("---")
