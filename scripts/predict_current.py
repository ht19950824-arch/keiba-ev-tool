from __future__ import annotations
import argparse,json,re
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import load
from app.model import predict
def flatten_current(path):
    raw=json.loads(path.read_text(encoding="utf-8")); rows=[]
    for idx,race in enumerate(raw.get("races",[])):
        meta=race.get("meta",{}).copy()
        meta["race_key"]=f"{meta.get('race_date','unknown')}-{meta.get('course','unknown')}-{meta.get('meeting_no','unknown')}-{meta.get('race_no',idx)}"
        for row in race.get("rows",[]):
            name=next((v for k,v in row.items() if "馬名" in k),None)
            if name: rows.append({**row,**meta,"race_label":race.get("label","")})
    return pd.DataFrame(rows)
def parse_num(s):
    m=re.search(r"-?\d+(?:\.\d+)?",str(s)); return float(m.group()) if m else np.nan
def recent_finish(s):
    m=re.search(r"(\d+)着",str(s)); return float(m.group(1)) if m else np.nan
def build_current(x,history):
    x=x.copy()
    col=lambda f: next((c for c in x.columns if f in c),None)
    name_col,age_col,weight_col,jockey_col,odds_col=map(col,["馬名","性齢","負担重量","騎手","単勝オッズ"])
    x["horse"]=x[name_col].astype(str).str.extract(r"^([^0-9]+)")[0].str.strip() if name_col else ""
    x["age"]=x[age_col].map(lambda s: parse_num(re.search(r"[牡牝セ]\s*(\d+)",str(s)).group(1)) if re.search(r"[牡牝セ]\s*(\d+)",str(s)) else np.nan) if age_col else np.nan
    x["sex"]=x[age_col].map(lambda s: next((z for z in ["牡","牝","セ"] if z in str(s)),"unknown")) if age_col else "unknown"
    x["weight_carried"]=x[weight_col].map(parse_num) if weight_col else np.nan; x["jockey"]=x[jockey_col].astype(str) if jockey_col else ""; x["odds"]=x[odds_col].map(parse_num) if odds_col else np.nan
    x["post"]=pd.to_numeric(x.get("馬番",np.nan),errors="coerce"); x["bracket"]=pd.to_numeric(x.get("枠",np.nan),errors="coerce"); x["race_group"]=x["race_date"].astype(str)+"|"+x["course"].astype(str)+"|"+x["race_no"].astype(str); x["field_size"]=x.groupby("race_group")["horse"].transform("count")
    history=history.copy(); history["race_date"]=pd.to_datetime(history["race_date"],errors="coerce"); history["win"]=(pd.to_numeric(history["finish"],errors="coerce")==1).astype(int)
    for key,name in [("horse","horse_win_rate"),("course","course_win_rate"),("distance","distance_win_rate"),("surface","surface_win_rate"),("track_condition","condition_win_rate")]:
        if key in history.columns and key in x.columns:
            g=history.groupby(key)["win"].agg(["sum","count"]); x[name]=x[key].map(((g["sum"]+1)/(g["count"]+20)).to_dict()).fillna(.05)
        else: x[name]=.05
    # Use historical outcomes available before the current race.
    if "jockey" in history.columns and "jockey" in x.columns:
        g=history.groupby("jockey")["win"].agg(["sum","count"])
        x["jockey_win_rate"]=x["jockey"].map(((g["sum"]+1)/(g["count"]+20)).to_dict()).fillna(.05)
    else:
        x["jockey_win_rate"]=.05
    if "course" in history.columns and "distance" in history.columns and "course" in x.columns and "distance" in x.columns:
        h=history.copy()
        h["_cd"]=h["course"].astype(str)+"|"+pd.to_numeric(h["distance"],errors="coerce").astype("Int64").astype(str)
        g=h.groupby("_cd")["win"].agg(["sum","count"])
        x["_cd"]=x["course"].astype(str)+"|"+pd.to_numeric(x["distance"],errors="coerce").astype("Int64").astype(str)
        x["course_distance_win_rate"]=x["_cd"].map(((g["sum"]+1)/(g["count"]+20)).to_dict()).fillna(.05)
    else:
        x["course_distance_win_rate"]=.05
    x["trainer_win_rate"]=.05
    recent_cols=[c for c in x.columns if any(k in c for k in ["前走","前々走","3走前","4走前"])]
    recent_values=x[recent_cols].map(recent_finish) if recent_cols else pd.DataFrame(index=x.index)
    x["last_finish"]=recent_values.iloc[:,0] if not recent_values.empty else np.nan
    x["last3_avg_finish"]=recent_values.iloc[:,:3].mean(axis=1) if not recent_values.empty else np.nan
    x["days_since_last"]=np.nan
    for c in ["horse_weight","horse_weight_diff","last3_avg_margin","last3_avg_speed","early_position","final_position","position_change","last3f_rank"]: x[c]=np.nan
    x["track_bias_score"]=0.; x["pace_score"]=0.; x["post_pct"]=(x["post"]-1)/x["field_size"].clip(lower=2); x["bracket_pct"]=(x["bracket"]-1)/x["field_size"].clip(lower=2)
    x["track_condition"]="unknown"; x["running_style"]="unknown"; x["class_name"]="unknown"; x["season"]=pd.Timestamp.now().month.__str__(); x["class_score"]=0.; x["meeting_no"]=x.get("meeting_no","unknown").astype(str)
    return x
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--entries",default="data/processed/current_entries.json"); ap.add_argument("--model",default="data/processed/model/model.joblib"); ap.add_argument("--history-glob",default="data/processed/runners_*.parquet"); ap.add_argument("--out",default="web/data/current_predictions.json"); a=ap.parse_args()
    current=flatten_current(Path(a.entries)); paths=sorted(Path("data/processed").rglob("runners_*.parquet"))
    if current.empty or not paths: Path(a.out).write_text("[]",encoding="utf-8"); return
    history=pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True); out=predict(load(a.model),build_current(current,history))
    cols=[c for c in ["race_key","race_label","race_date","course","race_no","post","horse","odds","model_win_prob","fair_odds","expected_value","value_edge"] if c in out]
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); out[cols].sort_values(["expected_value"],ascending=False,na_position="last").to_json(a.out,orient="records",force_ascii=False,indent=2)
if __name__=="__main__": main()
