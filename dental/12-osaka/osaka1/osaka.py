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
f = open("urls.txt", "r")

Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', 
      '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
      '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', 
      '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

base_url = 'https://www.mfis.pref.osaka.jp/ap/qq/dtl/pwdetaillt01_002.aspx?chosanendo=2022&chosano=1&kikancd='
base_url2 = 'https://www.mfis.pref.osaka.jp/ap/qq/dtl/pwdetaillt01_002.aspx?serviceid=pwdetaillt&chosanendo=2022&chosano=1&kikankbn=3&qrcodeflg=False&regist=1&category=2&kikancd='
base_url3 = 'https://www.mfis.pref.osaka.jp/ap/qq/dtl/pwdetaillt01_002.aspx?serviceid=pwdetaillt&chosanendo=2022&chosano=1&kikankbn=3&qrcodeflg=False&regist=1&category=3&kikancd='
base_url4 = 'https://www.mfis.pref.osaka.jp/ap/qq/dtl/pwdetaillt01_002.aspx?serviceid=pwdetaillt&chosanendo=2022&chosano=1&kikankbn=3&qrcodeflg=False&regist=1&category=4&kikancd='
main_url = 'https://www.mfis.pref.osaka.jp/ap/qq/dtl/pwdetaillt03_002.aspx?chosanendo=2022&chosano=1&kikancd='


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
def get_info_html(page_url, id):
    page = page_url + id
    response = requests.get(page, timeout = 10)
    if response.status_code == 200:
        return response
    else:
        get_info_html(page)

def get_detail_1(detailHtml):

    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')
    timeStamp = datetime.date.today()

    try:
        storename = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailKikanName4_lblKikanName'}).text.strip()
    except:
        storename = "na"
    try:
        address_original = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailKikanLocation4_lblLocationName'}).text.strip().replace("大阪府", "")
    except:
        address_original = "na"
    try:
        original = "大阪府" + address_original
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_1 = address_normalize_2 = "na"


    try:
        founder_text = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailKikanKaisetsu4_lblKaisetsuName'}).text.strip()
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
        admin_name = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailKikanKanri4_lblKanriName'}).text.strip()
    except:
        admin_name = "na"
    
    try:
        date_str = html_info.find('span', {'id': 'ctl00_cphdrBody_lblLastUpdate'}).text.strip()
        date_obj = parse(date_str)
        year_str = str(date_obj.year)
        month_str = str(date_obj.month)
        day_str = str(date_obj.day)
        updateDate = year_str + "年" + month_str + "月" + day_str + "日"
    except:
        updateDate = "na"


    baseData['timestamp'] = timeStamp
    baseData['storename'] = storename
    baseData['address_original'] = address_original
    baseData['address_normalize[0]'] = address_normalize_1
    baseData['address_normalize[1]'] = address_normalize_2
    baseData['updateDate'] = updateDate
    baseData['founder_type'] = founder_type
    baseData['founder_name'] = founder_name
    baseData['admin_name'] = admin_name

    return baseData

def get_detail_3(detailHtml):

    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')

    try:
        general_dentistry = "["
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailIryoKino4_tblIryoKino24'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            general_dentistry += (general_td.text.strip() + ", ")
        general_dentistry += "]"
    except:
        general_dentistry = "na"
    try:
        oral_surgery = "["
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailIryoKino4_tblIryoKino25'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            oral_surgery += (general_td.text.strip() + ", ")
        oral_surgery += "]"
    except:
        oral_surgery = "na"
    pediatric_dentistry = "na"
    orthodontic_dentistry = "na"

    baseData['general_dentistry'] = general_dentistry
    baseData['oral_surgery'] = oral_surgery
    baseData['pediatric_dentistry'] = pediatric_dentistry
    baseData['orthodontic_dentistry'] = orthodontic_dentistry

    return baseData

