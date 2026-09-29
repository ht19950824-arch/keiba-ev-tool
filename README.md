# 中央競馬 期待値分析ツール

JRA-VAN/JV-Linkを使用せず、JRA公式公開情報を中心に中央競馬の勝率・期待値を分析する基盤です。

## 方針
- 確定後の単勝オッズ・人気は予測モデルの入力に使わず、市場価格との比較にのみ使う。
- 対象レースより未来の情報を特徴量へ混入させない。
- 時系列バックテストを必須にする。
- 回収率150%は目標値であり、保証しない。
- 高カーディナリティな騎手・調教師・血統は履歴集計特徴量として扱う。
- JRA公式PDF等の利用条件を確認し、必要以上の原文再配布を避ける。

## 現在
v0.3の基盤をGitHubへ移行中。JRA年度別成績PDFの索引収集、PDFパーサー、特徴量、モデル、バックテスト、iPhone向けWeb UIを順次自動化します。

## 起動
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

データ源: https://www.jra.go.jp/datafile/seiseki/index.html
