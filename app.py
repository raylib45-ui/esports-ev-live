import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")

st.title("🏦 LCSLarry Esports Model - CS2 Cache Patch Edition")
st.caption("Premier Season 5 - Opening Lines & Value Scanner")

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

picks_board = [
    {"player": "Annihilation", "team": "The Huns", "match": "The Huns vs Staqued", "line": 32.5, "mu": apply_cache_patch(38.0, "entry", ["Cache","Nuke"]), "role": "entry", "maps_likely": ["Nuke","Anubis","Cache"]},
    {"player": "balencyy", "team": "Gremio", "match": "Gremio vs ODDIK", "line": 27.5, "mu": apply_cache_patch(30.5, "anchor_B", ["Inferno","Cache"]), "role": "anchor_B", "maps_likely": ["Inferno","Cache"]},
    {"player": "jared", "team": "Chicken Coop", "match": "Chicken Coop vs Overtake", "line": 30.0, "mu": apply_cache_patch(33.0, "entry", ["Mirage","Anubis"]), "role": "entry", "maps_likely": ["Mirage","Anubis"]},
    {"player": "donk", "team": "Spirit", "match": "Spirit vs FURIA", "line": 39.5, "mu": apply_cache_patch(42.0, "entry", ["Cache","Anubis"]), "role": "entry", "maps_likely": ["Anubis","Cache"]},
    {"player": "junior", "team": "Voca", "match": "Voca vs Marsborne", "line": 31.5, "mu": apply_cache_patch(35.0, "entry", ["Dust2"]), "role": "entry", "maps_likely": ["Dust2","Mirage"]},
    {"player": "cadnyx", "team": "Bushido", "match": "Bushido vs ex-RUSTEC", "line": 30.5, "mu": apply_cache_patch(33.5, "anchor_A", ["Cache"]), "role": "anchor_A", "maps_likely": ["Cache","Inferno"]},
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
