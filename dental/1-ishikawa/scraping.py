###  Import Modules

from bs4 import BeautifulSoup
import requests
import jaconv
import re
import json
import csv
import time
import datetime
from normalize_japanese_addresses import normalize
import numpy as np
import builtins


###  Global Variables

WAIT_SEC = 15
GetIds_Post_Url = "http://i-search.pref.ishikawa.jp/ajax/tableMake.php"
GetDetailInfo_Base_Url = "http://i-search.pref.ishikawa.jp/detail.php?rd_no="
Arg = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧','施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']




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


## Functions  before receiving detail info
# -------------------------------------------------------------------------------------
def make_csv_file():
    Today = datetime.today().strftime('%Y-%m-%d')
    csv_file_name = "ishikawa" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)

# -------------------------------------------------------------------------------------
def get_clinic_ids():
    simple_file = open("simple.txt", "ab")

    for x in range(1, 50):
        page_num = x
        body = {"sr_mode": "13", "sr_opt_outmode": "1", "sr_area_base": "0", "vl_page": page_num}
        response = requests.post(GetIds_Post_Url, data = body, timeout = 20).content
        simple_file.write(response)
        time.sleep(5)
    simple_file.close()
    time.sleep(5)

    clinic_ids = []
    pattern = re.compile(r'no:([^,]+)')
    with open('simple.txt', encoding='utf-8') as f:
        text_str = f.read()

    for id in re.finditer(pattern, text_str):
        no = int((id.group(1)).strip("'"))
        clinic_ids.append(no)

    return clinic_ids

