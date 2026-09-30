import pandas as pd
from scripts.features import add_historical_features

def test_prior_rates_exclude_other_horses_from_same_race():
    df=pd.DataFrame([
        {"race_key":"2026-10-01-Tokyo-1-1","race_date":"2026-10-01","post":1,"bracket":1,"horse":"A","jockey":"J","trainer":"T","course":"東京","distance":1800,"surface":"芝","track_condition":"良","finish":1},
        {"race_key":"2026-10-01-Tokyo-1-1","race_date":"2026-10-01","post":2,"bracket":1,"horse":"B","jockey":"J2","trainer":"T","course":"東京","distance":1800,"surface":"芝","track_condition":"良","finish":2},
        {"race_key":"2026-10-08-Tokyo-1-1","race_date":"2026-10-08","post":1,"bracket":1,"horse":"C","jockey":"J3","trainer":"T","course":"東京","distance":1800,"surface":"芝","track_condition":"良","finish":3},
    ])
    out=add_historical_features(df)
    # Both horses in the first race have the same pre-race trainer information.
    assert out.loc[out.horse=="A","trainer_win_rate"].iloc[0] == out.loc[out.horse=="B","trainer_win_rate"].iloc[0]
    # The later race can use both prior results from the trainer.
    assert out.loc[out.horse=="C","trainer_win_rate"].iloc[0] > out.loc[out.horse=="A","trainer_win_rate"].iloc[0]
