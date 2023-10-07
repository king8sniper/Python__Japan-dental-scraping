import requests
import time
import csv
import jaconv
import re
import json
import datetime
from dateutil.parser import parse
from normalize_japanese_addresses import normalize
import numpy as np
import builtins

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


WAIT_SEC = 20

f = open("urls_test.txt", "r")

data = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url',
        '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
        '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)',
        '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

fc = open('yamanashi.csv', 'a', newline='', encoding='utf-8')
# Create a CSV writer object
writer = csv.writer(fc)
# Write the data to the CSV file
writer.writerow(data)


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



def start_driver():
    # Selenium用のウェブドライバーを初期化し、さまざまなオプションで安定した最適なパフォーマンスを得る。
    # Selenium用のChromeドライバーオプションを設定。
    options = webdriver.ChromeOptions()
    # クリーンなブラウジングセッションのためにブラウザ拡張を無効にする。
    options.add_argument('--disable-extensions')
    # ブラウザを最大化したウィンドウで開始。参考: https://stackoverflow.com/a/26283818/1689770
    options.add_argument('--start-maximized')
    # 互換性向上のためにサンドボックスを無効にする。参考: https://stackoverflow.com/a/50725918/1689770
    options.add_argument('--no-sandbox')
    # より安定した動作のためにこのオプションを追加。参考: https://stackoverflow.com/a/50725918/1689770
    options.add_argument('--disable-dev-shm-usage')

    # 主処理
    try:
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)

    except ValueError:
        # 最新バージョンのChromeドライバーを取得してインストール。
        url = r'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'
        response = requests.get(url)
        data_dict = response.json()
        latest_version = data_dict["channels"]["Stable"]["version"]

        driver_path = ChromeDriverManager(version=latest_version).install()
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)

    except PermissionError:  # 暫定処理 参考: https://note.com/yuu________/n/n14d97c155e5e
        try:
            driver = webdriver.Chrome(service=Service(
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.141\\chromedriver.exe'), options=options)
        except:
            driver = webdriver.Chrome(service=Service(
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.140\\chromedriver.exe'), options=options)

    # ブラウザウィンドウを最大化。
    driver.maximize_window()
    # ウェブドライバの待機時間を設定。
    wait = WebDriverWait(driver, WAIT_SEC)
    return driver


def get_base_data(html):
    baseData = {}
    timeStamp = datetime.date.today()
    baseData['storename'] = html.find_element(By.ID, 'lblKikanName').text if len(
        html.find_elements(By.ID, 'lblKikanName')) > 0 else '-'
    baseData['updated_at'] = html.find_element(By.ID, 'lblLastUpdate').text.split(
        ' ')[0] if len(html.find_elements(By.ID, 'lblLastUpdate')) > 0 else '-'
    baseData['address'] = html.find_element(By.ID, 'lblLocationName').text if len(
        html.find_elements(By.ID, 'lblLocationName')) > 0 else '-'
    try:
        storeAddressNormalize = "".join(list(normalize(baseData['address']).values())[0:4])
        baseData['address_normalize_1'] = _split_buildingName(storeAddressNormalize)[0]
        baseData['address_normalize_2'] = _split_buildingName(storeAddressNormalize)[1]
    except:
        baseData['address_normalize_1'] = baseData['address_normalize_2'] = "na"
    baseData['founder_name'] = html.find_element(By.ID, 'lblKaisetsuName').text.replace(
        '\u3000', ' ') if len(html.find_elements(By.ID, 'lblKaisetsuName')) > 0 else '-'
    baseData['admin_name'] = html.find_element(By.ID, 'lblKanriName').text.replace(
        '\u3000', ' ') if len(html.find_elements(By.ID, 'lblKanriName')) > 0 else '-'
    
    baseData['timestamp'] = timeStamp
    try:
        department_spans = html.find_element(By.ID, 'tblBKamoku').find_elements(By.ID, 'lblKamokuName')
        print(department_spans)
        medical_department = "["
        for department_span in department_spans:
            medical_department += (department_span.text + ", ")
        medical_department += "]"
    except:
        medical_department = "na"

    baseData['medical_department'] = medical_department


    return baseData


def get_amenity_data(html):
    true_elements = html.find_elements(By.XPATH, "//td[text()='有り']")
    span_elements = html.find_elements(By.XPATH, "//span[text()='有り']")
    if len(span_elements) > 0:
        for s_el in span_elements:
            true_elements.append(s_el.find_element(By.XPATH, '..'))

    if len(true_elements) > 0:
        amenityData = []
        for t_el in true_elements:
            service = t_el.find_element(
                By.XPATH, "./preceding-sibling::td[1]").find_element(By.TAG_NAME, 'span').text
            amenityData.append(service)
    else:
        amenityData = 'na'

    return amenityData


def get_contents_data(html):
    contentsData = {}
    general_elements = []
    if len(html.find_elements(By.XPATH, "//span[contains(text(), '歯科領域')]")) > 0:
        general_ancestor = html.find_element(
            By.XPATH, "//span[contains(text(), '歯科領域')]").find_element(By.XPATH, './ancestor::table[1]')
        general_elements = general_ancestor.find_element(
            By.XPATH, "following-sibling::table").find_elements(By.ID, 'lblIryokinoName')
    if len(general_elements) > 0:
        general_dentistry = []
        for g_el in general_elements:
            general_dentistry.append(g_el.text)
    else:
        general_dentistry = 'na'
    contentsData['general_dentistry'] = general_dentistry

    oral_elements = []
    if len(html.find_elements(By.XPATH, "//span[contains(text(), '口腔外科領域')]")) > 0:
        oral_ancestor = html.find_element(
            By.XPATH, "//span[contains(text(), '口腔外科領域')]").find_element(By.XPATH, './ancestor::table[1]')
        oral_elements = oral_ancestor.find_element(
            By.XPATH, "following-sibling::table").find_elements(By.ID, 'lblIryokinoName')
    if len(oral_elements) > 0:
        oral_surgery = []
        for o_el in oral_elements:
            oral_surgery.append(o_el.text)
    else:
        oral_surgery = 'na'
    contentsData['oral_surgery'] = oral_surgery

    homecare_elements = []
    if len(html.find_elements(By.XPATH, "//span[contains(text(), '在宅医療') and @id='lblZaitakuiryo']")) > 0:
        homecare_elements = html.find_element(By.XPATH, "//span[contains(text(), '在宅医療') and @id='lblZaitakuiryo']").find_element(
            By.XPATH, "following-sibling::table").find_elements(By.ID, "lblZaitakuiryoName")
    if len(homecare_elements) > 0:
        homecare = []
        for h_el in homecare_elements:
            homecare.append(h_el.text)
    else:
        homecare = 'na'
    contentsData['homecare'] = homecare

    collaboration_elements = []
    if len(html.find_elements(By.XPATH, "//span[contains(text(), '連携の有無') and @id='lblZaitakuiryo']")) > 0:
        collaboration_elements = html.find_element(By.XPATH, "//span[contains(text(), '連携の有無') and @id='lblZaitakuiryo']").find_element(
            By.XPATH, "following-sibling::table").find_elements(By.ID, "lblZaitakuiryoName")
    if len(collaboration_elements) > 0:
        collaboration = []
        for c_el in collaboration_elements:
            collaboration.append(c_el.text)
    else:
        collaboration = 'na'
    contentsData['collaboration'] = collaboration

    return contentsData


def get_actual_data(html):
    actualData = {}
    if len(html.find_elements(By.XPATH, "//span[text()='歯科医師']")) > 0:
        dentist_ancestor = html.find_element(
            By.XPATH, "//span[text()='歯科医師']").find_element(By.XPATH, './ancestor::tr[@id="trJininhaichi"]')
        den_total = dentist_ancestor.find_element(By.ID, 'lblSoSouSu').text
        den_full = dentist_ancestor.find_element(By.ID, 'lblJoSouSu').text
        den_part = dentist_ancestor.find_element(By.ID, 'lblHjSouSu').text
        actualData['dentist'] = den_total+'|' + den_full + '|' + den_part
    else:
        actualData['dentist'] = 'na'

    if len(html.find_elements(By.XPATH, "//span[text()='歯科衛生士']")) > 0:
        hygienist_ancestor = html.find_element(
            By.XPATH, "//span[text()='歯科衛生士']").find_element(By.XPATH, './ancestor::tr[@id="trJininhaichi"]')
        hyg_total = hygienist_ancestor.find_element(By.ID, 'lblSoSouSu').text
        hyg_full = hygienist_ancestor.find_element(By.ID, 'lblJoSouSu').text
        hyg_part = hygienist_ancestor.find_element(By.ID, 'lblHjSouSu').text
        actualData['dental_hygienist'] = hyg_total + \
            '|' + hyg_full + '|' + hyg_part
    else:
        actualData['dental_hygienist'] = 'na'

    if len(html.find_elements(By.ID, "pnlGairaiKanjyasu")) > 0 and len(html.find_elements(By.ID, "tblGairaiKanjyasu")) > 0:
        actualData['day_patients'] = html.find_element(By.ID, "pnlGairaiKanjyasu").find_element(
            By.XPATH, 'table[@id="tblGairaiKanjyasu"]').find_element(By.TAG_NAME, 'tr').find_elements(By.TAG_NAME, 'td')[1].text
    else:
        actualData['day_patients'] = 'na'

    return actualData


def main():
    driver = start_driver()
    driver.maximize_window()

    index = 0
    for line in f:
        page = line.split(',')[0]
        url = line.split(',')[1]
        print(url)
        driver.get(url)
        data = {}

        baseData = get_base_data(driver)
        if baseData:
            btn_tabs = driver.find_elements(
                By.CSS_SELECTOR, 'a[class="DetailHyper"]')
            btn_tabs[1].click()

        amenityData = get_amenity_data(driver)
        if amenityData:
            btn_tabs = driver.find_elements(
                By.CSS_SELECTOR, 'a[class="DetailHyper"]')
            btn_tabs[3].click()

        contentsData = get_contents_data(driver)
        if contentsData:
            btn_tabs = driver.find_elements(
                By.CSS_SELECTOR, 'a[class="DetailHyper"]')
            btn_tabs[4].click()

        actualData = get_actual_data(driver)
        if actualData:
            data = [
                baseData['timestamp'],
                baseData['storename'],
                baseData['address'],
                baseData['address_normalize_1'],
                baseData['address_normalize_2'],
                baseData['updated_at'],
                url,
                'na',
                baseData['founder_name'],
                baseData['admin_name'],
                contentsData['general_dentistry'],
                contentsData['oral_surgery'],
                'na',
                'na',
                amenityData,
                'na',
                contentsData['homecare'],
                contentsData['collaboration'],
                actualData['dentist'],
                'na',
                'na',
                actualData['dental_hygienist'],
                actualData['day_patients'],
                'na',
                'na',
                page,
                baseData['medical_department']
            ]
            writer.writerow(data)

        index += 1
        print(index)

    fc.close()
    driver.close()
    time.sleep(5000)


if __name__ == '__main__':
    main()
