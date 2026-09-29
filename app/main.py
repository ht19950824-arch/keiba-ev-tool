from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
BASE=Path(__file__).resolve().parents[1]
app=FastAPI(title="中央競馬 期待値分析",version="0.3.0")
@app.get("/",response_class=HTMLResponse)
def home(): return (BASE/"web"/"index.html").read_text(encoding="utf-8")
@app.get("/api/status")
def status():
    p=BASE/"data"/"processed"; raw=BASE/"data"/"raw"
    return {"source":"JRA official only","jravan":False,"index_files":len(list(p.glob("jra_*_index.json"))) if p.exists() else 0,"raw_pdfs":len(list(raw.rglob("*.pdf"))) if raw.exists() else 0,"model_ready":(p/"model.joblib").exists()}
