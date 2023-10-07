from bs4 import BeautifulSoup
import requests
import csv
import jaconv
import re
import json
import csv
import time
import datetime
from normalize_japanese_addresses import normalize
import numpy as np

f = open("urls.txt", "r")

data = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url',
        '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
        '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)',
        '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

fc = open('iwate.csv', 'a', newline='', encoding='utf-8')
# Create a CSV writer object
writer = csv.writer(fc)
# Write the data to the CSV file
writer.writerow(data)


# Functions

# Functions  predefined
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
    result = result if type(result) == str else result.tolist() if type(
        result) == np.ndarray else "error"

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
    result = result if type(result) == str else result.tolist() if type(
        result) == np.ndarray else "error"

    return result

# -------------------------------------------------------------------------------------


def _split_buildingName(arg):
    # print(1, arg)
    """
    建物名を切り分ける内部関数。
    """
    # ハイフンの一般化
    address = normalization(arg)
    hyphens = '-˗ᅳ᭸‐‑‒–—―⁃⁻−▬─━➖ーㅡ﹘﹣－ｰ𐄐𐆑 '
    address = re.sub("|".join(hyphens), "-", address)
    address = re.sub(r"([ｱ-ﾝ])(-)", r"\1ｰ", address)

    # 丁目、番地、号などで使われる漢字の定義
    chome_poplist = ["ﾉ切", "町目", "地割", "丁目", "丁", "組",
                     "番町", "番地", "番目", "番", "号室", "号", "街区", "画地"]
    chome_popset = r"|".join(chome_poplist)
    chome_holdlist = ["条東", "条西", "条南", "条北", "条通", "条", "東", "西", "南", "北"]
    chome_holdset = r"|".join(chome_holdlist)
    chome_alllist = chome_popset + chome_holdset
    chome_allset = r"|".join(chome_alllist)

    # separate address
    result = re.findall(re.compile(
        f"(.*\d\[{chome_allset}\]*)|(\D+\[-\d\]+)|(.*)"), address)

    # convert kanji into hyphen
    result = [[re.sub(f"(\d+)({chome_popset})", r"\1-", "".join(t))
               for t in tl] for tl in result]

    # concat all
    result = ["".join(t) for t in result]
    result = "".join(result)

    # special case handling (1ﾉ3 1区1)
    result = re.sub(r"([^ｱｰﾝ])(ﾉ|ｰ)(\d)", r"\1-\3", result)
    result = re.sub(r"(\d)(区)(\d)", r"\1-\3", result)
    result = re.sub("--", "-", result)

    # separate into [japanese] + [number + hyphen] chunks
    result = re.findall(re.compile(
        f"(\D+[-\d]+[{chome_holdset}]*[-\d]+)|(\D+[-\d]+)|(.*)"), result)
    result = [t for t in ["".join(tl) for tl in result] if t != ""]
    # print(3, result)
    # merge [number + hyphen] chunks
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


def get_page(url, category):
    response = requests.get(url.replace('detail2', category))
    return response


def get_soup(html):
    soup = BeautifulSoup(html, 'lxml')
    return soup


def get_base_data(html):
    soup = get_soup(html)
    timeStamp = datetime.date.today()
    baseData = {
        'updated_at': soup.find('td', {"class": "scel0"}).find('b').text,
        'timestamp': timeStamp
    }
    table_items = soup.find('table', {"class": "stabl2"}).findAll(
        'table', {"class": "stabl3"})
    baseData['storename'] = table_items[0].findAll('tr')[1].find(
        'td', {"class": "scel4"}).find('b').text.replace('\u3000', ' ')
    baseData['founder_name'] = table_items[1].findAll('tr')[2].find(
        'td', {"class": "scel4"}).text.replace('\u3000', ' ')
    baseData['founder_type'] = table_items[1].findAll('tr')[3].find(
        'td', {"class": "scel4"}).text.replace('\u3000', ' ')
    baseData['admin_name'] = table_items[2].findAll('tr')[2].find(
        'td', {"class": "scel4"}).text.replace('\u3000', ' ')
    baseData['address'] = table_items[3].findAll('tr')[3].find(
        'td', {"class": "scel4"}).text.strip()
    try:
        storeAddressNormalize = "".join(
            list(normalize(baseData['address']).values())[0:4])
        baseData['address_normalize_1'] = _split_buildingName(storeAddressNormalize)[
            0]
        baseData['address_normalize_2'] = _split_buildingName(storeAddressNormalize)[
            1]
    except:
        baseData['address_normalize_1'] = baseData['address_normalize_2'] = "na"
    # print(baseData)
    return baseData


