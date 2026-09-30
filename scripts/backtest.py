from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

def evaluate(df:pd.DataFrame,min_ev:float=1.20,min_odds:float=3.0)->dict:
    x=df.copy()
    required=["odds","model_win_prob","finish"]
    missing=[c for c in required if c not in x.columns]
    if missing:
        raise ValueError(f"Missing backtest columns: {missing}")
    for c in required:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna(subset=required).copy()
    x=x[(x["odds"]>0)&(x["model_win_prob"]>=0)&(x["model_win_prob"]<=1)].copy()
    if "race_key" in x.columns and "horse" in x.columns:
        x=x.drop_duplicates(subset=["race_key","horse"],keep="last")
    if "field_size" in x.columns:
        fs=pd.to_numeric(x["field_size"],errors="coerce")
        x=x[(fs.isna())|((x["finish"]>=1)&(x["finish"]<=fs))].copy()
    x["ev"]=x["model_win_prob"]*x["odds"]
    picks=x[(x["ev"]>=min_ev)&(x["odds"]>=min_odds)].copy()
    picks["stake"]=1.0
    picks["return"]=np.where(picks["finish"]==1,picks["odds"],0.0)
    stake=float(picks["stake"].sum()); ret=float(picks["return"].sum())
    market_hit=float((1/picks["odds"]).mean()) if len(picks) else np.nan\n    brier=float(((picks["model_win_prob"]-(picks["finish"]==1).astype(float))**2).mean()) if len(picks) else np.nan
    hit=float((picks["finish"]==1).mean()) if len(picks) else np.nan
    race_count=int(picks["race_key"].nunique()) if "race_key" in picks.columns else None
    max_bets_per_race=int(picks.groupby("race_key").size().max()) if "race_key" in picks.columns and len(picks) else None
    return {
        "bets":int(len(picks)),"races":race_count,"stake":stake,"return":ret,
        "roi":ret/stake if stake else np.nan,"hit_rate":hit,
        "market_implied_hit_rate":market_hit,
        "hit_rate_minus_market":hit-market_hit if np.isfinite(hit) and np.isfinite(market_hit) else np.nan,
        "max_bets_per_race":max_bets_per_race,\n        "brier_score":brier,
        "quality_warning":bool(len(picks)>=50 and np.isfinite(hit) and np.isfinite(market_hit) and hit>market_hit*2.0),
    }

def chronological_split(df:pd.DataFrame,test_year:int):
    d=pd.to_datetime(df["race_date"],errors="coerce")
    return df[d.dt.year<test_year].copy(),df[d.dt.year==test_year].copy()

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--test-year",type=int,required=True); ap.add_argument("--min-ev",type=float,default=1.20); ap.add_argument("--min-odds",type=float,default=3.0)
    a=ap.parse_args(); _,test=chronological_split(pd.read_csv(a.csv),a.test_year); print(evaluate(test,a.min_ev,a.min_odds))
