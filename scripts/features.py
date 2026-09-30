from __future__ import annotations
import numpy as np
import pandas as pd

def _prior_rate(x, keys, target, alpha=1.0, beta=9.0):
    # Exclude the entire current race from historical aggregates. This prevents
    # multi-horse races (especially trainer/course aggregates) from leaking
    # earlier finish results into later rows of the same race.
    if "race_key" not in x.columns:
        g=x.groupby(keys,dropna=False,sort=False)[target]
        prior_sum=g.transform(lambda s:s.shift().fillna(0).cumsum())
        prior_n=g.transform(lambda s:s.shift().notna().cumsum())
        return (prior_sum+alpha)/(prior_n+alpha+beta)
    work=x.copy()
    race_cols=list(dict.fromkeys(list(keys)+["race_key"]))
    race=work.groupby(race_cols,dropna=False,sort=False)[target].agg(["sum","count"]).reset_index()
    race=race.sort_values(["race_key"],kind="stable")
    grouped=race.groupby(keys,dropna=False,sort=False)
    race["prior_sum"]=grouped["sum"].cumsum()-race["sum"]
    race["prior_n"]=grouped["count"].cumsum()-race["count"]
    rate=(race["prior_sum"]+alpha)/(race["prior_n"]+alpha+beta)
    lookup=race[race_cols].copy()
    lookup["_rate"]=rate.to_numpy()
    merged=work[race_cols].merge(lookup,on=race_cols,how="left",sort=False)
    return pd.Series(merged["_rate"].to_numpy(),index=x.index)
def add_historical_features(df):
    x=df.copy()
    x["race_date"]=pd.to_datetime(x["race_date"],errors="coerce")
    x=x.sort_values(["race_date","race_key","post"]).reset_index(drop=True)
    x["finish"]=pd.to_numeric(x["finish"],errors="coerce")
    x["win"]=(x["finish"]==1).astype(int)
    x["field_size"]=x.groupby("race_key")["post"].transform("count")
    horse=x.groupby("horse",dropna=False,sort=False)
    x["last_finish"]=horse["finish"].shift(1)
    x["last3_avg_finish"]=horse["finish"].transform(lambda s:s.shift().rolling(3,min_periods=1).mean())
    x["horse_win_rate"]=_prior_rate(x,["horse"],"win",1,19)
    x["days_since_last"]=horse["race_date"].diff().dt.days
    for name,keys in {"jockey_win_rate":["jockey"],"trainer_win_rate":["trainer"],"course_win_rate":["course"],"distance_win_rate":["distance"],"surface_win_rate":["surface"],"condition_win_rate":["track_condition"],"course_distance_win_rate":["course","distance"]}.items():
        x[name]=_prior_rate(x,keys,"win",1,19) if all(k in x.columns for k in keys) else 0.05
    x["post_pct"]=(x["post"]-1)/x["field_size"].clip(lower=2)
    x["bracket_pct"]=(x["bracket"]-1)/x["field_size"].clip(lower=2)
    x["odds"]=pd.to_numeric(x.get("odds"),errors="coerce")
    x["market_prob"]=1/x["odds"].clip(lower=1.01)
    return x

def add_features(df):
    x=add_historical_features(df)
    x["season"]=x["race_date"].dt.month.fillna(0).astype(int).astype(str)
    for col in ["early_position","final_position","post","bracket"]:
        if col not in x: x[col]=np.nan
        x[col]=pd.to_numeric(x[col],errors="coerce")
    x["position_change"]=x["early_position"]-x["final_position"]
    x["running_style"]="unknown"
    valid=x["early_position"].notna() & x["field_size"].notna()
    ratio=x.loc[valid,"early_position"]/x.loc[valid,"field_size"].clip(lower=1)
    x.loc[valid & (ratio<=.20),"running_style"]="逃げ"
    x.loc[valid & (ratio>.20) & (ratio<=.45),"running_style"]="先行"
    x.loc[valid & (ratio>.45) & (ratio<=.75),"running_style"]="差し"
    x.loc[valid & (ratio>.75),"running_style"]="追込"
    return x

def compute_running_style_stats(history):
    x=history.sort_values(["race_date","race_key","post"]).copy()
    x["style_win_rate"]=_prior_rate(x,["course","surface","distance","track_condition","running_style"],"win",1,19)
    return x

def compute_track_bias(df):
    x=df.sort_values(["race_date","race_key","post"]).copy()
    x["track_bias_score"]=0.0
    x["pace_score"]=0.0
    if "finish" in x:
        x["finish_pct"]=1-((x["finish"]-1)/x["field_size"].clip(lower=2))
        prior=_prior_rate(x,["course","surface","distance","track_condition","bracket"],"finish_pct",0.5,9.5)
        x["track_bias_score"]=((prior-0.5)*100).fillna(0.0)
    return x
