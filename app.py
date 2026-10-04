import numpy as np

def run_cs2_prop_monte_carlo(
    line=33.0,
    base_kpr=0.74,
    kpr_std=0.07,
    mean_rounds_per_map=20.5,
    std_rounds_per_map=3.0,
    num_simulations=100_000,
    seed=42
):
    """
    Simulates CS2 player kills across Maps 1 and 2 using a compound Poisson process.
    
    Parameters:
    - line (float): The line set by the platform (e.g., 33.0).
    - base_kpr (float): Projected Kills Per Round (e.g., 0.74).
    - kpr_std (float): Standard deviation of player's KPR (match-to-match volatility).
    - mean_rounds_per_map (float): Average MR12 map length (~20.5 rounds).
    - std_rounds_per_map (float): Standard deviation of map lengths.
    - num_simulations (int): Number of Monte Carlo trials.
    - seed (int): Random seed for reproducibility.
    """
    np.random.seed(seed)
    
    # 1. Simulate Round Counts for Map 1 and Map 2 (MR12 limits: min 13 rounds, max 36 with OT)
    rounds_m1 = np.clip(np.random.normal(mean_rounds_per_map, std_rounds_per_map, num_simulations), 13, 36)
    rounds_m2 = np.clip(np.random.normal(mean_rounds_per_map, std_rounds_per_map, num_simulations), 13, 36)
    
    # Total combined rounds across both maps
    total_rounds = np.round(rounds_m1) + np.round(rounds_m2)
    
    # 2. Simulate Match-Specific KPR (Accounting for form/match volatility)
    match_kpr = np.random.normal(base_kpr, kpr_std, num_simulations)
    match_kpr = np.maximum(match_kpr, 0.10)  # Prevent negative KPR
    
    # 3. Simulate Kills via Poisson Process: Poisson(lambda = total_rounds * match_kpr)
    expected_kills = total_rounds * match_kpr
    simulated_kills = np.random.poisson(expected_kills)
    
    # 4. Calculate Hit Rates
    over_mask = simulated_kills > line
    under_mask = simulated_kills < line
    push_mask = simulated_kills == line
    
    p_over = np.mean(over_mask)
    p_under = np.mean(under_mask)
    p_push = np.mean(push_mask)
    
    # Push-Adjusted Win Probabilities (Excluding refund cases)
    win_prob_over_adj = p_over / (p_over + p_under)
    win_prob_under_adj = p_under / (p_over + p_under)
    
    # Summary Output
    print(f"==================================================")
    print(f"   MONTE CARLO PROJECTION: CS2 MAPS 1-2 KILLS     ")
    print(f"==================================================")
    print(f" Target Line          : {line}")
    print(f" Base KPR             : {base_kpr:.2f} (Std: {kpr_std:.2f})")
    print(f" Mean Rounds / Map    : {mean_rounds_per_map:.1f}")
    print(f" Total Simulations    : {num_simulations:,}")
    print(f"--------------------------------------------------")
    print(f" Mean Projected Kills : {np.mean(simulated_kills):.2f}")
    print(f" Median Kills (50th%) : {np.median(simulated_kills):.1f}")
    print(f" Standard Deviation   : {np.std(simulated_kills):.2f}")
    print(f"--------------------------------------------------")
    print(f" OVER {line:4.1f}            : {p_over*100:6.2f}%  (Adj Win Prob: {win_prob_over_adj*100:.2f}%)")
    print(f" UNDER {line:4.1f}           : {p_under*100:6.2f}%  (Adj Win Prob: {win_prob_under_adj*100:.2f}%)")
    print(f" PUSH ({int(line)})             : {p_push*100:6.2f}%")
    print(f"==================================================")

# Execute simulation
if __name__ == "__main__":
    run_cs2_prop_monte_carlo(
        line=33.0,
        base_kpr=0.74,               # Brehze baseline KPR
        kpr_std=0.07,                # Form variance
        mean_rounds_per_map=20.5,    # Average CS2 MR12 map duration
        num_simulations=100_000
    )
