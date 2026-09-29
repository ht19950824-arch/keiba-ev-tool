import pandas as pd
from app.model import CATEGORICAL, NUMERIC, fit, predict

def sample():
    rows=[]
    for race in range(6):
        for h in range(8):
            rows.append({
                "race_key":f"r{race}","win":int(h==race%8),
                "age":3,"weight_carried":56,"horse_weight":480,"horse_weight_diff":0,
                "post":h+1,"bracket":h//2+1,"distance":1400,"field_size":8,
                "days_since_last":28,"last_finish":h+1,"last3_avg_finish":5,
                "last3_avg_margin":.5,"last3_avg_speed":0,"early_position":h+1,
                "final_position":h+1,"position_change":0,"last3f_rank":h+1,
                "track_bias_score":0,"pace_score":0,"jockey_win_rate":.1,
                "trainer_win_rate":.1,"course_win_rate":.1,"distance_win_rate":.1,
                "surface_win_rate":.1,"condition_win_rate":.1,"class_score":0,
                "course":"東京","surface":"ダート","track_condition":"良","sex":"牡",
                "running_style":"先行","class_name":"未勝利","season":"2","meeting_no":"1",
                "jockey":f"J{h}","trainer":f"T{h}","sire":f"S{h}","dam_sire":f"D{h}",
                "odds":5+h
            })
    return pd.DataFrame(rows)

def test_probability_normalization():
    df=sample(); bundle=fit(df); out=predict(bundle,df)
    assert all(abs(v-1)<1e-6 for v in out.groupby("race_key")["model_win_prob"].sum())
    assert "expected_value" in out.columns

def test_market_not_feature():
    assert "odds" not in NUMERIC+CATEGORICAL
    assert not ({"jockey","trainer","sire","dam_sire"} & set(CATEGORICAL))
