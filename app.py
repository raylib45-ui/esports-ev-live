import math
import streamlit as st

st.set_page_config(page_title="LCSLarry CS2 Model", page_icon="🏦", layout="wide")

st.title("🏦 LCSLarry Esports Model - CS2 Cache Patch Edition")
st.caption("Premier Season 5 - Maps 1-2 Kills Live Dabble Board Scanner")

# --- CONFIG ---
SIGMA_BASE = 4.5  # MAPS 1-2 Kills
SIGMA_CACHE = 4.8  # high variance on Cache
MIN_EDGE_PCT = 0.06  # >6% discrepancy
MIN_PROB = 0.61  # >61% bucket
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

        if p.get("forced_side") == "UNDER":
            if gap_under >= MIN_EDGE_PCT and prob_under >= MIN_PROB:
                p["side"] = "UNDER"
                p["prob"] = prob_under
                p["edge"] = gap_under
                p["sigma"] = sigma
                valid.append(p)
        elif p.get("forced_side") == "OVER":
            if gap_over >= MIN_EDGE_PCT and prob_over >= MIN_PROB:
                p["side"] = "OVER"
                p["prob"] = prob_over
                p["edge"] = gap_over
                p["sigma"] = sigma
                valid.append(p)
        else:
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

# Complete Live Dabble Board with Hammer Tags & Book Discrepancy Tracking
picks_board = [
    # Match: Borracheiros vs ALKA
    {"player": "zock9", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 28.5, "mu": apply_cache_patch(29.0, "entry", ["Cache", "Anubis"], "OVER"), "role": "entry", "maps_likely": ["Cache", "Anubis"], "forced_side": "OVER", "prizepicks_line": 29.5, "consensus_book_line": 29.0},
    {"player": "neozix", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 26.5, "mu": apply_cache_patch(23.0, "support", ["Cache", "Inferno"], "UNDER"), "role": "support", "maps_likely": ["Cache", "Inferno"], "forced_side": "UNDER", "prizepicks_line": 26.0, "consensus_book_line": 26.5},
    {"player": "trindade", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 28.5, "mu": apply_cache_patch(28.0, "anchor_A", ["Cache", "Mirage"], "OVER"), "role": "anchor_A", "maps_likely": ["Cache", "Mirage"], "forced_side": "OVER", "prizepicks_line": 28.0, "consensus_book_line": 28.5},
    {"player": "Lacerda", "team": "Borracheiros", "match": "Borracheiros vs ALKA", "line": 26.5, "mu": apply_cache_patch(27.0, "entry", ["Cache", "Dust2"], "OVER"), "role": "entry", "maps_likely": ["Cache", "Dust2"], "forced_side": "OVER", "prizepicks_line": 27.5, "consensus_book_line": 27.0},
    {"player": "puni", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 25.5, "mu": apply_cache_patch(22.0, "rifler_star", ["Cache", "Nuke"], "UNDER"), "role": "rifler_star", "maps_likely": ["Cache", "Nuke"], "forced_side": "UNDER", "prizepicks_line": 25.0, "consensus_book_line": 25.5},
    {"player": "proSHOW", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 30.5, "mu": apply_cache_patch(30.0, "entry", ["Cache", "Anubis"], "OVER"), "role": "entry", "maps_likely": ["Cache", "Anubis"], "forced_side": "OVER", "prizepicks_line": 31.0, "consensus_book_line": 30.5},
    {"player": "vinaabEAST", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 29.5, "mu": apply_cache_patch(25.0, "anchor_B", ["Cache", "Inferno"], "UNDER"), "role": "anchor_B", "maps_likely": ["Cache", "Inferno"], "forced_side": "UNDER", "prizepicks_line": 29.0, "consensus_book_line": 29.5},
    {"player": "cerolzin", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 27.5, "mu": apply_cache_patch(28.0, "rifler_star", ["Cache", "Mirage"], "OVER"), "role": "rifler_star", "maps_likely": ["Cache", "Mirage"], "forced_side": "OVER", "prizepicks_line": 28.5, "consensus_book_line": 27.5},
    {"player": "bnc", "team": "ALKA", "match": "Borracheiros vs ALKA", "line": 29.5, "mu": apply_cache_patch(25.5, "entry", ["Cache", "Dust2"], "UNDER"), "role": "entry", "maps_likely": ["Cache", "Dust2"], "forced_side": "UNDER", "prizepicks_line": 29.0, "consensus_book_line": 29.5},

    # Match: Nuclear TigerES vs Color
    {"player": "z1k4", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 32.0, "mu": apply_cache_patch(32.5, "entry", ["Dust2", "Mirage"], "OVER"), "role": "entry", "maps_likely": ["Dust2", "Mirage"], "forced_side": "OVER", "prizepicks_line": 32.5, "consensus_book_line": 32.0},
    {"player": "flouzer", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 31.0, "mu": apply_cache_patch(26.5, "rifler_star", ["Dust2", "Ancient"], "UNDER"), "role": "rifler_star", "maps_likely": ["Dust2", "Ancient"], "forced_side": "UNDER", "prizepicks_line": 30.5, "consensus_book_line": 31.0},
    {"player": "ayuki", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 30.0, "mu": apply_cache_patch(25.0, "support", ["Dust2", "Mirage"], "UNDER"), "role": "support", "maps_likely": ["Dust2", "Mirage"], "forced_side": "UNDER", "prizepicks_line": 29.5, "consensus_book_line": 30.0}, 
    {"player": "m1QUSE", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(30.0, "entry", ["Dust2", "Inferno"], "OVER"), "role": "entry", "maps_likely": ["Dust2", "Inferno"], "forced_side": "OVER", "prizepicks_line": 30.0, "consensus_book_line": 29.5},
    {"player": "senka", "team": "Nuclear TigerES", "match": "Nuclear TigerES vs Color", "line": 25.5, "mu": apply_cache_patch(21.0, "support", ["Dust2", "Nuke"], "UNDER"), "role": "support", "maps_likely": ["Dust2", "Nuke"], "forced_side": "UNDER", "prizepicks_line": 25.0, "consensus_book_line": 25.5},
    {"player": "lattykk", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 31.5, "mu": apply_cache_patch(32.0, "rifler_star", ["Mirage", "Dust2"], "OVER"), "role": "rifler_star", "maps_likely": ["Mirage", "Dust2"], "forced_side": "OVER", "prizepicks_line": 32.0, "consensus_book_line": 31.5},
    {"player": "cronuss", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(24.5, "support", ["Mirage", "Anubis"], "UNDER"), "role": "support", "maps_likely": ["Mirage", "Anubis"], "forced_side": "UNDER", "prizepicks_line": 29.0, "consensus_book_line": 29.5}, 
    {"player": "Ryujin", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 29.5, "mu": apply_cache_patch(30.0, "entry", ["Mirage", "Inferno"], "OVER"), "role": "entry", "maps_likely": ["Mirage", "Inferno"], "forced_side": "OVER", "prizepicks_line": 30.0, "consensus_book_line": 29.5},
    {"player": "oz1k", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 26.5, "mu": apply_cache_patch(22.0, "anchor_A", ["Mirage", "Nuke"], "UNDER"), "role": "anchor_A", "maps_likely": ["Mirage", "Nuke"], "forced_side": "UNDER", "prizepicks_line": 26.0, "consensus_book_line": 26.5},
    {"player": "reyoz", "team": "Color", "match": "Nuclear TigerES vs Color", "line": 26.0, "mu": apply_cache_patch(21.0, "support", ["Mirage", "Dust2"], "UNDER"), "role": "support", "maps_likely": ["Mirage", "Dust2"], "forced_side": "UNDER", "prizepicks_line": 25.5, "consensus_book_line": 26.0},

    # Match: Grêmio vs paiN Academy
    {"player": "MITHPUTTINI", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(29.0, "entry", ["Inferno", "Mirage"], "OVER"), "role": "entry", "maps_likely": ["Inferno", "Mirage"], "forced_side": "OVER", "prizepicks_line": 29.0, "consensus_book_line": 28.5},
    {"player": "yeda", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 27.5, "mu": apply_cache_patch(23.0, "rifler_star", ["Inferno", "Dust2"], "UNDER"), "role": "rifler_star", "maps_likely": ["Inferno", "Dust2"], "forced_side": "UNDER", "prizepicks_line": 27.0, "consensus_book_line": 27.5},
    {"player": "balencyy", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 31.5, "mu": apply_cache_patch(32.0, "anchor_B", ["Inferno", "Cache"], "OVER"), "role": "anchor_B", "maps_likely": ["Inferno", "Cache"], "forced_side": "OVER", "prizepicks_line": 32.0, "consensus_book_line": 31.5},
    {"player": "s1lent", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(24.0, "support", ["Inferno", "Anubis"], "UNDER"), "role": "support", "maps_likely": ["Inferno", "Anubis"], "forced_side": "UNDER", "prizepicks_line": 28.0, "consensus_book_line": 28.5},
    {"player": "souz4h", "team": "Grêmio", "match": "Grêmio vs paiN Academy", "line": 28.5, "mu": apply_cache_patch(29.0, "entry", ["Inferno", "Nuke"], "OVER"), "role": "entry", "maps_likely": ["Inferno", "Nuke"], "forced_side": "OVER", "prizepicks_line": 29.0, "consensus_book_line": 28.5},

    # Match: Tyloo vs Kaleido Gaming
    {"player": "Moseyuh", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.5, "mu": apply_cache_patch(29.0, "entry", ["Ancient", "Anubis"], "OVER"), "role": "entry", "maps_likely": ["Ancient", "Anubis"], "forced_side": "OVER", "prizepicks_line": 29.0, "consensus_book_line": 28.5},
    {"player": "Jee", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 30.0, "mu": apply_cache_patch(30.5, "awp", ["Ancient", "Mirage"], "OVER"), "role": "awp", "maps_likely": ["Ancient", "Mirage"], "forced_side": "OVER", "prizepicks_line": 30.5, "consensus_book_line": 30.0},
    {"player": "Zero", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.5, "mu": apply_cache_patch(24.0, "support", ["Ancient", "Inferno"], "UNDER"), "role": "support", "maps_likely": ["Ancient", "Inferno"], "forced_side": "UNDER", "prizepicks_line": 28.0, "consensus_book_line": 28.5},
    {"player": "JamYoung", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 31.0, "mu": apply_cache_patch(31.5, "rifler_star", ["Ancient", "Dust2"], "OVER"), "role": "rifler_star", "maps_likely": ["Ancient", "Dust2"], "forced_side": "OVER", "prizepicks_line": 31.5, "consensus_book_line": 31.0},
    {"player": "Mercury", "team": "Tyloo", "match": "Tyloo vs Kaleido Gaming", "line": 28.0, "mu": apply_cache_patch(23.5, "entry", ["Ancient", "Nuke"], "UNDER"), "role": "entry", "maps_likely": ["Ancient", "Nuke"], "forced_side": "UNDER", "prizepicks_line": 27.5, "consensus_book_line": 28.0},

    # Match: Rare Atom vs Lynn Vision
    {"player": "ChildKing", "team": "Rare Atom", "match": "Rare Atom vs Lynn Vision", "line": 27.5, "mu": apply_cache_patch(28.0, "rifler_star", ["Anubis", "Inferno"], "OVER"), "role": "rifler_star", "maps_likely": ["Anubis", "Inferno"], "forced_side": "OVER", "prizepicks_line": 28.0, "consensus_book_line": 27.5}
]