def get_detail_4(detailHtml):

    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')

    has_structure = "["
    try:
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailShohou4_tblShohou'}).find_all('td', {'class': 'Waku01Color'})
        for general_td in general_tds:
            has_structure += (general_td.text.strip() + ", ")
    except:
        flag = 0
        # print('not found prescription')
    try:
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailShogaisha4_tblShogaisha'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            has_structure += (general_td.text.strip() + ", ")
    except:
        flag = 0
        # print('not found disability')
    try:
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailWheel4_tblWheelHairyo'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            has_structure += (general_td.text.strip() + ", ")
    except:
        flag = 0
        # print('not found wheelchair')
    try:
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailJyudoKitsuen4_tblJyudoKitsuenJyoho'}).find_all('td', {'class': 'Waku01Color'})
        for general_td in general_tds:
            has_structure += (general_td.text.strip() + ", ")
    except:
        flag = 0
        # print('not found smoking')
    has_structure += "]"

    anesthesia_treatment = "na"
    
    try:
        home_care = "["
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailZaitakuIryo4_tblZaitakuiryo01'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            home_care += (general_td.text.strip() + ", ")
        home_care += "]"
    except:
        home_care = "na"
    try:
        affiliate_check = "["
        general_tds = html_info.find('table', {'id': 'ctl00_cphdrBody_uclDetailZaitakuIryo4_tblZaitakuiryo04'}).find_all('td', {'class': 'ArrangeLeft'})
        for general_td in general_tds:
            affiliate_check += (general_td.text.strip() + ", ")
        affiliate_check += "]"
    except:
        affiliate_check = "na"

    try:
        total = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblSoSouSu0'}).text.strip()
        full = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblJoSouSu0'}).text.strip()
        part = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblHjSouSu0'}).text.strip()
        dentist = total + "|" + full + "|" + part
    except:
        dentist = "na"
    try:
        total = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblSoSouSu1'}).text.strip()
        full = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblJoSouSu1'}).text.strip()
        part = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblHjSouSu1'}).text.strip()
        dental_hygienist = total + "|" + full + "|" + part
    except:
        dental_hygienist = "na"
    try:
        total = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblSoSouSu2'}).text.strip()
        full = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblJoSouSu2'}).text.strip()
        part = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblHjSouSu2'}).text.strip()
        dental_technician = total + "|" + full + "|" + part
    except:
        dental_technician = "na"
    try:
        total = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblSoSouSu3'}).text.strip()
        full = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblJoSouSu3'}).text.strip()
        part = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailJininHaichi4_lblHjSouSu3'}).text.strip()
        dental_assistant = total + "|" + full + "|" + part
    except:
        dental_assistant = "na"

    try:
        average_people_count = html_info.find('span', {'id': 'ctl00_cphdrBody_uclDetailNenkanKanjaSu4_tdDentalKanjaSu'}).text.strip().replace('人', '')
    except:
        average_people_count = "na"


    baseData['has_structure'] = has_structure
    baseData['anesthesia_treatment'] = anesthesia_treatment
    baseData['home_care'] = home_care
    baseData['affiliate_check'] = affiliate_check
    baseData['dentist'] = dentist
    baseData['dental_technician'] = dental_technician
    baseData['dental_assistant'] = dental_assistant
    baseData['dental_hygienist'] = dental_hygienist
    baseData['average_people_count'] = average_people_count

    return baseData

def get_detail_main(detailHtml):

    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')

    try:
        medical_department = "["
        general_lis = html_info.find('ul', {'id': 'ctl00_cphdrBody_ulKamokuList'}).find_all('li')
        for general_li in general_lis:
            medical_department += (general_li.text.strip() + ", ")
        medical_department += "]"
    except:
        medical_department = "na"

    latitude = "na"
    longitude = "na"


    baseData['medical_department'] = medical_department
    baseData['latitude'] = latitude
    baseData['longitude'] = longitude

    return baseData


def init():
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "osaka" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    # writer.writerow(Arg)
    
    # 4
    index = 0
    for line in f :
        index += 1

        page = line.split(',')[0]
        id = line.split(',')[1]
        page_url = base_url + id

        get_detailData_1 = get_info_html(base_url, id)
        if get_detailData_1.status_code == 200:
            detailInfo_1 = get_detail_1(get_detailData_1.text)


        get_detailData_3 = get_info_html(base_url3, id)
        if get_detailData_3.status_code == 200:
            detailInfo_3 = get_detail_3(get_detailData_3.text)

        get_detailData_4 = get_info_html(base_url4, id)
        if get_detailData_4.status_code == 200:
            detailInfo_4 = get_detail_4(get_detailData_4.text)

        get_detailData = get_info_html(main_url, id)
        if get_detailData.status_code == 200:
            detailInfo_main = get_detail_main(get_detailData.text)

        # detailhtml_file = open("detail_main.html", "ab")
        # detailhtml_file.write(get_detailData.text.encode('utf-8'))
        # detailhtml_file.close()
        
        
        data=[
            detailInfo_1['timestamp'],
            detailInfo_1['storename'],
            detailInfo_1['address_original'],
            detailInfo_1['address_normalize[0]'],
            detailInfo_1['address_normalize[1]'],
            detailInfo_1['updateDate'],
            page_url,
            detailInfo_1['founder_type'],
            detailInfo_1['founder_name'],
            detailInfo_1['admin_name'],
            detailInfo_3['general_dentistry'],
            detailInfo_3['oral_surgery'],
            detailInfo_3['pediatric_dentistry'],
            detailInfo_3['orthodontic_dentistry'],
            detailInfo_4['has_structure'],
            detailInfo_4['anesthesia_treatment'],
            detailInfo_4['home_care'],
            detailInfo_4['affiliate_check'],
            detailInfo_4['dentist'],
            detailInfo_4['dental_technician'],
            detailInfo_4['dental_assistant'],
            detailInfo_4['dental_hygienist'],
            detailInfo_4['average_people_count'],
            detailInfo_main['latitude'],
            detailInfo_main['longitude'],
            page,
            detailInfo_main['medical_department']
        ]

        writer.writerow(data)
        print(index)
        print(id, page_url)
        # print(data)

    csv_file.close()





    

init()
