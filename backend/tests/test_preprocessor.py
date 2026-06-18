import unittest
import pandas as pd
import numpy as np
from backend.data.preprocessor import parse_time_to_seconds, preprocess_game, get_game_winner

class TestPreprocessor(unittest.TestCase):
    
    def test_parse_time_to_seconds(self):
        self.assertEqual(parse_time_to_seconds("12:00"), 720.0)
        self.assertEqual(parse_time_to_seconds("11:58"), 718.0)
        self.assertEqual(parse_time_to_seconds("00:04.5"), 4.5)
        self.assertEqual(parse_time_to_seconds("00:00"), 0.0)
        self.assertEqual(parse_time_to_seconds(None), 0.0)
        self.assertEqual(parse_time_to_seconds("invalid"), 0.0)

    def test_preprocess_game(self):
        # Create a mock play-by-play sequence
        # Home Team ID = 10, Away Team ID = 20
        raw_events = [
            # Period 1 start
            {
                "eventnum": 1, "eventmsgtype": 12, "period": 1, "pctimestring": "12:00",
                "homedescription": None, "neutraldescription": "Start Period", "visitordescription": None,
                "score": None, "scoremargin": None, "player1_team_id": None, "player1_id": None, "player3_team_id": None
            },
            # Jump ball won by Home (10)
            {
                "eventnum": 2, "eventmsgtype": 10, "period": 1, "pctimestring": "12:00",
                "homedescription": "Jump Ball", "neutraldescription": None, "visitordescription": None,
                "score": None, "scoremargin": None, "player1_team_id": 10, "player1_id": 101, "player3_team_id": 10
            },
            # Home makes a 2-point shot, Score becomes Away 0 - Home 2
            {
                "eventnum": 3, "eventmsgtype": 1, "period": 1, "pctimestring": "11:30",
                "homedescription": "Player H 2pt shot", "neutraldescription": None, "visitordescription": None,
                "score": "0 - 2", "scoremargin": "2", "player1_team_id": 10, "player1_id": 102, "player3_team_id": None
            },
            # Away misses a shot
            {
                "eventnum": 4, "eventmsgtype": 2, "period": 1, "pctimestring": "11:00",
                "homedescription": None, "neutraldescription": None, "visitordescription": "Player A misses shot",
                "score": None, "scoremargin": None, "player1_team_id": 20, "player1_id": 201, "player3_team_id": None
            },
            # Home commits defensive foul
            {
                "eventnum": 5, "eventmsgtype": 6, "period": 1, "pctimestring": "10:45",
                "homedescription": "Player H defensive foul", "neutraldescription": None, "visitordescription": None,
                "score": None, "scoremargin": None, "player1_team_id": 10, "player1_id": 102, "player3_team_id": None
            },
            # Away calls timeout
            {
                "eventnum": 6, "eventmsgtype": 9, "period": 1, "pctimestring": "10:30",
                "homedescription": None, "neutraldescription": None, "visitordescription": "Timeout",
                "score": None, "scoremargin": None, "player1_team_id": 20, "player1_id": 20, "player3_team_id": None
            }
        ]
        
        df_raw = pd.DataFrame(raw_events)
        
        # Run preprocessing
        df_processed = preprocess_game(
            game_id="001",
            pbp_df=df_raw,
            home_team_id=10,
            away_team_id=20,
            home_team_abbr="BOS",
            away_team_abbr="LAL"
        )
        
        self.assertEqual(len(df_processed), 6)
        
        # Verify Score Margin calculation
        # Event 3 score is "0 - 2" (Visitor 0 - Home 2) -> margin should be 2.0
        self.assertEqual(df_processed.iloc[2]["score_margin"], 2.0)
        # Event 4 score is missing -> should carry over previous margin (2.0)
        self.assertEqual(df_processed.iloc[3]["score_margin"], 2.0)
        
        # Verify Possession changes
        # Event 2: Home wins jump ball -> possession = 1
        self.assertEqual(df_processed.iloc[1]["possession"], 1)
        # Event 3: Home makes shot -> possession shifts to Away (-1)
        self.assertEqual(df_processed.iloc[2]["possession"], -1)
        # Event 4: Away misses shot -> contested (0)
        self.assertEqual(df_processed.iloc[3]["possession"], 0)
        
        # Verify Timeout tracking
        # Away starts at 7 timeouts. Event 6 (Away timeout) should decrement it to 6.
        self.assertEqual(df_processed.iloc[5]["away_timeouts_remaining"], 6)
        self.assertEqual(df_processed.iloc[5]["home_timeouts_remaining"], 7)
        
        # Verify Foul tracking
        # Home fouls should increment on defensive foul (Event 5)
        self.assertEqual(df_processed.iloc[4]["home_fouls"], 1)
        self.assertEqual(df_processed.iloc[4]["away_fouls"], 0)
        
        # Verify Winner calculation
        self.assertEqual(get_game_winner(df_processed), 1)

if __name__ == '__main__':
    unittest.main()
