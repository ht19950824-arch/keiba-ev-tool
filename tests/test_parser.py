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


def test_parse_pdfplumber_control_markers():
    text='''20049 8月 8日 晴良 （2026年2中京） 第5日 第1競走 2歳未勝利 1，600ｍ\n発走 9時50分 （芝・左）\n8 9 ジーティーキャリー 牝2鹿 55 西村 淳也 田畑 利彦氏 松下 武士 安平 ノーザンファーム 466±0 1：34．4 1．4\x03\n'''
    rows=parse_text(text)
    assert len(rows)==1
    assert rows[0]["horse"]=="ジーティーキャリー"
    assert rows[0]["odds"]==1.4


def test_parse_jra_cid_digits():
    text="20049 8月 8日 晴良 （2026年2中京） 第5日 第1競走 2歳未勝利 1，600ｍ\n8 9 ジーティーキャリー 牝2鹿 55 西村 淳也 安平 ノーザンファーム 466±0 1：34．4 1．4\n".replace("20049","(cid:9874)(cid:9872)(cid:9872)(cid:9874)(cid:9879)").replace("8月","(cid:9880)月").replace("8日","(cid:9880)日").replace("2026","(cid:9874)(cid:9872)(cid:9874)(cid:9880)").replace("2中京","(cid:9874)中京").replace("第5日","第(cid:9877)日").replace("第1競走","第(cid:9873)競走")
    rows=parse_text(text)
    assert rows and rows[0]["race_no"]==1 and rows[0]["odds"]==1.4


def test_parse_2018_era_header():
    text='''2802510月 8日 晴良 （30京都4）第3日 第1競走 サラブレッド系2歳 1，800ｍ\n発走 9時55分 （ダート・右）\n3 4 セロシア 牡2黒鹿55 幸 英明 ノースヒルズ 渡辺 薫彦 新冠 ノースヒルズ 450－2 1：54．8 8．5\n5 7 タニノマイカ 牝2黒鹿54 島 良太 谷水 雄三氏 寺島 良 新ひだか 西村 和夫 456＋2 1：55．1 31．7\n'''
    rows=parse_text(text, "2018")
    assert len(rows)==2
    assert rows[0]["race_key"]=="2018-京都-4-28025"
    assert rows[0]["race_date"]=="2018-10-08"
    assert rows[0]["distance"]==1800
    assert rows[0]["course"]=="京都"
