import pandas as pd
import numpy as np
from scripts.predict_current import build_current

def test_predraw_entry_keeps_post_and_bracket_missing():
    current = pd.DataFrame([{
        "馬名": "テストホース",
        "性齢": "牡4",
        "負担重量": "57.0",
        "騎手": "テスト騎手",
        "調教師": "テスト調教師",
        "単勝オッズ": "5.0",
        "race_date": "2026-10-04",
        "course": "東京",
        "distance": 1800,
        "surface": "芝",
        "track_condition": "良",
        "race_no": 11,
        "meeting_no": 4,
    }])
    history = pd.DataFrame([{
        "race_date": "2026-09-20",
        "horse": "別馬",
        "finish": 2,
        "course": "東京",
        "distance": 1800,
        "surface": "芝",
        "track_condition": "良",
        "jockey": "テスト騎手",
        "trainer": "テスト調教師",
    }])
    out = build_current(current, history)
    assert len(out) == 1
    assert pd.isna(out.loc[0, "post"])
    assert pd.isna(out.loc[0, "bracket"])
    assert out.loc[0, "trainer_win_rate"] > 0
    assert out.loc[0, "season"] == "10"

def test_predraw_field_size_is_counted_per_race():
    current = pd.DataFrame([
        {"馬名":"A","性齢":"牡4","負担重量":"57","騎手":"J1","調教師":"T1","race_date":"2026-10-04","course":"東京","distance":1800,"surface":"芝","track_condition":"良","race_no":11,"meeting_no":4},
        {"馬名":"B","性齢":"牝4","負担重量":"55","騎手":"J2","調教師":"T2","race_date":"2026-10-04","course":"東京","distance":1800,"surface":"芝","track_condition":"良","race_no":11,"meeting_no":4},
    ])
    history = pd.DataFrame([{"race_date":"2026-09-20","horse":"X","finish":1,"course":"東京","distance":1800,"surface":"芝","track_condition":"良","jockey":"J0","trainer":"T0"}])
    out = build_current(current, history)
    assert set(out["field_size"]) == {2}
    assert all(np.isnan(out["post"]))


def test_predraw_missing_meeting_no_is_safe():
    current = pd.DataFrame([{
        "馬名": "テストホース", "性齢": "牡4", "負担重量": "57", "騎手": "J1",
        "調教師": "T1", "単勝オッズ": "5.0", "race_date": "2026-10-04",
        "course": "東京", "distance": 1800, "surface": "芝", "race_no": 11,
    }])
    history = pd.DataFrame([{
        "race_date": "2026-09-20", "horse": "X", "finish": 1, "course": "東京",
        "distance": 1800, "surface": "芝", "track_condition": "良",
        "jockey": "J0", "trainer": "T0",
    }])
    out = build_current(current, history)
    assert out.loc[0, "meeting_no"] == "unknown"


def test_current_prediction_rates_exclude_current_and_future_dates():
    current = pd.DataFrame([{
        "馬名": "テストホース", "性齢": "牡4", "負担重量": "57", "騎手": "J1",
        "調教師": "T1", "単勝オッズ": "5.0", "race_date": "2026-10-04",
        "course": "東京", "distance": 1800, "surface": "芝", "track_condition": "良",
        "race_no": 11, "meeting_no": 4,
    }])
    history = pd.DataFrame([
        {"race_date":"2026-09-20","horse":"X","finish":1,"course":"東京","distance":1800,"surface":"芝","track_condition":"良","jockey":"J0","trainer":"T0"},
        {"race_date":"2026-10-04","horse":"X","finish":1,"course":"東京","distance":1800,"surface":"芝","track_condition":"良","jockey":"J1","trainer":"T1"},
        {"race_date":"2026-10-05","horse":"X","finish":1,"course":"東京","distance":1800,"surface":"芝","track_condition":"良","jockey":"J1","trainer":"T1"},
    ])
    out = build_current(current, history)
    # Only the 2026-09-20 result is prior information; current/future outcomes must not affect the rate.
    assert abs(out.loc[0, "trainer_win_rate"] - (1+1)/(1+20)) < 1e-9
