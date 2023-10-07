import requests
import time
import csv
import jaconv
import re
import datetime
from normalize_japanese_addresses import normalize
import numpy as np

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


WAIT_SEC = 20
USERNAME='Administrator'

f = open("urls.txt", "r")

data = ['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url',
        '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
        '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)',
        '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

fc = open('kanagawa.csv', 'a', newline='', encoding='utf-8')
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
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.179\\chromedriver.exe'), options=options)
        except:
            driver = webdriver.Chrome(service=Service(
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.179\\chromedriver.exe'), options=options)

    # ブラウザウィンドウを最大化。
    driver.maximize_window()
    # ウェブドライバの待機時間を設定。
    wait = WebDriverWait(driver, WAIT_SEC)
    return driver


def get_base_data(html):
    baseData = {}
    timeStamp = datetime.date.today()
    baseData['storename'] = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_ctl58_lblShisetsuName').text if len(
        html.find_elements(By.ID, 'ctl00_ContentPlaceHolderContents_ctl58_lblShisetsuName')) > 0 else 'na'
    print('baseData')
    baseData['updated_at'] = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_lblLastUpdateDate').text.split('最終報告日')[1] if html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_lblLastUpdateDate').text!='休業中' else '休業中' if len(html.find_elements(By.ID, 'ctl00_ContentPlaceHolderContents_lblLastUpdateDate')) > 0 else 'na'
    baseData['address'] = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_ctl58_lblAddress').text.replace('\u3000', ' ') if len(
        html.find_elements(By.ID, 'ctl00_ContentPlaceHolderContents_ctl58_lblAddress')) > 0 else 'na'
    try:
        storeAddressNormalize = "".join(list(normalize(baseData['address']).values())[0:4])
        baseData['address_normalize_1'] = _split_buildingName(storeAddressNormalize)[0]
        baseData['address_normalize_2'] = _split_buildingName(storeAddressNormalize)[1]
    except:
        baseData['address_normalize_1'] = baseData['address_normalize_2'] = "na"
    baseData['founder_name'] = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_lblKaisetsuName').text.replace(
        '\u3000', ' ') if len(html.find_elements(By.ID, 'ctl00_ContentPlaceHolderContents_lblKaisetsuName')) > 0 else '-'
    baseData['admin_name'] = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_lblKanName').text.replace(
        '\u3000', ' ') if len(html.find_elements(By.ID, 'ctl00_ContentPlaceHolderContents_lblKanName')) > 0 else '-'
    
    baseData['timestamp'] = timeStamp
    try:
        medical_department = html.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_lblShinryoKamoku').text
    except:
        medical_department = "na"

    baseData['medical_department'] = medical_department

    print(baseData)
    return baseData


def get_service_data(html):
    serviceData=[]
    table_element = html.find_elements(By.XPATH,"//table[@class='DetailTable']")[1]
    
    dperson_td = table_element.find_element(By.XPATH, "//td[text()='障害者に対するサービス内容']")
    dperson_el = dperson_td.find_element(By.XPATH,"./following-sibling::td")
    if dperson_el.text !='':
        dperson = "障害者に対するサービス内容(" + dperson_el.text.replace('\n',',')+ ")" 
        serviceData.append(dperson)

    slang_td = table_element.find_element(By.XPATH, "//td[text()='車椅子等利用者に対する配慮']")
    slang_el = slang_td.find_element(By.XPATH,"./following-sibling::td")
    if slang_el.text !='':
        slang = "車椅子等利用者に対する配慮(" + slang_el.text.replace('\n',',')+ ")" 
        serviceData.append(slang)

    smoking_td = table_element.find_element(By.XPATH, "//td[text()='受動喫煙を防止するための措置']")
    smoking_el = smoking_td.find_element(By.XPATH,"./following-sibling::td")
    if smoking_el.text !='':
        smoking = "受動喫煙を防止するための措置(" + smoking_el.text.replace('\n',',')+ ")" 
        serviceData.append(smoking)
    
    print(serviceData)
    return serviceData if len(serviceData)>0 else 'na'


def get_number(string):
    match = re.search(r"\d+(\.\d+)?", string)
    if match:
        number = match.group()
        return number
    

