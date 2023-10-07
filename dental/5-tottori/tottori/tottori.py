###  Import Modules

from bs4 import BeautifulSoup
import requests
import jaconv
import re
import json
import csv
import time
import datetime
from dateutil.parser import parse
from normalize_japanese_addresses import normalize
import numpy as np
import builtins


###  Global Variables

WAIT_SEC = 15
Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', 
       '最終更新日', 'url', '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', 
       '小児歯科領域一覧', '矯正歯科領域一覧','施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', 
       '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', '歯科助手(総数|常勤|非常勤)', 
       '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

Get_ClinicId_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/?dayofweek=&departmentcategoryid=10&languagelevel=%E2%97%8E&kenshin_keyword=&searchtype=function&gairai_keyword=&objecttype=1%2C2%2C4&requestpage="



###  Functions

## Functions  predefined
# -------------------------------------------------------------------------------------
def _normalization(arg):
    """
    文字列の正規化を行う内部関数。
    ひらがなをカタカナに、全角を半角に、大文字を小文字に変換し、不可視文字も削除する。
    """

    try:
        # ひらがなをカタカナに変換
        try:
            result = jaconv.hira2kata(arg)
        except AttributeError:
            result = arg

        # 全角を半角に変換
        try:
            result = jaconv.z2h(result, digit=True, ascii=True)
        except AttributeError:
            result = result

        # 大文字を小文字に変換
        try:
            result = result.lower()
        except AttributeError:
            result = result

        # スペースと不可視文字を削除
        try:
            result = _str_clean(result)
        except TypeError:
            result = result

    except:
        result = arg

    return result

def normalization(arg):
    # print(2, arg)
    """
    文字列または文字列のリストを正規化する。
    """

    # 内部関数をNumPyのufuncに変換
    _func = np.frompyfunc(_normalization, 1, 1)

    # リストをNumPy配列に変換
    _list = np.array(arg, dtype="object")

    # 結果を取得
    result = _func(_list)

    # データ型を変換
    result = result if type(result) == str else result.tolist() if type(result) == np.ndarray else "error"

    return result

# -------------------------------------------------------------------------------------
def _str_clean(arg):
    """
    文字列のスペースと不可視文字を削除する内部関数。
    """

    try:
        result = arg.strip()
    except:
        result = arg

    try:
        result = re.sub(r"\r|\n|\r\n|\u3000|\t|　| |,", " ", result)
    except TypeError:
        result = result

    return result

# -------------------------------------------------------------------------------------
def str_clean(arg):
    """
    文字列または文字列のリストのスペースと不可視文字を削除する。
    """

    # 内部関数をNumPyのufuncに変換
    _func = np.frompyfunc(_str_clean, 1, 1)

    # リストをNumPy配列に変換
    _list = np.array(arg, dtype="object")

    # 結果を取得
    result = _func(_list)

    # データ型を変換
    result = result if type(result) == str else result.tolist() if type(result) == np.ndarray else "error"

    return result

