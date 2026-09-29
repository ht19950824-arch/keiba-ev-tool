from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC=["age","weight_carried","horse_weight","horse_weight_diff","post","bracket","distance","field_size","days_since_last","last_finish","last3_avg_finish","last3_avg_margin","last3_avg_speed","early_position","final_position","position_change","last3f_rank","track_bias_score","pace_score","horse_win_rate","jockey_win_rate","trainer_win_rate","course_win_rate","distance_win_rate","surface_win_rate","condition_win_rate","course_distance_win_rate","post_pct","bracket_pct","class_score"]
CATEGORICAL=["course","surface","track_condition","sex","running_style","class_name","season","meeting_no"]

@dataclass
class ModelBundle:
    pipeline: Pipeline
    features: list[str]

def build_pipeline():
    pre=ColumnTransformer([
        ("num",SimpleImputer(strategy="median"),NUMERIC),
        ("cat",Pipeline([("imputer",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore",sparse_output=False))]),CATEGORICAL)
    ],remainder="drop")
    clf=HistGradientBoostingClassifier(learning_rate=.045,max_iter=350,max_leaf_nodes=31,l2_regularization=1.5,random_state=42)
    return Pipeline([("pre",pre),("model",clf)])

def fit(df):
    features=NUMERIC+CATEGORICAL
    pipe=build_pipeline()
    pipe.fit(df.reindex(columns=features),df["win"].astype(int))
    return ModelBundle(pipe,features)

def predict(bundle,df):
    out=df.copy()
    raw=bundle.pipeline.predict_proba(out.reindex(columns=bundle.features))[:,1]
    out["raw_model_win_prob"]=raw
    if "race_key" in out:
        totals=out.groupby("race_key")["raw_model_win_prob"].transform("sum")
        out["model_win_prob"]=raw/totals.replace(0,np.nan)
    else:
        out["model_win_prob"]=raw/(raw.sum() if raw.sum() else 1)
    out["fair_odds"]=1/out["model_win_prob"].clip(lower=1e-9)
    if "odds" in out:
        odds=pd.to_numeric(out["odds"],errors="coerce")
        out["market_prob"]=1/odds.clip(lower=1.01)
        out["expected_value"]=out["model_win_prob"]*odds
        out["value_edge"]=out["model_win_prob"]-out["market_prob"]
    return out
