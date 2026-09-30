from __future__ import annotations
import argparse, sqlite3
from pathlib import Path
import pandas as pd
from app.parser import parse_pdf
from scripts.features import add_features, compute_track_bias
SCHEMA=Path(__file__).with_name("schema.sql")
def init_db(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path); con.executescript(SCHEMA.read_text(encoding="utf-8")); return con
def ingest_year(year,raw,processed,db):
    con=init_db(db); rows=[]
    for pdf in sorted((raw/str(year)).glob("*.pdf")):
        try: rows.extend(parse_pdf(pdf))
        except Exception as e: print(f"WARN {pdf}: {e}")
    if not rows:
        con.close()
        raise RuntimeError(f"No runner rows parsed for year {year}")
    raw_df=pd.DataFrame(rows)
    raw_df=raw_df.drop_duplicates(["race_key","post"],keep="first").reset_index(drop=True)
    df=compute_track_bias(add_features(raw_df))
    race_cols=["race_key","race_date","course","meeting_no","race_no","surface","distance","track_condition","field_size"]
    races=df[race_cols].drop_duplicates("race_key")
    drop_cols=["race_date","course","meeting_no","day_no","race_no","surface","distance","track_condition","field_size"]
    runners=df.drop(columns=[c for c in drop_cols if c in df.columns]).copy()
    db_cols=[r[1] for r in con.execute("PRAGMA table_info(runners)").fetchall()]
    runners=runners[[c for c in db_cols if c in runners.columns]]
    for y in sorted(pd.to_datetime(df["race_date"]).dt.year.dropna().unique().tolist()):
        con.execute("DELETE FROM runners WHERE race_key IN (SELECT race_key FROM races WHERE substr(race_date,1,4)=?)",(str(int(y)),))
        con.execute("DELETE FROM races WHERE substr(race_date,1,4)=?",(str(int(y)),))
    races.to_sql("races",con,if_exists="append",index=False); runners.to_sql("runners",con,if_exists="append",index=False)
    con.commit(); con.close()
    processed.mkdir(parents=True,exist_ok=True); df.to_parquet(processed/f"runners_{year}.parquet",index=False)
    return len(df)
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--year",type=int,required=True); ap.add_argument("--raw",default="data/raw"); ap.add_argument("--processed",default="data/processed"); ap.add_argument("--db",default="data/processed/keiba.sqlite")
    a=ap.parse_args(); print(f"rows={ingest_year(a.year,Path(a.raw),Path(a.processed),Path(a.db))}")