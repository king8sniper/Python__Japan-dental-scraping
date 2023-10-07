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
Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧','施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

Get_ClinicId_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/?dayofweek=&departmentcategoryid=10&languagelevel=%E2%97%8E&kenshin_keyword=&searchtype=function&gairai_keyword=&objecttype=1%2C2%2C4&requestpage="

GetInfo_Detail_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/detail.cfm?objectid="
GetInfo_Access_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/access.cfm?objectid="
GetInfo_Service_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/service.cfm?objectid="
GetInfo_Cost_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/cost.cfm?objectid="
GetInfo_Consult_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/consult.cfm?objectid="
GetInfo_Showcase_BaseUrl = "https://iryojoho.pref.aichi.jp/medical/showcase.cfm?objectid="





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


## Functions  get Dental Clinic Ids

# -------------------------------------------------------------------------------------
def get_ids_html(page):
    response = requests.get(page, timeout = 5)
    if response.status_code == 200:
        return response
    else:
        get_ids_html(page)

# -------------------------------------------------------------------------------------
def save_clinic_ids(clinic_ids_html):
    html_info = BeautifulSoup(clinic_ids_html, 'lxml')
    id_list_html = html_info.find_all('li', {'class': 'detail-name'})
    clinicid_file = open("Clinicids.txt", "ab")

    for id_html in id_list_html:
        match = re.search(r'objectid=(\d+)', str(id_html))
        if match:
            ClinicIds = match.group(1)
            cid_str = (str(ClinicIds) + ", ").encode("utf-8")
            clinicid_file.write(cid_str)
        else:
            print('No match found')
    clinicid_file.close()

# -------------------------------------------------------------------------------------
def get_clinic_ids():

    for page in range(1, 184):
        ClinicId_pageUrl = Get_ClinicId_BaseUrl + str(page)
        clinic_ids_html = get_ids_html(ClinicId_pageUrl)
        if clinic_ids_html.status_code == 200:
            print(page)
            get_ids = save_clinic_ids(clinic_ids_html.text)
# get_clinic_ids()


def rerutn_clinic_ids():
    clinic_ids = []
    with open('Clinicids.txt', 'r') as file:
        content = file.read()
    clinic_ids = content.split(", ")
    # print(clinic_ids)
    return clinic_ids


## Functions  get Dental Clinic Info

# -------------------------------------------------------------------------------------
def get_info_html(page):
    response = requests.get(page, timeout = 20)
    if response.status_code == 200:
        return response
    else:
        get_info_html(page)

def get_detail_info(detailHtml):

    detail_data = {}
    html_info = BeautifulSoup(detailHtml, 'lxml')
    timeStamp = datetime.date.today()

    try:
        storename = html_info.find('table', {'aria-label': '医療機関の名称'}).find("th", string="機関名称").find_next_sibling('td').text.strip().replace('\u3000', ' ')
    except:
        storename = "na"
    try:
        address_original = html_info.find('table', {'aria-label': '医療機関の所在地'}).find("th", string="所在地").find_next_sibling('td').text.strip().replace('\u3000', ' ').replace("愛知県","")
    except:
        address_original = "na"
    try:
        original = "愛知県" + address_original
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_1 = address_normalize_2 = "na"


    try:
        founder_text = html_info.find('table', {'aria-label': '医療機関の開設者'}).find("th", string="開設者名称").find_next_sibling('td').text
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
        admin_name = html_info.find('table', {'aria-label': '医療機関の管理者'}).find("th", string="管理者名称").find_next_sibling('td').text.strip().replace('\u3000', ' ')
    except:
        admin_name = "na"
    try:
        date_str = html_info.find('div', {'id': 'contents'}).find("p", {'class': 'text-right'}).text.replace("最終更新日：","")
        date_obj = parse(date_str)
        year_str = str(date_obj.year)
        month_str = str(date_obj.month)
        day_str = str(date_obj.day)
        updateDate = year_str + "年" + month_str + "月" + day_str + "日"
    except:
        updateDate = "na"


    longitude = "na"
    latitude = "na"

    detail_data['timestamp'] = timeStamp
    detail_data['storename'] = storename
    detail_data['address_original'] = address_original
    detail_data['address_normalize[0]'] = address_normalize_1
    detail_data['address_normalize[1]'] = address_normalize_2
    detail_data['updateDate'] = updateDate
    detail_data['founder_type'] = founder_type
    detail_data['founder_name'] = founder_name
    detail_data['admin_name'] = admin_name
    detail_data['longitude'] = longitude
    detail_data['latitude'] = latitude

    return detail_data

