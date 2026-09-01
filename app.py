import math

# --- CONFIG ---
SIGMA_BASE = 4.5  # MAPS 1-2 Kills
SIGMA_CACHE = 4.8  # high variance on Cache
MIN_EDGE_PCT = 0.06  # >6% discrepancy
MIN_PROB = 0.61  # >61% bucket (no 54-56% forcing)
MAX_PER_TEAM = 1
MAX_PER_MATCH = 2  # if Cache in pool, treat as 1
MAX_PER_MATCH_CACHE = 1

# Patch adjustments - post July 9 only data weighted 100%, pre July 9 weighted 50%
PATCH = {
    "mid_duels": 1.5,  # removed CT mid boost hole = more aim duels
    "self_boost_A": 0.8,  # Shroud boost A
    "ebox_checkers": 1.0,  # E-box visibility + Checkers/Vent light
    "post_plant_smoke_molly": 1.5,  # July 21 bomb disperses smoke + extinguishes molly
    "awp_save_buff": 1.0,  # July 10 no min 1 dmg = more saves = + mu next round for AWPer
    "exit_frag_nerf": -0.5,  # fewer exit frags
}

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def apply_cache_patch(mu, role, maps_likely):
    """ role: 'entry', 'anchor_A', 'anchor_B', 'awp', 'support' """
    adj = PATCH.get("post_plant_smoke_molly", 1.5)
    if role in ["entry", "rifler_star"]:
        adj += PATCH.get("mid_duels", 1.5)
    if role in ["anchor_A", "awp"]:
        adj += PATCH.get("self_boost_A", 0.8) + PATCH.get("awp_save_buff", 1.0)
    if role == "anchor_B":
        adj += PATCH.get("ebox_checkers", 1.0)
    if "Cache" in maps_likely:
        adj += 0.5  # extra chaos
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
    """
    picks = list of dict {player, team, match, line, mu, role, maps_likely, sigma}
    """
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

# --- EXAMPLE USAGE ---
picks_board = [
    {"player": "Annihilation", "team": "The Huns", "match": "The Huns vs Staqued", "line": 32.5, "mu": apply_cache_patch(38.0, "entry", ["Cache","Nuke"]), "role": "entry", "maps_likely": ["Nuke","Anubis","Cache"]},
    {"player": "balencyy", "team": "Gremio", "match": "Gremio vs ODDIK", "line": 27.5, "mu": apply_cache_patch(30.5, "anchor_B", ["Inferno","Cache"]), "role": "anchor_B", "maps_likely": ["Inferno","Cache"]},
    {"player": "jared", "team": "Chicken Coop", "match": "Chicken Coop vs Overtake", "line": 30.0, "mu": apply_cache_patch(33.0, "entry", ["Mirage","Anubis"]), "role": "entry", "maps_likely": ["Mirage","Anubis"]},
    {"player": "donk", "team": "Spirit", "match": "Spirit vs FURIA", "line": 39.5, "mu": apply_cache_patch(42.0, "entry", ["Cache","Anubis"]), "role": "entry", "maps_likely": ["Anubis","Cache"]},
    {"player": "junior", "team": "Voca", "match": "Voca vs Marsborne", "line": 31.5, "mu": apply_cache_patch(35.0, "entry", ["Dust2"]), "role": "entry", "maps_likely": ["Dust2","Mirage"]},
    {"player": "cadnyx", "team": "Bushido", "match": "Bushido vs ex-RUSTEC", "line": 30.5, "mu": apply_cache_patch(33.5, "anchor_A", ["Cache"]), "role": "anchor_A", "maps_likely": ["Cache","Inferno"]},
]

best6 = filter_picks(picks_board)
for b in best6:
    print(f"{b['player']} {b['side']} {b['line']} -> mu {b['mu']:.1f} prob {b['prob']*100:.1f}% edge {b['edge']*100:.1f}% match {b['match']}")
