import pandas as pd
import numpy as np

def scan_cs2_props(props_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters CS2 player props using strict Capricorn/Scorpio quantitative rules:
    1. Calculates projected kills using KPR, expected rounds, and map/opponent modifiers.
    2. Enforces a strict 80%+ consistency threshold over the last 10 game logs.
    3. Requires a minimum projection gap of +/- 2.5 kills from the line.
    """
    
    # --- PHASE 1: SCORPIO PROJECTION ENGINE ---
    # Formula: (KPR * Expected Rounds) * Map Multiplier * Opponent Adjustment
    props_df['projected_kills'] = (
        props_df['kpr_l15'] * props_df['expected_rounds'] * props_df['map_factor'] * props_df['opponent_adj']
    )
    
    # Calculate raw projection gap relative to the betting line
    props_df['proj_gap'] = props_df['projected_kills'] - props_df['line']
    
    # --- PHASE 2: CAPRICORN CONSISTENCY AUDIT ---
    def calculate_hit_rates(row):
        logs = np.array(row['last_10_logs'])
        over_rate = np.sum(logs > row['line']) / len(logs)
        under_rate = np.sum(logs < row['line']) / len(logs)
        return pd.Series([over_rate, under_rate])

    props_df[['over_hit_rate', 'under_hit_rate']] = props_df.apply(calculate_hit_rates, axis=1)

    # --- PHASE 3: STRICT BINARY FILTERING ---
    # Rule 1: Must be strictly OVER gap (+2.5) AND consistently over (>= 80% / 8 of 10)
    qualify_over = (props_df['proj_gap'] >= 2.5) & (props_df['over_hit_rate'] >= 0.80)
    
    # Rule 2: Must be strictly UNDER gap (-2.5) AND consistently under (>= 80% / 8 of 10)
    qualify_under = (props_df['proj_gap'] <= -2.5) & (props_df['under_hit_rate'] >= 0.80)

    # Apply strict selection criteria
    conditions = [qualify_over, qualify_under]
    choices = ['QUALIFIED OVER 🔒', 'QUALIFIED UNDER 🔒']
    props_df['recommendation'] = np.select(conditions, choices, default='PASS (NO EDGE)')

    return props_df


# ==========================================
# EXAMPLE BOARD SCANNER IMPLEMENTATION
# ==========================================

board_data = [
    {
        'player': 'b1t',
        'prop_type': 'Maps 1-2 Kills',
        'line': 32.5,
        'kpr_l15': 0.74,
        'expected_rounds': 46.0,  # Projected tight 2-map series (~23 rounds/map)
        'map_factor': 1.05,        # Strong map pool matchup
        'opponent_adj': 1.00,
        'last_10_logs': [35, 38, 33, 36, 29, 34, 37, 33, 31, 35]  # 8/10 Over -> 80%
    },
    {
        'player': 'apEX',
        'prop_type': 'Map 1 Kills',
        'line': 14.5,
        'kpr_l15': 0.52,
        'expected_rounds': 19.5,  # Projected heavy blowout (low round volume)
        'map_factor': 0.95,
        'opponent_adj': 0.90,     # Slow CT default playstyle
        'last_10_logs': [11, 12, 10, 13, 16, 12, 9, 11, 14, 10]   # 9/10 Under -> 90%
    },
    {
        'player': 'm0NESY',
        'prop_type': 'Map 1 Kills',
        'line': 18.5,
        'kpr_l15': 0.85,
        'expected_rounds': 22.0,
        'map_factor': 1.00,
        'opponent_adj': 1.00,
        'last_10_logs': [19, 14, 22, 12, 20, 15, 21, 13, 18, 17]  # Volatile (5/10) -> FAILS Rule 1
    }
]

df = pd.DataFrame(board_data)
results = scan_cs2_props(df)

# Output only actionable plays
qualified_board = results[results['recommendation'] != 'PASS (NO EDGE)']
print(qualified_board[['player', 'prop_type', 'line', 'projected_kills', 'proj_gap', 'recommendation']])