# -------------------------------------------------------------------------------------
def _split_buildingName(arg):
    # print(1, arg)
    """
    建物名を切り分ける内部関数。
    """
    ## ハイフンの一般化
    address = normalization(arg)
    hyphens = '-˗ᅳ᭸‐‑‒–—―⁃⁻−▬─━➖ーㅡ﹘﹣－ｰ𐄐𐆑 '
    address = re.sub("|".join(hyphens), "-", address)
    address = re.sub(r"([ｱ-ﾝ])(-)",r"\1ｰ", address)

    ## 丁目、番地、号などで使われる漢字の定義
    chome_poplist = ["ﾉ切","町目","地割","丁目","丁","組","番町","番地","番目","番","号室","号","街区","画地"]
    chome_popset = r"|".join(chome_poplist)
    chome_holdlist = ["条東","条西","条南","条北","条通","条","東","西","南","北"]
    chome_holdset = r"|".join(chome_holdlist)
    chome_alllist = chome_popset + chome_holdset
    chome_allset = r"|".join(chome_alllist)

    ## separate address
    result = re.findall(re.compile(f"(.*\d\[{chome_allset}\]*)|(\D+\[-\d\]+)|(.*)"), address)

    ## convert kanji into hyphen
    result = [[re.sub(f"(\d+)({chome_popset})", r"\1-", "".join(t)) for t in tl] for tl in result]

    ## concat all
    result = ["".join(t) for t in result]
    result = "".join(result)

    ## special case handling (1ﾉ3 1区1)
    result = re.sub(r"([^ｱｰﾝ])(ﾉ|ｰ)(\d)", r"\1-\3", result)
    result = re.sub(r"(\d)(区)(\d)", r"\1-\3", result)
    result = re.sub("--", "-", result)

    ## separate into [japanese] + [number + hyphen] chunks
    result = re.findall(re.compile(f"(\D+[-\d]+[{chome_holdset}]*[-\d]+)|(\D+[-\d]+)|(.*)"), result)
    result = [t for t in ["".join(tl) for tl in result] if t != ""]
    # print(3, result)
    ## merge [number + hyphen] chunks
    try:
        result = [result[0]] + ["".join(result[1:])]
    except:
        result = result

    # 2列目が単独「f, 階」のとき、1列目の末尾数を2列目へ移動
    if re.fullmatch(r"f|階", result[1]):
        result[1] = "".join(re.compile(r"\d+$").findall(result[0])) + result[1]
        result[0] = re.sub(r"\d+$", "", result[0])

    # 2列目で、階数が番地と結合してしまっているとき、階数を1桁とみなし、残りの数字を番地として1列目へ移動
    if (re.fullmatch(r"\D+", result[0]) or re.search(r"-$", result[0])) and re.match(r"(\d*)(\d)(f|階)(\d*)", result[1]):
        result[1] = re.sub(r"(\d*)(\d)(f|階)(\d*)", r"\1,\2\3\4", result[1])
        result[0] = result[0] + result[1][:result[1].find(",")]
        result[1] = result[1][result[1].find(",")+1:]

    # 末尾のハイフンを削除
    result[0] = re.sub(r"-+$", "", result[0])

    return result


def get_page(url):
    response = requests.get(url, timeout = 20)
    if response.status_code == 200:
        return response
    else:
        get_page(url)