def get_system_data(html):
    systemData={
        "dentist":"na",
        "hygienist":"na",
    }
    table_element=html.find_elements(By.XPATH,"//table[@class='DetailTable']")[1]
    # print(table_element.get_attribute('outerHTML'))
    staffing_td=table_element.find_element(By.XPATH, "//td[@class='DetailTitle' and contains(text(), '人員配置')]")
    staffing_elements = staffing_td.find_element(By.XPATH,"./following-sibling::td").text.split('\n')
    for staffing_el in staffing_elements:
        if '歯科医師数' in staffing_el:
            dentist=get_number(staffing_el)
            systemData['dentist']=dentist+'|-|-' if dentist else 'na'
        elif '歯科衛生士数' in staffing_el:
            hygienist=get_number(staffing_el)
            systemData['hygienist']=hygienist+'|-|-' if hygienist else 'na'

    print(systemData)
    return systemData

def  get_treatment_data(html):
    table_element = html.find_elements(By.XPATH,"//table[@class='DetailTable']")[1]
    dental_td = table_element.find_element(By.XPATH, "//td[text()='歯科領域']")
    dental_el = dental_td.find_element(By.XPATH,"./following-sibling::td")
    dental=dental_el.text.replace('\n',',') if dental_el.text != '' else 'na' 

    oral_td = table_element.find_element(By.XPATH, "//td[text()='歯科口腔外科領域']")
    oral_el = oral_td.find_element(By.XPATH,"./following-sibling::td")
    oral=oral_el.text.replace('\n',',') if oral_el.text != '' else 'na' 
    
    treatmentData={
        "dental":dental,
        "oral":oral
    }
    print(treatmentData)
    return treatmentData

def get_homecare_data(html):
    table_element = html.find_elements(By.XPATH,"//table[@class='DetailTable']")[1]
    homecare_td = table_element.find_element(By.XPATH, "//td[text()='在宅医療']")
    homecare_el = homecare_td.find_element(By.XPATH,"./following-sibling::td")
    homecare=homecare_el.text.replace('\n',',') if homecare_el.text != '' else 'na' 

    collaboration_td = table_element.find_element(By.XPATH, "//td[text()='他の施設との連携の有無']")
    collaboration_el = collaboration_td.find_element(By.XPATH,"./following-sibling::td")
    collaboration=collaboration_el.text.replace('\n',',') if collaboration_el.text != '' else 'na' 
    
    homecareData={
        "homecare":homecare,
        "collaboration":collaboration
    }
    print(homecareData)
    return homecareData



def get_result_data(html):
    table_element=html.find_elements(By.XPATH,"//table[@class='DetailTable']")[1]
    day_patients_td=table_element.find_element(By.XPATH, "//td[@class='DetailTitle' and contains(text(), '日当りの患者数')]")
    day_patients_el = day_patients_td.find_element(By.XPATH,"./following-sibling::td").text.split('外来患者数')[1] if len(day_patients_td.find_element(By.XPATH,"./following-sibling::td").text.split('外来患者数'))>1 else 'na'
    day_patients=get_number(day_patients_el)
    resultData=day_patients if day_patients else 'na'

    print(resultData)
    return resultData


def main():
    driver = start_driver()
    driver.maximize_window()

    for line in f:
        page = line.split(',')[0]
        url = line.split(',')[1]
        print(url)
        driver.get(url)
        data = {}

        baseData = get_base_data(driver)
        if baseData:
            service_tab = driver.find_element(By.ID,"ctl00_ContentPlaceHolderContents_btnDetail03")
            service_tab.click()

        serviceData = get_service_data(driver)
        if serviceData:
            system_tab = driver.find_element(By.XPATH,"//input[@alt='提供する医療の体制']")
            system_tab.click()

        systemData = get_system_data(driver)
        if systemData:
            treatment_tab = driver.find_element(By.XPATH,"//input[@alt='対応する疾患及び治療１']")
            treatment_tab.click()

        treatmentData = get_treatment_data(driver)
        if treatmentData:
            homecare_tab = driver.find_element(By.XPATH,"//input[@alt='対応する在宅医療']")
            homecare_tab.click()
        homecareData=get_homecare_data(driver)
        if homecareData:
            result_tab = driver.find_element(By.XPATH,"//input[@alt='実績・結果']")
            result_tab.click()
        resultData=get_result_data(driver)
        if resultData:
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
                treatmentData['dental'],
                treatmentData['oral'],
                'na',
                'na',
                serviceData,
                'na',
                homecareData['homecare'],
                homecareData['collaboration'],
                systemData['dentist'],
                'na',
                'na',
                systemData['hygienist'],
                resultData,
                'na',
                'na',
                page,
                baseData['medical_department']
            ]
            writer.writerow(data)

    fc.close()
    driver.close()
    time.sleep(10000)


if __name__ == '__main__':
    main()