def get_department_data(html):
    soup = get_soup(html)
    table_elements = soup.find('table', {"class": "stabl2"}).findAll(
        'table', {"class": "stabl3"})
    departmentData = []
    for td_el in table_elements[0].findAll('td', {"class", "scel4"}):
        if td_el.text == '\u3000':
            break
        departmentData.append(td_el.text)
    # print(departmentData)
    return departmentData


def get_service_data(html):
    soup = get_soup(html)
    table_elements = soup.find('table', {"class": "stabl2"}).findAll(
        'table', {"class": "stabl3"})
    serviceData = []
    if table_elements[0].find('td', {"class": "scel4"}).text.strip() == '有':
        serviceData.append(table_elements[0].find(
            'td', {"class": "scel3"}).text.strip())
    if table_elements[2].find('td', {"class": "scel4"}).find('img') is not None:
        serviceData.append(
            '障がい者に対する配慮('+table_elements[2].find('td', {"class": "scel4"}).text.strip().replace('\n', ',').replace('\xa0', ' ')+')')
    if table_elements[3].find('td', {"class": "scel4"}).find('img') is not None:
        serviceData.append(
            '車椅子利用者に対する配慮('+table_elements[3].find('td', {"class": "scel4"}).text.strip().replace('\n', ',').replace('\xa0', ' ')+')')
    if table_elements[4].find('td', {"class": "scel4"}).find('img') is not None:
        serviceData.append(table_elements[4].find(
            'td', {"class": "scel4"}).text.strip().replace('\n', ',').replace('\xa0', ' '))
    print('service', serviceData)
    return serviceData if len(serviceData) > 0 else 'na'


def get_general_data(html):
    soup = get_soup(html)
    table_elements = soup.find("table", {"class", "stabl2"}).findAll(
        "table", {"class", "stabl3"})
    generalData = {}
    total = table_elements[5].findAll('td', {"class": "scel4"})
    homecare_element = table_elements[5].find('td', string='在宅医療')
    collaboration_element = table_elements[5].find('td', string='連携の有無')
    collaboration = []
    homecare = []
    if homecare_element is None:
        if collaboration_element is None:
            collaboration = 'na'
        else:
            for t in total:
                collaboration.append(t.text)
        homecare = 'na'
    else:
        if collaboration_element is None:
            for t in total:
                homecare.append(t.text)
            collaboration = 'na'
        else:
            table_string = str(table_elements[5])
            htd_elements = table_string.split(
                '<td class="scel3"')[2].split('<td')
            for htd_el in htd_elements[1:]:
                homecare.append(htd_el.split('</td>')
                                [0].split('>')[1])
            ctd_elements = table_string.split(
                '<td class="scel3"')[3].split('<td')
            for ctd_el in ctd_elements[1:]:
                collaboration.append(ctd_el.split(
                    '</td>')[0].split('>')[1])
    generalData['homecare'] = homecare
    generalData['collaboration'] = collaboration

    dentist_element = table_elements[7].find('td', string='歯科医師')
    hygienist_element = table_elements[7].find('td', string='歯科衛生士')
    tech_element = table_elements[7].find('td', string='歯科技工士')
    if not dentist_element is None:
        den_total = dentist_element.find_next_sibling(
            'td').text.strip().split(' 人')[0]
        generalData['dentist'] = den_total+'|' + '-' + \
            '|' + '-' if den_total != '' else 'na'
    else:
        generalData['dentist'] = 'na'
    if not hygienist_element is None:
        hyg_total = hygienist_element.find_next_sibling(
            'td').text.strip().split(' 人')[0]
        generalData['hygienist'] = hyg_total+'|' + \
            '-' + '|' + '-' if hyg_total != '' else 'na'
    else:
        generalData['hygienist'] = 'na'
    if not tech_element is None:
        tech_total = tech_element.find_next_sibling(
            'td').text.strip().split(' 人')[0]
        generalData['tech'] = tech_total+'|' + '-' + \
            '|' + '-' if tech_total != '' else 'na'
    else:
        generalData['tech'] = 'na'

    print(generalData)

    return generalData