# -------------------------------------------------------------------------------------
def get_detailHtml(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 GTB7.1 (.NET CLR 3.5.30729)", "Referer": "http://example.com"}
    try:
        response = requests.get(url,headers=headers, timeout = 5)
        return response.text
    except requests.exceptions.ConnectTimeout:
        time.sleep(5 + np.random.rand()*5)
        response = requests.get(url,headers=headers, timeout = 5)
        return response.text


## Functions  after receiving detail info
# -------------------------------------------------------------------------------------
def get_base_data(Detail_Info):
    baseData = {}
    html_info1 = BeautifulSoup(Detail_Info, 'lxml')
    html_info = str(BeautifulSoup(Detail_Info, 'lxml'))

    timeStamp = datetime.date.today()
    try:
        storename = html_info1.find('div', {'id': 'basicname'}).find('h2', {'class': 'r21'}).text.replace('\u3000', ' ')
    except:
        storename = "na"
    try:
        address_original = html_info1.find('div', {'class': 'detail001'}).find("th", string="所在地").find_next_sibling('td').text.strip().replace('\u3000', ' ').replace("石川県","")
        # address_original = address_original.replace("石川県","")
    except:
        address_original = "na"
    try:
        original = "石川県" + address_original
        storeAddressNormalize = "".join(list(normalize(address_original).values())[0:4])
        address_normalize_1 = _split_buildingName(storeAddressNormalize)[0]
        address_normalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        address_normalize_1 = address_normalize_2 = "na"
    updateDate = "na"


    tr_tags = html_info1.find('div', {'class': 'detail001'}).find_all('tr')
    try:
        founder_text = tr_tags[2].find("td").text.strip()
        check_type = "医療法人" in founder_text
        if check_type:
            founder_type = "医療法人"
            founder_name = founder_text.replace("医療法人社団","").replace('\u3000', ' ')
        else :
            founder_type = "個人"
            founder_name = founder_text.replace('\u3000', ' ')
    except:
        founder_type = "na"
        founder_name = "na"

    try:
        admin_text = tr_tags[3].find("th").text.strip()
        if admin_text == "法人代表者" :
            admin_name = tr_tags[4].find("td").text.strip().replace('\u3000', ' ')
        else :
            admin_name = tr_tags[3].find("td").text.strip().replace('\u3000', ' ')
    except:
        admin_name = "na"

    longitude = ''
    latitude = ''

    try:
        soup = BeautifulSoup(Detail_Info, 'html.parser')
        script_tag_x = soup.find('script', string=lambda t: t and 'var x' in t)
        script_tag_y = soup.find('script', string=lambda t: t and 'var y' in t)

        longitude = script_tag_x.text.split('var x')[1].split(';')[0].strip().strip('=').strip("'").strip('"')
        latitude = script_tag_y.text.split('var y')[1].split(';')[0].strip().strip('=').strip("'").strip('"')
    except:
        longitude = "na"
        latitude = "na"


    baseData['timestamp'] = timeStamp
    baseData['storename'] = storename
    baseData['address_original'] = address_original
    baseData['address_normalize[0]'] = address_normalize_1
    baseData['address_normalize[1]'] = address_normalize_2
    baseData['updateDate'] = updateDate
    baseData['founder_type'] = founder_type
    baseData['founder_name'] = founder_name
    baseData['admin_name'] = admin_name
    baseData['longitude'] = longitude
    baseData['latitude'] = latitude

    return baseData

# -------------------------------------------------------------------------------------
def get_clinic_data(Detail_Info):
    clinicData = {}
    html_info = BeautifulSoup(Detail_Info, 'lxml')

    try:
        general_td = html_info.find("td", string="歯科")
        general_dentistry = general_td.find_next_sibling('td').text.strip().replace("　", "").replace("\n", "")
    except:
        general_dentistry = "na"
    try:
        general_td = html_info.find("h3", string="対応することができる疾患・治療内容").find_parent('div')
        li_tags = general_td.find_next_sibling('div', {'class': 'detail034'}).find("th", string="歯科領域").find_next_sibling('td').find_all('li')
        general_dentistry_list = "["
        for li_tag in li_tags:
            general_dentistry_list += (li_tag.text.strip().replace("　", "").replace("\n", "") + ", ")
        general_dentistry_list += (general_dentistry + "]")
    except:
        general_dentistry_list = general_dentistry

    try:
        general_td = html_info.find("td", string="歯科口腔外科")
        oral_surgery = general_td.find_next_sibling('td').text.strip().replace("　", "").replace("\n", "")
    except:
        oral_surgery = "na"
    try:
        general_td = html_info.find("h3", string="対応することができる疾患・治療内容").find_parent('div')
        li_tags = general_td.find_next_sibling('div', {'class': 'detail034'}).find("th", string="口腔外科領域").find_next_sibling('td').find_all('li')
        oral_surgery_list = "["
        for li_tag in li_tags:
            oral_surgery_list += (li_tag.text.strip().replace("　", "").replace("\n", "") + ", ")
        oral_surgery_list += (oral_surgery + "]")
    except:
        oral_surgery_list = oral_surgery

    try:
        general_td = html_info.find("td", string="小児歯科")
        pediatric_dentistry = general_td.find_next_sibling('td').text.strip().replace("　", "").replace("\n", "")
        if pediatric_dentistry == "無":
            pediatric_dentistry = "na"
    except:
        pediatric_dentistry = "na"

    try:
        general_td = html_info.find("td", string="矯正歯科")
        orthodontic_dentistry = general_td.find_next_sibling('td').text.strip().replace("　", "").replace("\n", "")
        if orthodontic_dentistry == "無":
            orthodontic_dentistry = "na"
    except:
        orthodontic_dentistry = "na"

    try:
        general_td = html_info.find("th", string="有している構造")
        structure_list = general_td.find_next_sibling('td').find_all("li")
        has_structure = "["
        for s_list in structure_list:
            has_structure += (s_list.text.strip().replace("　", "").replace("\n", "") + ", ")
        has_structure += "]"
    except:
        has_structure = "na"

    try:
        general_td = html_info.find("h3", string="対応することができる疾患・治療内容").find_parent('div')
        li_tags = general_td.find_next_sibling('div', {'class': 'detail034'}).find("th", string="麻酔領域").find_next_sibling('td').find_all('li')
        avariable_treatment = "["
        for li_tag in li_tags:
            avariable_treatment += (li_tag.text.strip().replace("　", "").replace("\n", "") + ", ")
        avariable_treatment += "]"
    except:
        avariable_treatment = "na"

    try:
        general_td = html_info.find("th", string="在宅医療")
        home_care_list = general_td.find_next_sibling('td').find_all("li")
        home_care = "["
        for s_list in home_care_list:
            home_care += (s_list.text.strip().replace("　", "").replace("\n", "") + ", ")
        home_care += "]"
    except:
        home_care = "na"

    try:
        general_td = html_info.find("th", string="連携の有無")
        affiliate_check_list = general_td.find_next_sibling('td').find_all("li")
        affiliate_check = "["
        for s_list in affiliate_check_list:
            affiliate_check += (s_list.text.strip().replace("　", "").replace("\n", "") + ", ")
        affiliate_check += "]"
    except:
        affiliate_check = "na"

    try:
        general_div = html_info.find("h3", string="診療科目").find_parent('div')
        td_tags = general_div.find_next_sibling('div', {'class': 'detail006'}).find_all('td', {'class': 'detail006bg'})
        medical_department_list = "["
        for td_tag in td_tags:
            medical_department_list += (td_tag.text.strip().replace("　", "").replace("\n", "") + ", ")
        medical_department_list += "]"
    except:
        medical_department_list = "na"



    clinicData['general_dentistry'] = general_dentistry_list
    clinicData['oral_surgery'] = oral_surgery_list
    clinicData['pediatric_dentistry'] = pediatric_dentistry
    clinicData['orthodontic_dentistry'] = orthodontic_dentistry
    clinicData['has_structure'] = has_structure
    clinicData['avariable_treatment'] = avariable_treatment
    clinicData['home_care'] = home_care
    clinicData['affiliate_check'] = affiliate_check
    clinicData['medical_department'] = medical_department_list

    return clinicData

# -------------------------------------------------------------------------------------
def get_person_data(Detail_Info):
    personData = {}
    html_info = BeautifulSoup(Detail_Info, 'lxml')

    try:
        dentist_div = html_info.find("td", string="歯科医師数")
        dentist_element = dentist_div.find_next_sibling('td').text.strip().replace('人', '')
    except:
        dentist_element = "na"

    try:
        technician_div = html_info.find("td", string="歯科技工士数")
        dental_technician = technician_div.find_next_sibling('td').text.strip().replace('人', '')
    except:
        dental_technician = "na"

    try:
        assistant_div = html_info.find("td", string="歯科助手数")
        dental_assistant = assistant_div.find_next_sibling('td').text.strip().replace('人', '')
    except:
        dental_assistant = "na"

    try:
        hygienist_div = html_info.find("td", string="歯科衛生士数")
        dental_hygienist_element = hygienist_div.find_next_sibling('td').text.strip().replace('人', '')
    except:
        dental_hygienist_element = "na"

    try:
        people_count_div = html_info.find("td", string="外来患者数")
        average_people_count = people_count_div.find_next_sibling('td').text.strip().replace('人', '')
    except:
        average_people_count = "na"


    personData['dentist'] = dentist_element + '|-|-'
    personData['dental_technician'] = dental_technician + '|-|-'
    personData['dental_assistant'] = dental_assistant + '|-|-'
    personData['dental_hygienist'] = dental_hygienist_element + '|-|-'
    personData['average_people_count'] = average_people_count

    return personData


## Init Function
# -------------------------------------------------------------------------------------
def init():
    datetime_module = builtins.__import__('datetime')
    Today = datetime_module.date.today()

    csv_file_name = "ishikawa" + str(Today) + ".csv"
    csv_file = open(csv_file_name, 'a', newline="", encoding="utf-8", errors="replace")
    writer = csv.writer(csv_file)
    writer.writerow(Arg)
    clinic_ids = get_clinic_ids()
    print(len(clinic_ids)) #[139:] + clinic_ids[:139]

    index = 0
    for clinic_id in clinic_ids:
        detail_url = GetDetailInfo_Base_Url + str(clinic_id)
        print(detail_url)

        Detail_Info = get_detailHtml(detail_url)
        baseData = get_base_data(Detail_Info)
        baseData['url'] = detail_url
        clinicData = get_clinic_data(Detail_Info)
        personData = get_person_data(Detail_Info)
        index += 1
        page = (int(index/10)+1)

        data=[
            baseData['timestamp'],
            baseData['storename'],
            baseData['address_original'],
            baseData['address_normalize[0]'],
            baseData['address_normalize[1]'],
            baseData['updateDate'],
            baseData['url'],
            baseData['founder_type'],
            baseData['founder_name'],
            baseData['admin_name'],
            clinicData['general_dentistry'],
            clinicData['oral_surgery'],
            clinicData['pediatric_dentistry'],
            clinicData['orthodontic_dentistry'],
            clinicData['has_structure'],
            clinicData['avariable_treatment'],
            clinicData['home_care'],
            clinicData['affiliate_check'],
            personData['dentist'],
            personData['dental_technician'],
            personData['dental_assistant'],
            personData['dental_hygienist'],
            personData['average_people_count'],
            baseData['latitude'],
            baseData['longitude'],
            page,
            clinicData['medical_department']
        ]


        writer.writerow(data)
        print(index, clinic_id)
        # print(data)

    csv_file.close()

init()

