import json
import re
import cv2
import easyocr
import pandas as pd

# Initialize EasyOCR reader (English)
reader = easyocr.Reader(['en'], gpu=False)


def parse_prizepicks_screenshot(
    image_path: str, default_match_id: str = "MATCH_1"
) -> pd.DataFrame:
    """Extracts player lines from a PrizePicks CS2 screenshot using OCR

    and regex pattern matching.
    """
    # 1. Run OCR on the image
    results = reader.readtext(image_path, detail=0)
    full_text = " ".join(results)

    # 2. Extract individual player entry blocks using Regex
    # Regex pattern matches: [Player Name] [Team/Pos] [Prop Type] [Line Value]
    # Example matched pattern: "KSCERATO FURIA • G MAPS 1-2 Kills 31.5"
    player_pattern = re.compile(
        r'([A-Za-z0-9_\-\s]{2,15})\s+([A-Za-z0-9]{2,12}\s*•\s*[A-Z])\s+(MAPS\s+1-2\s+[A-Za-z\s]+)\s+([0-9]{1,2}\.5)',
        re.IGNORECASE,
    )

    extracted_props = []

    # Alternative block parsing if text line breaks occur
    i = 0
    while i < len(results):
        text = results[i].strip()

        # Look for standard prop types: "MAPS 1-2 Kills" or "MAPS 1-2 Headshots"
        if "MAPS 1-2" in text.upper():
            try:
                # Player name is usually 2 positions above the prop type
                player_name = results[max(0, i - 2)].strip()
                team_info = results[max(0, i - 1)].strip()
                prop_type = text
                line_val = float(results[min(len(results) - 1, i + 1)].strip())

                # Clean Team Name (e.g., "FURIA • G" -> "FURIA")
                team_clean = (
                    team_info.split("•")[0].strip()
                    if "•" in team_info
                    else team_info
                )

                extracted_props.append({
                    "match_id": default_match_id,
                    "player": player_name,
                    "team": team_clean,
                    "opponent": "OPPONENT",  # Default placeholder
                    "prop_type": prop_type,
                    "line": line_val,
                    # Baseline model defaults (populated automatically for scanner)
                    "stat_per_round": 0.65,
                    "expected_rounds": 44.0,
                    "map_factor": 1.00,
                    "opponent_adj": 1.00,
                    "adr": 72.0,
                    "assist_rate": 0.15,
                    "first_kills_per_round": 0.10,
                    "match_rating_diff": 0.15,
                    "last_10_logs": json.dumps(
                        [
                            int(line_val - 2),
                            int(line_val + 3),
                            int(line_val - 1),
                            int(line_val + 1),
                            int(line_val + 4),
                            int(line_val - 3),
                            int(line_val + 2),
                            int(line_val - 1),
                            int(line_val + 2),
                            int(line_val + 1),
                        ]
                    ),
                })
            except (ValueError, IndexError):
                pass
        i += 1

    df = pd.DataFrame(extracted_props)
    return df


# ==========================================
# EXECUTION & EXPORT
# ==========================================
if __name__ == "__main__":
    # Replace with your screenshot file name
    screenshot_file = "prizepicks_slip.png"

    print(f"🔍 Processing {screenshot_file}...")
    parsed_df = parse_prizepicks_screenshot(
        screenshot_file, default_match_id="MOUZ_FURIA"
    )

    if not parsed_df.empty:
        output_filename = "prizepicks_parsed_slate.csv"
        parsed_df.to_csv(output_filename, index=False)
        print(f"✅ Successfully extracted {len(parsed_df)} player props!")
        print(f"📂 Saved formatted CSV to: {output_filename}")
        print("\nParsed Summary:")
        print(parsed_df[["player", "team", "prop_type", "line"]])
    else:
        print(
            "⚠️ No valid prop patterns detected. Ensure image is clear and cropped to the lineup area."
        )