def get_consult_info(consultHtml):
    consult_data = {}
    html_info = BeautifulSoup(consultHtml, 'lxml')

    try:
        general_dentistry = "["

        try:
            html_info.find("h3", string="歯科領域").find_next_sibling('table').find('th')

            general_ths = html_info.find("h3", string="歯科領域").find_next_sibling('table').find_all('th')
            for general_th in general_ths:
                if general_th.find_next_sibling('td').text.strip().strip(' ').replace("　", "").replace("\n", "") == "○":
                    general_dentistry += (general_th.text.strip().replace("　", "").replace("\n", "") + ", ")
        except:
            general_tds = html_info.find("h3", string="歯科領域").find_next_sibling('table').find_all('td')
            for general_td in general_tds:
                if general_td.text.strip() != "":
                    general_dentistry += (general_td.text.strip().replace("　", "").replace("\n", "") + ", ")

        general_dentistry += "]"
    except:
        general_dentistry = "na"


    try:
        oral_surgery = "["

        try:
            html_info.find("h3", string="歯科口腔(くう)外科領域").find_next_sibling('table').find('th')

            general_ths = html_info.find("h3", string="歯科口腔(くう)外科領域").find_next_sibling('table').find_all('th')
            for general_th in general_ths:
                if general_th.find_next_sibling('td').text.strip().strip(' ').replace("　", "").replace("\n", "") == "○":
                    oral_surgery += (general_th.text.strip().replace("　", "").replace("\n", "") + ", ")
        except:
            general_tds = html_info.find("h3", string="歯科領域").find_next_sibling('table').find_all('td')
            for general_td in general_tds:
                if general_td.text.strip() != "":
                    oral_surgery += (general_td.text.strip().replace("　", "").replace("\n", "") + ", ")

        oral_surgery += "]"
    except:
        oral_surgery = "na"


    pediatric_dentistry = "na"
    orthodontic_dentistry = "na"

    try:
        avariable_treatment = "["
        general_tds = html_info.find("h3", string="麻酔領域").find_next_sibling('table').find_all('td')
        for general_td in general_tds:
            if general_td.text.strip() != "":
                text_without_numbers = re.sub(r'\d+', '', general_td.text.strip())
                cleaned_text = text_without_numbers.replace("　", "").replace("\n", "")
                avariable_treatment += (cleaned_text + ", ")
        avariable_treatment += "]"
    except:
        avariable_treatment = "na"

    try:
        home_care = "["
        general_tds = html_info.find("h3", string="在宅療養指導").find_next_sibling('table').find_all('td')
        for general_td in general_tds:
            home_care += (general_td.text.strip().replace("　", "").replace("\n", "") + ", ")
        home_care += "]"
    except:
        home_care = "na"

    affiliate_check = "na"


    try:
        medical_department_list = "["

        try:
            html_info.find("h2", string="対応することができる疾患又は治療の内容").find_parent('section', {'class': 'around'})
            
            general_secs = html_info.find("h2", string="対応することができる疾患又は治療の内容").find_parent('section').find_parent('div', {'id': 'details'}).find_all('section', {'class': 'around'})
            for general_sec in general_secs:
                medical_department_list += (general_sec.find('h3', {'class': 'quinary-title'}).text.strip().replace("　", "").replace("\n", "") + ", ")
        except:
            general_h3s = html_info.find("h2", string="対応することができる疾患又は治療の内容").find_parent('section').find_parent('div', {'id': 'details'}).find_all('h3')
            for general_h3 in general_h3s:
                medical_department_list += (general_h3.text.strip().replace("　", "").replace("\n", "") + ", ")

        medical_department_list += "]"
    except:
        medical_department_list = "na"


    consult_data['general_dentistry'] = general_dentistry
    consult_data['oral_surgery'] = oral_surgery
    consult_data['pediatric_dentistry'] = pediatric_dentistry
    consult_data['orthodontic_dentistry'] = orthodontic_dentistry
    consult_data['avariable_treatment'] = avariable_treatment
    consult_data['home_care'] = home_care
    consult_data['affiliate_check'] = affiliate_check
    consult_data['medical_department'] = medical_department_list

    return consult_data

def get_access_info(accessHtml):
    access_data = {}
    html_info = BeautifulSoup(accessHtml, 'lxml')

    has_structure = ' '
    try:
        general_td = html_info.find('table', {'aria-label': '医療機関の駐車場'}).find("th", string="駐車場の有無（契約駐車場も含む）").find_next_sibling('td')
        if general_td.text.strip() == "有り":
            has_structure = "駐車場の有無（契約駐車場も含む）"
    except:
        has_structure = " "

    access_data['has_structure'] = has_structure

    return access_data

def get_service_info(serviceHtml):
    service_data = {}
    html_info = BeautifulSoup(serviceHtml, 'lxml')
    has_structure = []
    table_labels = ['入院食の提供方法', '障害者に対するサービス内容', '車椅子等利用者に対するサービス内容', '病院内の売店又は食堂の有無', '受動喫煙を防止するための措置']

    for table_label in table_labels:
        try:
            general_trs = html_info.find('table', {'aria-label': table_label}).find_all("tr")
            for general_tr in general_trs:
                if general_tr.find('td').text.strip().replace("　", "").replace("\n", "") == "有り":
                    has_structure.append(general_tr.find('th').text.strip().replace("　", "").replace("\n", ""))
        except:
            a = 5

    service_data['has_structure'] = has_structure

    return service_data