def get_base_data(html):
    html_info = BeautifulSoup(html, 'lxml')
    timeStamp = datetime.date.today()

    baseData = {
        'timestamp': timeStamp
    }

    try:
        storename = html_info.find("caption", string="1. 診療所の名称").find_next_sibling('tr').find_next_sibling('tr').find('td').text.strip().replace(" ", "").replace("\n", "")
    except:
        storename = "na"
    
    try:
        updateDate = html_info.find('span', {'style': 'font-size:80%;'}).text.replace("最終更新日：", "").replace("（", "").replace("）", "").replace("\n", "").replace(" ", "").replace("\r", "")
    except:
        updateDate = "na"
    
    try:
        founder_text = html_info.find("th", string="診療所の名称").find_next_sibling('td').text
        if "法人" in founder_text:
            founder_type = founder_text[:founder_text.index('法人')].replace("\n", "").replace("\t", "") + "法人"
        else :
            founder_type = "個人"
    except:
        founder_type = "個人"

    try:
        founder_name = html_info.find("caption", string="2. 診療所の開設者").find_next_sibling('tr').find_next_sibling('tr').find('td').text.strip().replace("\n", "").replace(" ", "")
    except:
        founder_name = "na"

    try:
        admin_name = html_info.find("caption", string="3. 診療所の管理者").find_next_sibling('tr').find_next_sibling('tr').find('td').text.strip().replace("\n", "").replace(" ", "")
    except:
        admin_name = "na"

    try:
        # address_original = html_info.find("th", string="住所").find_next_sibling('td').text.strip().replace("\n", "").replace(" ", "").replace("鳥取県","")
        address_original = html_info.find("caption", string="4. 診療所の所在地").find_next_sibling('tr').find_next_sibling('tr').find_next_sibling('tr').find("td").text.strip().replace("\n", "").replace(" ", "")
    except:
        address_original = "na"
    try:
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_0 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_0 = address_normalize_1 = "na"

    try:
        general_dentistry = "["
        try:
            general_dentistry_list = ['1. 歯科領域の一次診療', '2. 成人の歯科矯正治療', '3. 唇顎口蓋裂の歯科矯正治療', '4. 顎変形症の歯科矯正治療', '5. 障がい者等の歯科治療', '6. 摂食機能障害の治療']
            for item in general_dentistry_list:
                gerneral_ths = html_info.find("caption", string="23. 対応することができる疾患又は治療の内容").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                for gerneral_th in gerneral_ths:
                    if gerneral_th.text.strip() == item:
                        td_text = gerneral_th.find_next_sibling('td').text.strip()
                        if "◯" in td_text or "○" in td_text:
                            general_dentistry += (item + ", ")
        except:
            print('not found')
        general_dentistry += "]"
    except:
        general_dentistry = "na"

    try:
        oral_surgery = "["
        try:
            oral_surgery_list = ['1. 埋伏歯抜歯', '2. 顎関節症治療', '3. 顎変形症治療', '4. 顎骨骨折治療', '5. 口唇・舌・口腔粘膜の炎症・外傷・腫瘍の治療', '6. 唇顎口蓋裂治療']
            for item in oral_surgery_list:
                gerneral_ths = html_info.find("caption", string="23. 対応することができる疾患又は治療の内容").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                for gerneral_th in gerneral_ths:
                    if gerneral_th.text.strip() == item:
                        td_text = gerneral_th.find_next_sibling('td').text.strip()
                        if "◯" in td_text or "○" in td_text:
                            oral_surgery += (item + ", ")
        except:
            print('not found')
        oral_surgery += "]"
    except:
        oral_surgery = "na"


    try:
        has_structure = "["
        try:
            has_structure_list = ['駐車場の有無', '1. 手話による対応', '2. 施設内の情報の表示', '3. 音声による情報の伝達', '4. 施設内点字ブロックの設置', '5. 点字による表示', '施設のバリアフリー化の実施', '車椅子等利用者用駐車施設の有無', '多機能トイレの設置', '1. 施設内における全面禁煙の実施', '2. 健康増進法第28条第13号に規定する特定屋外喫煙場所の設置']
            for item in has_structure_list:
                gerneral_ths = html_info.find("caption", string="10. 診療所の駐車場").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                gerneral_ths += html_info.find("caption", string="16. 障がい者に対するサービス内容").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                gerneral_ths += html_info.find("caption", string="17. 車椅子等利用者に対するサービス内容").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                gerneral_ths += html_info.find("caption", string="18. 受動喫煙を防止するための措置").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                for gerneral_th in gerneral_ths:
                    if gerneral_th.text.strip() == item:
                        td_text = gerneral_th.find_next_sibling('td').text.strip()
                        if "◯" in td_text or "○" in td_text or "有" in td_text:
                            has_structure += (item + ", ")
        except:
            print('not found')
        has_structure += "]"
    except:
        has_structure = "na"
        
    try:
        anesthesia_treatment = "["
        try:
            anesthesia_treatment_list = ['1. 麻酔科標榜医による麻酔（麻酔管理）', '2. 全身麻酔', '3. 硬膜外麻酔', '4. 脊椎麻酔', '5. 神経ブロック']
            for item in anesthesia_treatment_list:
                gerneral_ths = html_info.find("caption", string="23. 対応することができる疾患又は治療の内容").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
                for gerneral_th in gerneral_ths:
                    if gerneral_th.text.strip() == item:
                        td_text = gerneral_th.find_next_sibling('td').text.strip()
                        if "◯" in td_text or "○" in td_text:
                            anesthesia_treatment += (item + ", ")
        except:
            print('not found')
        anesthesia_treatment += "]"
    except:
        anesthesia_treatment = "na"

    try:
        home_care = "["
        affiliate_check = "["
        affiliate_list = ['1. 病院との連携', '2. 診療所との連携', '3. 訪問看護ステーションとの連携', '4. 居宅介護支援事業所との連携', '5. 薬局との連携']
        try:
            gerneral_tds = html_info.find("caption", string="26. 対応することができる在宅医療").find_parent('table', {'class': 'search_detail_table'}).find_all('td')
            for gerneral_td in gerneral_tds:
                td_text = gerneral_td.text.strip()
                if "◯" in td_text or "○" in td_text:
                    item = gerneral_td.find_previous_sibling('th').text.strip()
                    if item in affiliate_list:
                        affiliate_check += (item + ", ")
                    else:
                        home_care += (item + ", ")
        except:
            print('not found')
        home_care += "]"
        affiliate_check += "]"
    except:
        home_care = "na"
        affiliate_check = "na"

    dentist = '-'
    dental_hygienist = '-'
    try:
        person_ths = html_info.find("caption", string="28.歯科診療所の人員配置(常勤換算後) ").find_parent('table', {'class': 'search_detail_table'}).find_all('th')
        for person_th in person_ths:
            person_th_text = person_th.text.strip()
            if person_th_text == '2.歯科医師':
                dentist = person_th.find_next_sibling('td').text.strip()
                if dentist == '':
                    dentist = "-"
            elif person_th_text == '7.歯科衛生士':
                dental_hygienist = person_th.find_next_sibling('td').text.strip()
                if dental_hygienist == '':
                    dental_hygienist = "-"
    except:
        dentist = "-"
        dental_hygienist = "-"

    dental_technician = "-"
    dental_assistant = "-"

    try:
        average_people_count = html_info.find("caption", string="6. 外来患者数").find_next_sibling('tr').find('td').text.strip().replace(" ", "").replace("\n", "")
    except:
        average_people_count = "na"


    baseData['storename'] = storename
    baseData['updateDate'] = updateDate
    baseData['founder_type'] = founder_type
    baseData['founder_name'] = founder_name
    baseData['admin_name'] = admin_name
    baseData['address_original'] = address_original
    baseData['address_normalize[0]'] = address_normalize_0
    baseData['address_normalize[1]'] = address_normalize_1
    baseData['general_dentistry'] = general_dentistry
    baseData['oral_surgery'] = oral_surgery
    baseData['pediatric_dentistry'] = "na"
    baseData['orthodontic_dentistry'] = "na"
    baseData['has_structure'] = has_structure
    baseData['anesthesia_treatment'] = anesthesia_treatment
    baseData['home_care'] = home_care
    baseData['affiliate_check'] = affiliate_check
    baseData['dentist'] = dentist + '|-|-'
    baseData['dental_technician'] = dental_technician + '|-|-'
    baseData['dental_assistant'] = dental_assistant + '|-|-'
    baseData['dental_hygienist'] = dental_hygienist + '|-|-'
    baseData['average_people_count'] = average_people_count
    baseData['longitude'] = "na"
    baseData['latitude'] = "na"
    baseData['medical_department'] = ["歯科領域", "口腔外科領域"]
    # print(baseData)

    return baseData






