###  Import Modules

from bs4 import BeautifulSoup
import requests
import jaconv
import re
import json
import csv
import time
import datetime
# from dateutil.parser import parse
from normalize_japanese_addresses import normalize
import numpy as np
import builtins


###  Global Variables

WAIT_SEC = 15
f = open("urls.txt", "r")

Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', 
      '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
      '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', 
      '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

base_url = 'https://www.qq.pref.mie.lg.jp/qq24/qqport/kenmintop/detail/fk1102.php?kinouid=fk9127&sisetuid='

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

# -------------------------------------------------------------------------------------
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


## Functions  get Dental Clinic Info

# -------------------------------------------------------------------------------------
def get_info_html(page):
    response = requests.get(page, timeout = 20)
    if response.status_code == 200:
        return response
    else:
        get_info_html(page)

def get_base_data(detailHtml):

    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')
    timeStamp = datetime.date.today()

    try:
        storename = html_info.find('table', {'summary': '医療機関名称'}).find_all('tr')[1].find('td').text.strip()
    except:
        storename = "na"
    try:
        address_original = html_info.find('table', {'summary': '医療機関の所在地詳細'}).find_all('tr')[2].find('td').text.strip().replace("　"," ").replace("新潟県","")
    except:
        address_original = "na"
    try:
        original = "新潟県" + address_original
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_1 = address_normalize_2 = "na"


    try:
        founder_text = html_info.find('table', {'summary': '医療機関の開設者名'}).find_all("tr")[1].find('td').text.strip()
        check_type = "法人" in founder_text
        if check_type:
            founder_type = founder_text[:founder_text.index('法人')].replace("\n", "").replace("\t", "") + "法人"
            founder_name = founder_text[founder_text.index('法人') + 2:].strip().replace('\u3000', ' ')
        else :
            founder_type = "個人"
            founder_name = founder_text.strip().replace('\u3000', ' ')
    except:
        founder_type = "na"
        founder_name = "na"
    try:
        admin_name = html_info.find('table', {'summary': '医療機関管理者'}).find_all("tr")[1].find('td').text.strip()
    except:
        admin_name = "na"
    try:
        updateDate = html_info.find('div', {'class': 'FDRegister'}).find_all("p")[0].text.replace("最終報告日：","")
    except:
        updateDate = "na"

    try:
        general_dentistry = "["
        general_tds = html_info.find('table', {'summary': '歯科領域一覧'}).find_all('td')
        for general_td in general_tds:
            general_dentistry += (general_td.text.strip() + ", ")
        general_dentistry += "]"
    except:
        general_dentistry = "na"
    try:
        oral_surgery = "["
        general_tds = html_info.find('table', {'summary': '口腔外科領域一覧'}).find_all('td')
        for general_td in general_tds:
            oral_surgery += (general_td.text.strip() + ", ")
        oral_surgery += "]"
    except:
        oral_surgery = "na"
    try:
        pediatric_dentistry = "["
        general_tds = html_info.find('table', {'summary': '小児歯科領域一覧'}).find_all('td')
        for general_td in general_tds:
            pediatric_dentistry += (general_td.text.strip() + ", ")
        pediatric_dentistry += "]"
    except:
        pediatric_dentistry = "na"
    try:
        orthodontic_dentistry = "["
        general_tds = html_info.find('table', {'summary': '矯正歯科領域一覧'}).find_all('td')
        for general_td in general_tds:
            orthodontic_dentistry += (general_td.text.strip() + ", ")
        orthodontic_dentistry += "]"
    except:
        orthodontic_dentistry = "na"

    try:
        has_structure = "["
        general_td = html_info.find('table', {'summary': '駐車場'}).find_all('tr')[0].find('td')
        if general_td.text.strip() == '有り':
            has_structure += (general_td.find_previous_sibling('th').text.strip().replace('\r', '').replace('\n', '').replace(' ', '') + ", ")
        general_tds = html_info.find('div', {'id': 'body-tab3'}).find_all('td', string="有り")
        for general_td in general_tds:
            has_structure += (general_td.find_previous_sibling('th').text.strip().replace('\r', '').replace('\n', '').replace(' ', '') + ", ")
        has_structure += "]"
    except:
        has_structure = "na"

    try:
        home_care = "["
        general_tds = html_info.find('table', {'summary': '在宅医療'}).find_all('td')
        for general_td in general_tds:
            if general_td.text.strip() == "実施":
                home_care += (general_td.find_previous_sibling('th').text.strip() + ", ")
        home_care += "]"
    except:
        home_care = "na"
    try:
        affiliate_check = "["
        general_tds = html_info.find('table', {'summary': '他の施設との連携'}).find_all('td')
        for general_td in general_tds:
            if general_td.text.strip() == "実施":
                affiliate_check += (general_td.find_previous_sibling('th').text.strip() + ", ")
        affiliate_check += "]"
    except:
        affiliate_check = "na"

    try:
        general_th = html_info.find('table', {'summary': '医療機関の人員配置'}).find('th', string='歯科医師')
        total = general_th.find_next_sibling('td').text.strip()
        full = general_th.find_next_sibling('td').find_next_sibling('td').text.strip()
        part = general_th.find_next_sibling('td').find_next_sibling('td').find_next_sibling('td').text.strip()
        dentist = total + "|" + full + "|" + part
    except:
        dentist = "na"
    try:
        general_th = html_info.find('table', {'summary': '医療機関の人員配置'}).find('th', string='歯科衛生士')
        total = general_th.find_next_sibling('td').text.strip()
        full = general_th.find_next_sibling('td').find_next_sibling('td').text.strip()
        part = general_th.find_next_sibling('td').find_next_sibling('td').find_next_sibling('td').text.strip()
        dental_hygienist = total + "|" + full + "|" + part
    except:
        dental_hygienist = "na"
    try:
        average_people_count = html_info.find('table', {'summary': '患者数'}).find('th', string='前年度１日平均外来患者数').find_next_sibling('td').text.strip()
    except:
        average_people_count = "na"

    longitude = ''
    latitude = ''
    try:
        soup = BeautifulSoup(detailHtml, 'html.parser')
        script_tag_x = soup.find('script', string=lambda t: t and 'var lng' in t)
        script_tag_y = soup.find('script', string=lambda t: t and 'var lat' in t)

        longitude = script_tag_x.text.split('var lng')[1].split(';')[0].strip().strip('=').replace("'", "").replace('"', '').strip(' ')
        latitude = script_tag_y.text.split('var lat')[1].split(';')[0].strip().strip('=').replace("'", "").replace('"', '').strip(' ')
    except:
        longitude = "na"
        latitude = "na"

    
    try:
        medical_department = "[" + html_info.find('table', {'summary': '医療機関概要'}).find('th', string='診療科目').find_next_sibling('td').text.strip() + "]"
    except:
        medical_department = "na"


    baseData['timestamp'] = timeStamp
    baseData['storename'] = storename
    baseData['address_original'] = address_original
    baseData['address_normalize[0]'] = address_normalize_1
    baseData['address_normalize[1]'] = address_normalize_2
    baseData['updateDate'] = updateDate
    baseData['founder_type'] = founder_type
    baseData['founder_name'] = founder_name
    baseData['admin_name'] = admin_name
    baseData['general_dentistry'] = general_dentistry
    baseData['oral_surgery'] = oral_surgery
    baseData['pediatric_dentistry'] = pediatric_dentistry
    baseData['orthodontic_dentistry'] = orthodontic_dentistry
    baseData['has_structure'] = has_structure
    baseData['anesthesia_treatment'] = "na"
    baseData['home_care'] = home_care
    baseData['affiliate_check'] = affiliate_check
    baseData['dentist'] = dentist
    baseData['dental_technician'] = "-|-|-"
    baseData['dental_assistant'] = "-|-|-"
    baseData['dental_hygienist'] = dental_hygienist
    baseData['average_people_count'] = average_people_count
    baseData['latitude'] = latitude
    baseData['longitude'] = longitude
    baseData['medical_department'] = medical_department


    return baseData


def init():
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "mie" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)
    

    for line in f :
        page = line.split(',')[0]
        id = line.split(',')[1]

        page_url = base_url + id
        baseInfo = get_info_html(page_url)

        # detailhtml_file = open("detail.html", "ab")
        # detailhtml_file.write(baseInfo.content)
        # detailhtml_file.close()
        
        if baseInfo.status_code == 200:
            baseData = get_base_data(baseInfo.text)
        
        print(id)

        data=[
            baseData['timestamp'],
            baseData['storename'],
            baseData['address_original'],
            baseData['address_normalize[0]'],
            baseData['address_normalize[1]'],
            baseData['updateDate'],
            page_url,
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
            baseData['latitude'],
            baseData['longitude'],
            page,
            baseData['medical_department']
        ]

        writer.writerow(data)
        print(page_url)
        # print(data)

    csv_file.close()





    

init()
