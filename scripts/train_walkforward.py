from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
from joblib import dump
from app.model import fit,predict
from scripts.backtest import evaluate
def load_years(processed,years):
    frames=[]
    for y in years:
        matches=list(processed.rglob(f"runners_{y}.parquet"))
        if matches:
            frames.append(pd.read_parquet(matches[0]))
    if not frames: raise FileNotFoundError("No processed runner parquet files found")
    return pd.concat(frames,ignore_index=True)
def run(train_years,test_year,processed,out,public_dir):
    train=load_years(processed,train_years); test=load_years(processed,[test_year])
    bundle=fit(train); pred=predict(bundle,test)
    out.mkdir(parents=True,exist_ok=True); dump(bundle,out/"model.joblib")
    pred.to_parquet(out/f"predictions_{test_year}.parquet",index=False)
    cols=[c for c in ["race_key","race_date","course","distance","post","bracket","horse","odds","model_win_prob","fair_odds","expected_value","value_edge"] if c in pred.columns]
    pred[cols].to_json(out/f"predictions_{test_year}.json",orient="records",force_ascii=False,indent=2)
    metrics=evaluate(pred,min_ev=1.10,min_odds=3.0)
    (out/f"backtest_{test_year}.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2,default=float),encoding="utf-8")
    public_dir.mkdir(parents=True,exist_ok=True)
    (public_dir/"current_predictions.json").write_text((out/f"predictions_{test_year}.json").read_text(encoding="utf-8"),encoding="utf-8")
    (public_dir/"backtest_current.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2,default=float),encoding="utf-8")
    print(json.dumps(metrics,ensure_ascii=False))
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--train-start",type=int,default=2017); ap.add_argument("--test-year",type=int,required=True); ap.add_argument("--processed",default="data/processed"); ap.add_argument("--out",default="data/processed/model"); ap.add_argument("--public-dir",default="web/data")
    a=ap.parse_args(); run(list(range(a.train_start,a.test_year)),a.test_year,Path(a.processed),Path(a.out),Path(a.public_dir))