def get_showcase_info(showcaseHtml):
    showcase_data = {}
    html_info = BeautifulSoup(showcaseHtml, 'lxml')

    dentist = "na"
    dental_hygienist = "na"
    try:
        general_trs = html_info.find('table', {'aria-label': '医療機関の人員配置'}).find('tbody').find_all("tr")
        for general_tr in general_trs:
            if general_tr.find('th').text.strip().replace("　", "").replace("\n", "") == "歯科医師":
                dentist_all = general_tr.find_all('td')[0].text.strip().replace("　", "").replace("\n", "")
                dentist_in = general_tr.find_all('td')[1].text.strip().replace("　", "").replace("\n", "")
                dentist_out = general_tr.find_all('td')[2].text.strip().replace("　", "").replace("\n", "")
                dentist = dentist_all + '|' + dentist_in + '|' + dentist_out
    except:
        dentist = "na"

    try:
        general_trs = html_info.find('table', {'aria-label': '医療機関の人員配置'}).find('tbody').find_all("tr")
        for general_tr in general_trs:
            if general_tr.find('th').text.strip().replace("　", "").replace("\n", "") == "歯科衛生士":
                hygienist_all = general_tr.find_all('td')[0].text.strip().replace("　", "").replace("\n", "")
                hygienist_in = general_tr.find_all('td')[1].text.strip().replace("　", "").replace("\n", "")
                hygienist_out = general_tr.find_all('td')[2].text.strip().replace("　", "").replace("\n", "")
                dental_hygienist = hygienist_all + '|' + hygienist_in + '|' + hygienist_out
    except:
        dental_hygienist = "na"

    dental_technician = "na"
    dental_assistant = "na"

    try:
        average_people_count = html_info.find('table', {'aria-label': '患者数及び平均在院日数'}).find("th", string="前年度１日平均患者数").find_next_sibling('td').text.strip().replace("　", "").replace("\n", "")
    except:
        average_people_count = ""

    showcase_data['dentist'] = dentist
    showcase_data['dental_technician'] = dental_technician
    showcase_data['dental_assistant'] = dental_assistant
    showcase_data['dental_hygienist'] = dental_hygienist
    showcase_data['average_people_count'] = average_people_count

    return showcase_data


def init():
    get_clinic_ids()
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "aichi" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)

    clinic_ids = rerutn_clinic_ids()
    # clinic_ids = [51865, 51860]
    # clinic_ids = [51860]  [546:] + clinic_ids[:546]
    print(len(clinic_ids))

    index = 0
    for cid in clinic_ids:
        detailPage_url = GetInfo_Detail_BaseUrl + str(cid)
        consultPage_url = GetInfo_Consult_BaseUrl + str(cid)
        accessPage_url = GetInfo_Access_BaseUrl + str(cid)
        servicePage_url = GetInfo_Service_BaseUrl + str(cid)
        showcasePage_url = GetInfo_Showcase_BaseUrl + str(cid)
        # detailPage_url = GetInfo_Cost_BaseUrl + str(cid)


        get_detailData = get_info_html(detailPage_url)
        if get_detailData.status_code == 200:
            detailInfo = get_detail_info(get_detailData.text)
        
        get_consultData = get_info_html(consultPage_url)
        if get_consultData.status_code == 200:
            consultInfo = get_consult_info(get_consultData.text)

        get_accessData = get_info_html(accessPage_url)
        if get_accessData.status_code == 200:
            accessInfo = get_access_info(get_accessData.text)

        get_serviceData = get_info_html(servicePage_url)
        if get_serviceData.status_code == 200:
            serviceInfo = get_service_info(get_serviceData.text)

        get_showcaseData = get_info_html(showcasePage_url)
        if get_showcaseData.status_code == 200:
            showcaseInfo = get_showcase_info(get_showcaseData.text)

        has_structure = "["
        for li in serviceInfo['has_structure']:
            has_structure += (li + ", ")
        has_structure += (", " + accessInfo['has_structure'] + "]")
        index += 1
        page = (int(index / 20) + 1)

        data=[
            detailInfo['timestamp'],
            detailInfo['storename'],
            detailInfo['address_original'],
            detailInfo['address_normalize[0]'],
            detailInfo['address_normalize[1]'],
            detailInfo['updateDate'],
            detailPage_url,
            detailInfo['founder_type'],
            detailInfo['founder_name'],
            detailInfo['admin_name'],
            consultInfo['general_dentistry'],
            consultInfo['oral_surgery'],
            consultInfo['pediatric_dentistry'],
            consultInfo['orthodontic_dentistry'],
            has_structure,
            consultInfo['avariable_treatment'],
            consultInfo['home_care'],
            consultInfo['affiliate_check'],
            showcaseInfo['dentist'],
            showcaseInfo['dental_technician'],
            showcaseInfo['dental_assistant'],
            showcaseInfo['dental_hygienist'],
            showcaseInfo['average_people_count'],
            detailInfo['longitude'],
            detailInfo['latitude'],
            page,
            consultInfo['medical_department']
        ]

        writer.writerow(data)
        print(index, cid)
        print(detailPage_url)

    csv_file.close()





    # detail_file = open("showcase.html", "ab")
    # detail_file.write(get_showcaseData.content)
    # detail_file.close()

init()