best6 = filter_picks(picks_board)

st.subheader("🔥 Top Filtered Portal Cards")

if not best6:
    st.info("No picks met the strict model criteria for this slate.")
else:
    for b in best6:
        # Calculate book discrepancies
        pp_diff = b['line'] - b['prizepicks_line']
        book_diff = b['line'] - b['consensus_book_line']
        
        # Determine Hammer tag status based on sharp discrepancies
        hammer_tag = None
        if b['side'] == 'OVER' and (pp_diff < 0 or book_diff < 0):
            hammer_tag = "🔨 HAMMER MORE"
        elif b['side'] == 'UNDER' and (pp_diff > 0 or book_diff > 0):
            hammer_tag = "🔨 HAMMER LESS"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                hammer_display = f"  \n*{hammer_tag}*" if hammer_tag else ""
                st.markdown(f"**{b['player']}** ({b['team']})  \n*Match:* {b['match']}{hammer_display}")
            with col2:
                st.markdown(f"**Side:** `{b['side']}`  \n**Line:** {b['line']}  \n*PP Line:* {b['prizepicks_line']} | *Books:* {b['consensus_book_line']}")
            with col3:
                st.metric(label="Model Probability", value=f"{b['prob']*100:.1f}%", delta=f"+{b['edge']*100:.1f}% Edge")
            st.markdown("---")
