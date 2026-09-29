from app.parser import parse_text

def test_parse_jra_sample():
    text='''03056 2月15日 晴 良 （2026年1東京） 第6日 第1競走 3歳未勝利 1，300ｍ
発走10時05分 （ダート・左）
7 14 ジャックナダル 牡3栗 57 R．キング 辻 高史氏 伊坂 重信 日高 クラウン日高牧場 522－6 1：18．1 3．6
1 2 トヨサカエ 牡3鹿 57 吉田 豊 中村 勝重氏 高橋 文雅 新冠 松浦牧場 470＋2 1：19．1 4．1
'''
    rows=parse_text(text)
    assert len(rows)==2
    assert rows[0]["race_key"]=="2026-東京-1-03056"
    assert rows[0]["post"]==14
    assert rows[0]["horse"]=="ジャックナダル"
    assert rows[0]["horse_weight"]==522
    assert rows[0]["horse_weight_diff"]==-6
    assert rows[0]["finish"]==1
    assert rows[0]["odds"]==3.6
