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

Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', 
      '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
      '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', 
      '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

get_id_url = 'https://www.pref.yamagata.jp/medical-net/score/med/med_byou_sel.php'

detail_url_1 = 'https://www.pref.yamagata.jp/medical-net/score/med/med.php'
detail_url_2 = 'https://www.pref.yamagata.jp/medical-net/score/med/med_b.php'
detail_url_3 = 'https://www.pref.yamagata.jp/medical-net/score/med/med_c.php'



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
def get_id():
    clinicIds_file = open("ClinicIds.txt", "ab")
    params = {"BYOU_KIND": "3", "BYOU_KIND_NAME": "歯科診療所", "selectView": "1"}

    response = requests.post(get_id_url, data = params, timeout = 20)
    if response.status_code == 200:
        html_code = response.text
        clinic_ids = re.search(r"\$\(\'PARAM_VALUE\'\)\.value = \"(.*?)\"", html_code).group()
        print_ids = clinic_ids.split('"')[1]
        # print(print_ids)

        clinicIds_file.write(print_ids.encode('utf-8'))
        time.sleep(2)
    else:
        get_id()

def rerutn_clinic_ids():
    clinic_ids = []
    with open('ClinicIds.txt', 'r') as file:
        content = file.read()
    clinic_ids = content.split(",")
    return clinic_ids

def get_detail_html(url, cid):
    params = {"MED_ID": cid}

    response = requests.post(url, data = params, timeout = 20)
    if response.status_code == 200:
        return response
    else:
        get_detail_html(url, cid)


def get_detail_1(detailHtml):
    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')
    timeStamp = datetime.date.today()

    try:
        storename = html_info.find('div', {'class': 'RESULT_TITLE-KJ'}).text.strip()
    except:
        storename = "na"

    try:
        address_original = html_info.find('div', {'class': 'RESULT_ADD-KJ'}).text.split('　')[1].strip().replace("山形県","")
    except:
        address_original = "na"
    try:
        original = "山形県" + address_original
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_1 = address_normalize_2 = "na"

    try:
        updateDate = html_info.find('li', string='表示されている内容には一部変更が生じている場合もあります。医療機関を受診される場合は、電話等でご確認くださるようお願い致します。').find_previous_sibling('li').text.split('表示されている内容は')[1].split(' ')[0].strip()
    except:
        updateDate = "na"

    try:
        founder_text = html_info.find('div', {'class': 'RESULT_ESTBLISH-KJ'}).text
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
        admin_name = html_info.find('div', {'class': 'RESULT_ADMIN-KJ'}).text.strip()
    except:
        admin_name = "na"
        
    try:
        departments = html_info.find('div', {'id': 'RESULT-BOX-SUBJECT'}).find('table').find('td').text.strip().replace('\n', '').replace('\xa0', '').split('●')[1:]
        medical_department = "["
        for department in departments:
            medical_department += (department + ", ")
        medical_department += "]"
    except:
        medical_department = "na"

    try:
        src = html_info.find('div', {'class': 'RESULT_ADD-MAP'}).find('iframe').get('src')
        url_params = src.split('?')[1]
        params = url_params.split('X=')[1].split('&Y=')

        latitude = params[0]
        longitude = params[1]
    except:
        latitude = "na"
        longitude = "na"


    baseData['timestamp'] = timeStamp
    baseData['storename'] = storename
    baseData['address_original'] = address_original
    baseData['address_normalize[0]'] = address_normalize_1
    baseData['address_normalize[1]'] = address_normalize_2
    baseData['updateDate'] = updateDate
    baseData['founder_type'] = founder_type
    baseData['founder_name'] = founder_name
    baseData['admin_name'] = admin_name
    baseData['medical_department'] = medical_department
    baseData['latitude'] = latitude
    baseData['longitude'] = longitude

    return baseData


def get_detail_2(detailHtml):
    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')

    try:
        has_structure = "["

        try:
            structure_1_tds = html_info.find('div', {'id': 'RESULT-BOX-HANDY'}).find_all('td', {'class': 'BRR_NONE'})
            for structure_1_td in structure_1_tds:
                has_structure += (structure_1_td.text.strip().replace('●', '').replace('\xa0', '') + ", ")
        except:
            print('not HANDY')
        try:
            structure_2_tds = html_info.find('div', {'id': 'RESULT-BOX-WHEEL'}).find_all('td', {'class': 'BRR_NONE'})
            for structure_2_td in structure_2_tds:
                has_structure += (structure_2_td.text.strip().replace('●', '').replace('\xa0', '') + ", ")
        except:
            print('not WHEEL')
        try:
            structure_3_tds = html_info.find('div', {'id': 'RESULT-BOX-SMOKE'}).find_all('td', {'class': 'BRr'})
            for structure_3_td in structure_3_tds:
                has_structure += (structure_3_td.text.strip().replace('●', '').replace('\xa0', '') + ", ")
        except:
            print('not SMOKE')

        has_structure += "]"
    except:
        has_structure = "na"

    anesthesia_treatment = "na"

    try:
        home_care = "["
        affiliate_check = "["

        general_trs = html_info.find('div', {'id': 'RESULT-BOX-HMCS'}).find('table').find_all('tr')
        flag = 0
        for general_tr in general_trs:
            first_td = general_tr.find_all('td')[0]

            if '在宅医療' in first_td.text:
                flag = 1
                home_care += (general_tr.find_all('td')[-1].text.replace('\xa0', '') + ', ')
            elif '連携の有無' in first_td.text:
                flag = 2
                affiliate_check += (general_tr.find_all('td')[-1].text.replace('\xa0', '') + ', ')

            elif first_td.text == '\xa0' and flag == 1:
                home_care += (general_tr.find_all('td')[-1].text.replace('\xa0', '') + ', ')
            elif first_td.text == '\xa0' and flag == 2:
                affiliate_check += (general_tr.find_all('td')[-1].text.replace('\xa0', '') + ', ')

        home_care += "]"
        affiliate_check += "]"
    except:
        home_care = "na"
        affiliate_check = "na"


    baseData['has_structure'] = has_structure
    baseData['anesthesia_treatment'] = anesthesia_treatment
    baseData['home_care'] = home_care
    baseData['affiliate_check'] = affiliate_check

    return baseData


