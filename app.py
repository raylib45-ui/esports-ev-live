import json
import pandas as pd
import requests


def fetch_prizepicks_cs2_board():
    """Fetches the live PrizePicks CS2 board (League ID 124) and formats it for the Streamlit Scanner App."""
    url = "https://api.prizepicks.com/projections"
    params = {
        "league_id": "124",  # CS2 League ID on PrizePicks
        "per_page": "250",
        "single_stat": "true",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    print("📡 Fetching live PrizePicks CS2 slate...")
    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error fetching slate: HTTP {response.status_code}")
        return None

    payload = response.json()

    # Build a lookup dictionary for players and stat types
    included_data = {
        item["id"]: item for item in payload.get("included", [])
    }

    parsed_board = []

    for proj in payload.get("data", []):
        rel = proj.get("relationships", {})

        # Extract Player and Stat IDs
        player_id = (
            rel.get("new_player", {}).get("data", {}).get("id")
            if "new_player" in rel
            else None
        )
        stat_id = (
            rel.get("stat_type", {}).get("data", {}).get("id")
            if "stat_type" in rel
            else None
        )

        player_info = included_data.get(player_id, {}).get("attributes", {})
        stat_info = included_data.get(stat_id, {}).get("attributes", {})

        player_name = player_info.get("name", "Unknown")
        team = player_info.get("team", "TBD")
        stat_type = stat_info.get("name", "Kills")
        line_score = proj.get("attributes", {}).get("line_score")

        # Skip invalid or empty lines
        if not line_score or not player_name:
            continue

        parsed_board.append({
            "player": player_name,
            "team": team,
            "opponent": "OPP",
            "prop_type": stat_type,
            "line": float(line_score),
            # Model default parameters for live scanning (or integrate with HLTV API)
            "kpr_l15": 0.72,
            "expected_rounds": 44.0 if "1-2" in stat_type else 22.0,
            "map_factor": 1.00,
            "opponent_adj": 1.00,
            "last_10_logs": json.dumps([
                int(line_score + i) for i in [-2, 1, 3, -1, 4, 2, -3, 1, 2, 3]
            ]),  # Sample log structure
        })

    df = pd.DataFrame(parsed_board)

    # Save formatted CSV directly
    filename = "CS2_PrizePicks_Slate.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Successfully exported {len(df)} live CS2 props to '{filename}'!")
    return df


if __name__ == "__main__":
    fetch_prizepicks_cs2_board()
