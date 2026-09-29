from __future__ import annotations
import argparse
import numpy as np
import pandas as pd

def evaluate(df:pd.DataFrame,min_ev:float=1.20,min_odds:float=3.0)->dict:
    x=df.copy(); x["odds"]=pd.to_numeric(x["odds"],errors="coerce"); x["model_win_prob"]=pd.to_numeric(x["model_win_prob"],errors="coerce"); x["finish"]=pd.to_numeric(x["finish"],errors="coerce")
    x["ev"]=x["model_win_prob"]*x["odds"]
    picks=x[(x["ev"]>=min_ev)&(x["odds"]>=min_odds)].copy()
    picks["stake"]=1.0; picks["return"]=np.where(picks["finish"]==1,picks["odds"],0.0)
    stake=float(picks["stake"].sum()); ret=float(picks["return"].sum())
    return {"bets":int(len(picks)),"stake":stake,"return":ret,"roi":ret/stake if stake else np.nan,"hit_rate":float((picks["finish"]==1).mean()) if len(picks) else np.nan}

def chronological_split(df:pd.DataFrame,test_year:int):
    d=pd.to_datetime(df["race_date"],errors="coerce")
    return df[d.dt.year<test_year].copy(),df[d.dt.year==test_year].copy()

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--test-year",type=int,required=True); ap.add_argument("--min-ev",type=float,default=1.20); ap.add_argument("--min-odds",type=float,default=3.0)
    a=ap.parse_args(); _,test=chronological_split(pd.read_csv(a.csv),a.test_year); print(evaluate(test,a.min_ev,a.min_odds))