def get_detail_3(detailHtml):
    baseData = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')

    try:
        general_dentistry = "["
        oral_surgery = "["

        general_trs = html_info.find('div', {'id': 'RESULT-BOX-DCS'}).find('table').find_all('tr')[1:]
        flag = 0
        for general_tr in general_trs:
            first_td = general_tr.find_all('td')[0]

            if '歯科領域' in first_td.text:
                flag = 1
                general_dentistry += (general_tr.find_all('td')[1].text.replace('\xa0', '') + ', ')
            elif '歯科口腔外科領域' in first_td.text:
                flag = 2
                oral_surgery += (general_tr.find_all('td')[1].text.replace('\xa0', '') + ', ')

            elif first_td.text == '\xa0' and flag == 1:
                general_dentistry += (general_tr.find_all('td')[1].text.replace('\xa0', '') + ', ')
            elif first_td.text == '\xa0' and flag == 2:
                oral_surgery += (general_tr.find_all('td')[1].text.replace('\xa0', '') + ', ')

        general_dentistry += "]"
        oral_surgery += "]"
    except:
        general_dentistry = "na"
        oral_surgery = "na"

    pediatric_dentistry = "na"
    orthodontic_dentistry = "na"

    try:
        general_trs = html_info.find('div', {'id': 'RESULT-BOX-MWC'}).find('table').find_all('tr')[1:]
        for general_tr in general_trs:
            td_1 = general_tr.find_all('td')[0]
            td_2 = general_tr.find_all('td')[1]
            td_3 = general_tr.find_all('td')[2]

            a = td_2.text.strip().replace('人', '').replace('\xa0', '')
            b = td_3.text.strip().replace('人', '').replace('\xa0', '')
            if a == '-':
                a = 0
            if b == '-':
                b = 0
            total = float(a) + float(b)

            if td_1.text.strip() == '歯科医師':
                dentist = str(total) + "|-|-"
            if td_1.text.strip() == '歯科衛生士':
                dental_hygienist = str(total) + "|-|-"
            if td_1.text.strip() == '歯科技工士':
                dental_technician = str(total) + "|-|-"
            if td_1.text.strip() == 'その他':
                dental_assistant = str(total) + "|-|-"

        try: dentist
        except NameError: dentist = "na"
        try: dental_hygienist
        except NameError: dental_hygienist = "na"
        try: dental_technician
        except NameError: dental_technician = "na"
        try: dental_assistant
        except NameError: dental_assistant = "na"

    except:
        dentist = "na"
        dental_hygienist = "na"
        dental_technician = "na"
        dental_assistant = "na"

    try:
        average_people_count = html_info.find('div', {'id': 'RESULT-BOX-RESULT'}).find('td', string='外来患者数（１日平均外来患者数）').find_next_sibling('td').text.strip().replace('人', '').replace('\xa0', '')
    except:
        average_people_count = "na"


    baseData['general_dentistry'] = general_dentistry
    baseData['oral_surgery'] = oral_surgery
    baseData['pediatric_dentistry'] = pediatric_dentistry
    baseData['orthodontic_dentistry'] = orthodontic_dentistry
    baseData['dentist'] = dentist
    baseData['dental_technician'] = dental_technician
    baseData['dental_assistant'] = dental_assistant
    baseData['dental_hygienist'] = dental_hygienist
    baseData['average_people_count'] = average_people_count

    return baseData


def init():
    print('Start!')
    get_id()
    time.sleep(3)
    
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "yamagata" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)

    clinic_ids = rerutn_clinic_ids()
    # clinic_ids = [306310027, 306310030, 306310043]
    # clinic_ids = [306310027]  [546:] + clinic_ids[:546]

    index = 0
    for cid in clinic_ids:
        print(index + 1, clinic_ids[index])
        index += 1
        page = 1
        page_url = detail_url_1

        get_detailData_1 = get_detail_html(detail_url_1, cid)
        if get_detailData_1.status_code == 200:
            detailInfo_1 = get_detail_1(get_detailData_1.text)

        get_detailData_2 = get_detail_html(detail_url_2, cid)
        if get_detailData_2.status_code == 200:
            detailInfo_2 = get_detail_2(get_detailData_2.text)

        get_detailData_3 = get_detail_html(detail_url_3, cid)
        if get_detailData_3.status_code == 200:
            detailInfo_3 = get_detail_3(get_detailData_3.text)


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
            detailInfo_2['has_structure'],
            detailInfo_2['anesthesia_treatment'],
            detailInfo_2['home_care'],
            detailInfo_2['affiliate_check'],
            detailInfo_3['dentist'],
            detailInfo_3['dental_technician'],
            detailInfo_3['dental_assistant'],
            detailInfo_3['dental_hygienist'],
            detailInfo_3['average_people_count'],
            detailInfo_1['latitude'],
            detailInfo_1['longitude'],
            page,
            detailInfo_1['medical_department']
        ]

        writer.writerow(data)
        print(page, page_url)
        # print(data)

    csv_file.close()



    # detail_file = open("detail3.html", "ab")
    # detail_file.write(get_detailData_3.content)
    # detail_file.close()

init()