def init():
    f = open("urls.txt", "r")
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "tottori" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)

    for line in f:
        page = line.split(',')[0]
        url = line.split(',')[1]
        data = {}
        print(url)

        baseInfo = get_page(url)
        if baseInfo.status_code == 200:
            baseData = get_base_data(baseInfo.text)
        
        data=[
            baseData['timestamp'],
            baseData['storename'],
            baseData['address_original'],
            baseData['address_normalize[0]'],
            baseData['address_normalize[1]'],
            baseData['updateDate'],
            url,
            baseData['founder_type'],
            baseData['founder_name'],
            baseData['admin_name'],
            baseData['general_dentistry'],
            baseData['oral_surgery'],
            baseData['pediatric_dentistry'],
            baseData['orthodontic_dentistry'],
            baseData['has_structure'],
            baseData['anesthesia_treatment'],
            baseData['home_care'],
            baseData['affiliate_check'],
            baseData['dentist'],
            baseData['dental_technician'],
            baseData['dental_assistant'],
            baseData['dental_hygienist'],
            baseData['average_people_count'],
            baseData['longitude'],
            baseData['latitude'],
            page,
            baseData['medical_department']
        ]
        
        writer.writerow(data)



    # url = 'https://medinfo.pref.tottori.lg.jp/ComDisp/dental_03_view.php?ID=76'
    # baseInfo = get_page(url)
    # if baseInfo.status_code == 200:
    #     print(baseInfo.text)
    #     # baseData = get_base_data(baseInfo.text)
    
    # detail_file = open("detail.html", "ab")
    # detail_file.write(baseInfo.content)
    # detail_file.close()

init()
