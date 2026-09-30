import pandas as pd
from scripts.backtest import evaluate

def test_evaluate_deduplicates_horse_rows_and_reports_market_baseline():
    df=pd.DataFrame([
        {"race_key":"r1","horse":"A","odds":4,"model_win_prob":0.5,"finish":1,"field_size":2},
        {"race_key":"r1","horse":"A","odds":4,"model_win_prob":0.5,"finish":1,"field_size":2},
        {"race_key":"r1","horse":"B","odds":5,"model_win_prob":0.3,"finish":2,"field_size":2},
    ])
    out=evaluate(df,min_ev=1.2,min_odds=3)
    assert out["bets"]==2
    assert out["races"]==1
    assert out["max_bets_per_race"]==2
    assert out["market_implied_hit_rate"]>0

def test_evaluate_rejects_impossible_finish_positions():
    df=pd.DataFrame([
        {"race_key":"r1","horse":"A","odds":4,"model_win_prob":0.5,"finish":3,"field_size":2},
        {"race_key":"r1","horse":"B","odds":5,"model_win_prob":0.3,"finish":1,"field_size":2},
    ])
    out=evaluate(df,min_ev=1.2,min_odds=3)
    assert out["bets"]==1
    assert out["return"]==5.0
