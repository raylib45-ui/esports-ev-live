import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")

st.title("🏦 LCSLarry Esports Model - 24/7 Sharp Discrepancy & Hammer Engine")
st.caption("Premier Season 5 - Maps 1-2 Kills Real-Time Scanner (PrizePicks vs. DraftKings, bet365 & GG.BET)")

# --- CONFIG ---
SIGMA_BASE = 4.5  
SIGMA_CACHE = 4.8  
MIN_EDGE_PCT = 0.04  
MIN_PROB = 0.58  
MAX_PER_TEAM = 1
MAX_PER_MATCH = 2 
MAX_PER_MATCH_CACHE = 1

PATCH = {
    "mid_duels": 1.5,
    "self_boost_A": 0.8,
    "ebox_checkers": 1.0,
    "post_plant_smoke_molly": 1.5,
    "awp_save_buff": 1.0,
    "exit_frag_nerf": -1.5,
}

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def apply_cache_patch(base_val, role, maps_likely, side_lean="OVER"):
    adj = PATCH.get("post_plant_smoke_molly", 1.5)
    if role in ["entry", "rifler_star"]:
        adj += PATCH.get("mid_duels", 1.5)
    if role in ["anchor_A", "awp"]:
        adj += PATCH.get("self_boost_A", 0.8) + PATCH.get("awp_save_buff", 1.0)
    if role == "anchor_B":
        adj += PATCH.get("ebox_checkers", 1.0)
    if "Cache" in maps_likely:
        adj += 0.5
    if side_lean == "UNDER":
        return max(10.0, base_val - abs(adj) - 1.5)
    return base_val + adj

def calc_prob(mu, line, sigma, side="OVER"):
    z = (line - mu) / sigma
    return 1 - norm_cdf(z) if side == "OVER" else norm_cdf(z)

def calc_edge(mu, line, sigma, side="OVER"):
    if line <= 0:
        return 0.0, 0.0
    prob = calc_prob(mu, line, sigma, side)
    gap_pct = (mu - line) / line if side == "OVER" else (line - mu) / line
    return gap_pct, prob

def filter_picks(picks):
    valid = []
    for p in picks:
        sigma = SIGMA_CACHE if "Cache" in p["maps_likely"] else SIGMA_BASE
        gap_over, prob_over = calc_edge(p["mu"], p["line"], sigma, "OVER")
        gap_under, prob_under = calc_edge(p["mu"], p["line"], sigma, "UNDER")

        if p.get("forced_side") == "UNDER" and gap_under >= MIN_EDGE_PCT and prob_under >= MIN_PROB:
            p.update({"side": "UNDER", "prob": prob_under, "edge": gap_under, "sigma": sigma})
            valid.append(p)
        elif p.get("forced_side") == "OVER" and gap_over >= MIN_EDGE_PCT and prob_over >= MIN_PROB:
            p.update({"side": "OVER", "prob": prob_over, "edge": gap_over, "sigma": sigma})
            valid.append(p)
        elif not p.get("forced_side"):
            if gap_over >= MIN_EDGE_PCT and prob_over >= MIN_PROB:
                p.update({"side": "OVER", "prob": prob_over, "edge": gap_over, "sigma": sigma})
                valid.append(p)
            elif gap_under >= MIN_EDGE_PCT and prob_under >= MIN_PROB:
                p.update({"side": "UNDER", "prob": prob_under, "edge": gap_under, "sigma": sigma})
                valid.append(p)

    valid.sort(key=lambda x: (x["edge"] * x["prob"]), reverse=True)
    selected, team_count, match_count = [], {}, {}

    for p in valid:
        t, m = p["team"], p["match"]
        if team_count.get(t, 0) >= MAX_PER_TEAM:
            continue
        max_m = MAX_PER_MATCH_CACHE if "Cache" in p["maps_likely"] else MAX_PER_MATCH
        if match_count.get(m, 0) >= max_m:
            continue
        selected.append(p)
        team_count[t] = team_count.get(t, 0) + 1
        match_count[m] = match_count.get(m, 0) + 1
        if len(selected) == 6:
            break
    return selected

picks_board = []
best6 = filter_picks(picks_board)

st.subheader("🔥 24/7 Live Scanner: Dabble vs. PrizePicks & Sharp Books")

if not best6:
    st.info("No active lines loaded in picks_board.")
else:
    for b in best6:
        pp_diff = b['line'] - b['prizepicks_line']
        dk_diff = b['line'] - b['draftkings_line']
        b365_diff = b['line'] - b['bet365_line']
        gg_diff = b['line'] - b['ggbet_line']
        
        hammer_tag = None
        if b['side'] == 'OVER' and (pp_diff < 0 or dk_diff < 0 or b365_diff < 0 or gg_diff < 0):
            hammer_tag = "🔨 HAMMER MORE 🔨"
        elif b['side'] == 'UNDER' and (pp_diff > 0 or dk_diff > 0 or b365_diff > 0 or gg_diff > 0):
            hammer_tag = "🔨 HAMMER LESS 🔨"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{b['player']}** ({b['team']})  \n*{b['match']}*  \n**{hammer_tag or 'Standard Edge'}**")
            with col2:
                st.markdown(f"**Side:** `{b['side']}` | **Line:** {b['line']}  \n*PP:* {b['prizepicks_line']} | *DK:* {b['draftkings_line']}")
            with col3:
                st.metric(label="Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}%")
            st.markdown("---")