def get_professional_data(html):
    soup = get_soup(html)
    table_elements = soup.find("table", {"class", "stabl2"}).findAll(
        "table", {"class", "stabl3"})
    professionalData = {}
    total = table_elements[4].findAll('td', {"class": "scel4"})
    dental_element = table_elements[4].find('td', string='歯科領域')
    oral_element = table_elements[4].find('td', string='口腔外科領域')
    dental = []
    oral = []
    if dental_element is None:
        if oral_element is None:
            oral = 'na'
        else:
            for t in total:
                oral.append(t.text)
        dental = 'na'
    else:
        if oral_element is None:
            for t in total:
                dental.append(t.text)
            oral = 'na'
        else:
            table_string = str(table_elements[4])
            dtd_elements = table_string.split(
                '<td class="scel3"')[2].split('<td class="scel4"')
            for dtd_el in dtd_elements[1:]:
                dental.append(dtd_el.split('</td>')
                              [0].split('>')[1])
            otd_elements = table_string.split(
                '<td class="scel3"')[3].split('<td class="scel4"')
            for otd_el in otd_elements[1:]:
                oral.append(otd_el.split('</td>')
                            [0].split('>')[1])
    professionalData['dental'] = dental
    professionalData['oral'] = oral

    day_patients = soup.find('td', string='前年度1日平均患者数').find_parent(
        'tr').find_next_sibling('tr').find('td').text.strip()
    professionalData['day_patients'] = day_patients.split(
        ' 人')[0] if day_patients != '' else 'na'
    print(professionalData)

    return professionalData


def main():
    for line in f:
        page = line.split(',')[0]
        url = line.split(',')[1]
        print(url)
        data = {}
        # url = 'http://www.med-info.pref.iwate.jp/imin/kikan/show-shika-detail2.do?f.kikanCd=03300431&by='
        baseInfo = get_page(url, 'detail1')
        if baseInfo.status_code == 200:
            baseData = get_base_data(baseInfo.text)

        departmentInfo = get_page(url, 'detail2')
        if departmentInfo.status_code == 200:
            departmentData = get_department_data(departmentInfo.text)

        serviceInfo = get_page(url, 'detail5')
        if serviceInfo.status_code == 200:
            serviceData = get_service_data(serviceInfo.text)

        generalInfo = get_page(url, 'detail6')
        if generalInfo.status_code == 200:
            generalData = get_general_data(generalInfo.text)

        professionalInfo = get_page(url, 'detail7')
        if professionalInfo.status_code == 200:
            professionalData = get_professional_data(professionalInfo.text)

        data = [
            baseData['timestamp'],
            baseData['storename'],
            baseData['address'],
            baseData['address_normalize_1'],
            baseData['address_normalize_2'],
            baseData['updated_at'],
            url,
            baseData['founder_type'],
            baseData['founder_name'],
            baseData['admin_name'],
            professionalData['dental'],
            professionalData['oral'],
            'na',
            'na',
            serviceData,
            'na',
            generalData['homecare'],
            generalData['collaboration'],
            generalData['dentist'],
            generalData['tech'],
            'na',
            generalData['hygienist'],
            professionalData['day_patients'],
            'na',
            'na',
            page,
            departmentData
        ]
        writer.writerow(data)

    fc.close()


if __name__ == '__main__':
    main()
