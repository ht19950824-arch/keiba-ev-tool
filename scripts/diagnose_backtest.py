from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from app.model import fit, predict
from scripts.backtest import evaluate

def load_years(processed: Path, years: list[int]) -> pd.DataFrame:
    frames=[]
    for y in years:
        p=processed/f"runners_{y}.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p))
    if not frames:
        raise FileNotFoundError("No runner parquet files")
    return pd.concat(frames, ignore_index=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--processed",default="data/processed")
    ap.add_argument("--test-year",type=int,default=2026)
    ap.add_argument("--min-ev",type=float,default=1.20)
    ap.add_argument("--min-odds",type=float,default=3.0)
    a=ap.parse_args()
    processed=Path(a.processed)
    train=load_years(processed,list(range(2017,a.test_year)))
    test=load_years(processed,[a.test_year])
    bundle=fit(train)
    pred=predict(bundle,test)
    odds=pd.to_numeric(pred["odds"],errors="coerce")
    finish=pd.to_numeric(pred["finish"],errors="coerce")
    win=(finish==1)
    print("ROWS",len(pred))
    print("RACES",pred["race_key"].nunique())
    print("ALL_WIN_RATE",float(win.mean()))
    print("ODDS_COUNT",int(odds.notna().sum()))
    print("ODDS_MIN",float(odds.min()))
    print("ODDS_MEDIAN",float(odds.median()))
    print("ODDS_MAX",float(odds.max()))
    print("FINISH_1_COUNT",int(win.sum()))
    print("FINISH_1_RATE",float(win.mean()))
    print("UNIQUE_HORSE_RACE",pred[["race_key","horse"]].drop_duplicates().shape[0])
    sums=pred.groupby("race_key")["model_win_prob"].sum()
    print("PREDICTION_SUM_MIN",float(sums.min()))
    print("PREDICTION_SUM_MAX",float(sums.max()))
    m=evaluate(pred,a.min_ev,a.min_odds)
    print("STRICT_BACKTEST",json.dumps(m,ensure_ascii=False,sort_keys=True))
    picks=pred[(pred["expected_value"]>=a.min_ev)&(odds>=a.min_odds)].copy()
    print("PICKS",len(picks))
    print("PICKS_WIN_COUNT",int((pd.to_numeric(picks["finish"],errors="coerce")==1).sum()))
    print("PICKS_FINISH_COUNTS",pd.to_numeric(picks["finish"],errors="coerce").value_counts().sort_index().head(15).to_dict())
    print("PICKS_ODDS_DESCRIBE",odds.loc[picks.index].describe().to_dict())
    if len(picks):
        print("PICKS_BY_RACE_MAX",int(picks.groupby("race_key").size().max()))
        print("PICKS_BY_RACE_MEAN",float(picks.groupby("race_key").size().mean()))
    flags=[]
    if len(picks)>=50 and float((pd.to_numeric(picks["finish"],errors="coerce")==1).mean())>0.5:
        flags.append("selected_win_rate_above_50pct")
    if float((sums-1).abs().max())>1e-6:
        flags.append("race_probability_not_normalized")
    if len(pred[["race_key","horse"]].drop_duplicates()) != len(pred):
        flags.append("duplicate_race_horse_rows")
    print("SANITY_FLAGS",json.dumps(flags,ensure_ascii=False))

if __name__=="__main__":
    main()
