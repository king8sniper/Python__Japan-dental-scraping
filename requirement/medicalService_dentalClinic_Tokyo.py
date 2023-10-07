#!/usr/bin/env python
# coding: utf-8

# #### ライブラリのインポート、URLなど各種設定

# In[1]:


### import necessary library
from bs4 import BeautifulSoup
import csv
import datetime
import getpass
import jaconv
from normalize_japanese_addresses import normalize
import numpy as np
import pandas as pd
import random
import re
import requests
import random
import selenium
from selenium import webdriver
import sys
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from urllib.parse import urljoin


# In[2]:


### version
print("Selenium: ", selenium.__version__)
print("Python: ",sys.version)


# In[3]:


### individual configure
SOURCE_NAME = "medicalInfoService" 
BASE_URL = "https://www.himawari.metro.tokyo.jp/qq13/qqport/tomintop/"
START_URL = "https://www.himawari.metro.tokyo.jp/qq13/qqport/tomintop/"
WAIT_SEC = 5
maxTry = 5
dt_now = datetime.datetime.now()
page = 1
num = 0
EXPORT_PATH = r"shops"


# #### ウェブブラウジング系の関数設定

# In[4]:


def start_driver():
    # Selenium用のウェブドライバーを初期化し、さまざまなオプションで安定した最適なパフォーマンスを得る。
    # Selenium用のChromeドライバーオプションを設定。
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-extensions')  # クリーンなブラウジングセッションのためにブラウザ拡張を無効にする。
    options.add_argument('--start-maximized')  # ブラウザを最大化したウィンドウで開始。参考: https://stackoverflow.com/a/26283818/1689770
    options.add_argument('--no-sandbox')  # 互換性向上のためにサンドボックスを無効にする。参考: https://stackoverflow.com/a/50725918/1689770
    options.add_argument('--disable-dev-shm-usage')  # より安定した動作のためにこのオプションを追加。参考: https://stackoverflow.com/a/50725918/1689770

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
            driver = webdriver.Chrome(service=Service(f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.97\\chromedriver.exe'), options=options)
        except:
            driver = webdriver.Chrome(service=Service(f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.96\\chromedriver.exe'), options=options)

    # ブラウザウィンドウを最大化。
    driver.maximize_window()
    # ウェブドライバの待機時間を設定。
    wait = WebDriverWait(driver, WAIT_SEC)

    return driver


# #### 文字列操作系の関数設定

# In[5]:


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


# #### 対象サイトスクレイピング用の関数設定

# In[6]:


def click_search_with_medical_dep(driver):
    search_buttons = driver.find_elements(By.CSS_SELECTOR, "div[class='home-contents'] li a")

    for search_button in search_buttons:
        if search_button.text.strip() == "診療科目で探す":
            search_button.click()
            break
        else:
            pass
        
# -------------------------------------------------------------------------------------
def select_city_buttons(driver):
    select_buttons = driver.find_elements(By.CSS_SELECTOR, "div[id='sectionIn-01'] span[class='button-label']")

    for select_button in select_buttons:
        if select_button.text.strip() == "住所一覧から指定する":
            select_button.click()
            break
        else:
            pass
        
# -------------------------------------------------------------------------------------
def select_city(driver, cityIndex):
    select_city_buttons(driver)
    time.sleep(WAIT_SEC)

    handle_array = driver.window_handles
    driver.switch_to.window(handle_array[-1])

    cities = driver.find_elements(By.CSS_SELECTOR, "div[class='section-main'] a")
    cities[cityIndex].click()
    time.sleep(WAIT_SEC)

    select_buttons = driver.find_elements(By.CSS_SELECTOR, "span[class='button-container']")
    for select_button in select_buttons:
        if select_button.text.strip() == "決定":
            select_button.click()
            break
        else:
            pass
    
    driver.switch_to.window(handle_array[0])
    
    return nCities

# -------------------------------------------------------------------------------------
def select_clinic_type(driver, clinicIndex):
    clinic_select_boxes = driver.find_elements(By.CSS_SELECTOR, "div[id='search-collapse-04'] div[class='col-xs-4']")

    for clinic_select_box in clinic_select_boxes:
        if clinic_select_box.text.strip() == TARGET_CLINIC[clinicIndex]:
            driver.execute_script('arguments[0].click();', clinic_select_box.find_elements(By.CSS_SELECTOR, "input")[0])
            break
        else:
            pass
        
# -------------------------------------------------------------------------------------
def search_button(driver):
    buttons = driver.find_elements(By.CSS_SELECTOR, "span[class='button-label']")
    for button in buttons:
        if button.text.strip() == "検索する":
            button.click()
            break
        else:
            pass
        
# -------------------------------------------------------------------------------------
def get_page_info(driver):
    nClinics = driver.find_elements(By.CSS_SELECTOR, "div[class='search-list-hospital']")
    
    latlon_list = []
    latlonObjects = driver.find_elements(By.CSS_SELECTOR, "div[class='search-list-hospital'] dd > a")
    
    pattern = r"q=([\d.-]+),([\d.-]+)"   
    for latlonObject in latlonObjects:
        text = latlonObject.get_attribute("href")
        
        matches = re.search(pattern, text)
        if matches:
            latitude = matches.group(1)
            longitude = matches.group(2)
        else:
            latitude = "na"
            longitude = "na"
        
        latlon_list.append([latitude, longitude])
    
    return len(nClinics), latlon_list

# -------------------------------------------------------------------------------------
def visit_stores(driver, storeIndex):
    store_objects = driver.find_elements(By.CSS_SELECTOR, "div[class='search-list-hospital-box'] table[class='table'] h3 > a")
    store_objects[storeIndex].click()

# -------------------------------------------------------------------------------------
def switch_window(driver):
    original_window = driver.current_window_handle
    handle_array = driver.window_handles

    # seleniumで操作可能なdriverを切り替える
    driver.switch_to.window(handle_array[-1])
    
    return original_window

# -------------------------------------------------------------------------------------
def scrape_basic_info(driver):
    html = BeautifulSoup(driver.page_source, "lxml")
    
    updateDate = html.select("div[class='article-time']")[0].text.replace("最終報告日：","")
    current_url = driver.current_url
    timeStamp = datetime.date.today()
    
    basic_info = html.select("div[id='tabContent01']")[0]
    tableKeys = [str_clean(t.text.strip()).replace(" ","") for t in basic_info.select("table tr > th")]
    tableValues = [str_clean(t.text.strip()).replace(" ","") for t in basic_info.select("table tr > td")]
    
    try:
        store_name = tableValues[tableKeys.index("正式名称（医療法届出正式名称）")]
    except:
        store_name = "na"
    try:
        founder_type = tableValues[tableKeys.index("開設者種別")]
    except:
        founder_type = "na"
    try:
        founder_name = tableValues[tableKeys.index("開設者名")]
    except:
        founder_name = "na"
    try:
        administrator_name = tableValues[tableKeys.index("管理者名")]
    except:
        administrator_name = "na"
    try:
        store_address = tableValues[tableKeys.index("所在地")]
    except:
        store_address = "na"
    
    storeAddressOriginal = omit_postcode_tel(store_address)

    try:
        storeAddressNormalize = "".join(list(normalize(storeAddressOriginal).values())[0:4])
        storeAddressNormalize_1 = _split_buildingName(storeAddressNormalize)[0]
        storeAddressNormalize_2 = _split_buildingName(storeAddressNormalize)[1]
    except:
        storeAddressNormalize_1 = storeAddressNormalize_2 = "na"
    
    return [timeStamp, store_name, storeAddressOriginal, storeAddressNormalize_1, storeAddressNormalize_2, updateDate, current_url, founder_type, founder_name, administrator_name]

# -------------------------------------------------------------------------------------
def scrape_clinic_service(driver):
    html = BeautifulSoup(driver.page_source, "lxml")
    
    service_info = html.select("div[id='tabContent05']")[0]
    clinic_tables = [t for t in service_info.select("table") if t.has_attr("summary")]
    clinic_table_names = [t["summary"] for t in clinic_tables]

    
    try:
        general_service_table = clinic_tables[clinic_table_names.index("歯科一般領域一覧")]
        general_service = [str_clean(t.text.strip()).replace(" ","") for t in general_service_table.select("tbody th")]
    except:
        general_service = "na"
    
    try:
        oral_surgery_table = clinic_tables[clinic_table_names.index("歯科口腔外科領域一覧")]
        oral_surgery = [str_clean(t.text.strip()).replace(" ","") for t in oral_surgery_table.select("tbody th")]
    except:
        oral_surgery = "na"

    try:
        kids_table = clinic_tables[clinic_table_names.index("小児歯科領域一覧")]
        kids_service = [str_clean(t.text.strip()).replace(" ","") for t in kids_table.select("tbody th")]
    except:
        kids_service = "na"
    
    try:
        orthodontics_table = clinic_tables[clinic_table_names.index("矯正歯科領域一覧")]
        orthodontics_service = [str_clean(t.text.strip()).replace(" ","") for t in orthodontics_table.select("tbody th")]
    except:
        orthodontics_service = "na"
    
    try:
        facility_table = clinic_tables[clinic_table_names.index("施設状況一覧")]
        facility_service = [str_clean(t.text.strip()).replace(" ","") for t in facility_table.select("tbody th")]
    except:
        facility_service = "na"
    
    try:
        anesthesia_table = clinic_tables[clinic_table_names.index("対応可能な麻酔治療一覧")]
        anesthesia_service = [str_clean(t.text.strip()).replace(" ","") for t in anesthesia_table.select("tbody th")]
    except:
        anesthesia_service = "na"
    
    try:
        home_therapy_table = clinic_tables[clinic_table_names.index("在宅医療")]
        home_therapy = [str_clean(t.text.strip()).replace(" ","") for t in home_therapy_table.select("tbody th")]
    except:
        home_therapy = "na"
    
    try:
        collabo_service_table = clinic_tables[clinic_table_names.index("連携の有無")]
        collabo_service = [str_clean(t.text.strip()).replace(" ","") for t in collabo_service_table.select("tbody th")]
    except:
        collabo_service = "na"
    
    return [general_service, oral_surgery, kids_service, orthodontics_service, facility_service, anesthesia_service, home_therapy, collabo_service]

# -------------------------------------------------------------------------------------
def scrape_result_info(driver):
    html = BeautifulSoup(driver.page_source, "lxml")
    
    result_info = html.select("div[id='tabContent06']")[0]
    result_rows = result_info.select("table tbody tr")
    result_keys = [t.select("th")[0].text.strip() for t in result_rows]
    
    try:
        dentists = "|".join([t.text for t in result_rows[result_keys.index("歯科医師")].select("td")])
    except:
        dentists = "na"
    
    try:
        dental_technician = "|".join([t.text for t in result_rows[result_keys.index("歯科技工士")].select("td")])
    except:
        dental_technician = "na"
    
    try:
        dental_assistant = "|".join([t.text for t in result_rows[result_keys.index("歯科助手")].select("td")])
    except:
        dental_assistant = "na"
    
    try:
        dental_hygienist = "|".join([t.text for t in result_rows[result_keys.index("歯科衛生士")].select("td")])
    except:
        dental_hygienist = "na"
    
    try:
        patiensts = "|".join([t.text for t in result_rows[result_keys.index("前年度１日平均外来患者数")].select("td")])
    except:
        patiensts = "na"
        
        
    return [dentists, dental_technician, dental_assistant, dental_hygienist, patiensts]

# -------------------------------------------------------------------------------------
def paging(driver, page):
    next_page_button = driver.find_elements(By.CSS_SELECTOR, "ul[class='hospital-pager'] li[class='next'] a")[-1]
    
    if "disabled" in next_page_button.get_attribute("href"):
        print("no more pages")
        return False, page
    
    else:
        page += 1
        next_page_button.click()
        return True, page
    


# #### 住所処理系の関数設定

# In[7]:


def _omit_postcode_tel(arg):
    """
    郵便番号と電話番号を削除する内部関数。
    """
    # 文字列の正規化と前後の空白を削除
    result = normalization(arg).strip()

    # 郵便番号の削除
    result = re.sub(r"〒.*?\d{2,3}\D*?\d{3,5}\s*", "", result)
    result = re.sub(r"^\d{3}\D*?\d{4}\s*", "", result)

    # 電話番号の削除
    result = re.sub(r"tel.*\d{2,5}.*\d{2,5}.*\d{4}|電話.*\d{2,5}.*\d{2,5}.*\d{4}","",result)

    # 「住所」などの特定の単語の削除
    result = result.replace("住所","").replace("地図ｦ表示","")

    return result

# -------------------------------------------------------------------------------------
def omit_postcode_tel(arg):
    ## universalize
    _func = np.frompyfunc(_omit_postcode_tel, 1, 1)

    ## list to ndarray
    _list = np.array(arg)

    ## get results
    result = _func(_list)

    ## convert data type
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

# -------------------------------------------------------------------------------------
def split_buildingName(arg):
    ## universalize
    _func = np.frompyfunc(_split_buildingName, 1, 1)

    ## list to ndarray
    _list = np.array(arg)

    ## get results
    result = _func(_list)

    ## convert data type
    result = result if type(result) == str else result.tolist() if type(result) == np.ndarray else "error"

    return result


# #### ファイル保存系の関数設定

# In[8]:


def set_columns(FLAG, args):
    if FLAG:
        # ヘッダー行を設定
        csvlist = [[
        "timeStamp",
        "storeName",
        "address_original", 
        "address_normalize[0]",
        "address_normalize[1]"
        ] + args]
    else:
        # 空のリストを設定
        csvlist = []
    return csvlist


# -------------------------------------------------------------------------------------
def write_to_csv(EXPORT_PATH, SOURCE_NAME, dt_now, page, csvlist):
    max_attemts = 5  # 最大試行回数
    delay_between_attempts = 60  # 試行間の遅延（秒）

    # 文字列の正規化
    csvlist = normalization(csvlist)

    # ファイルへの書き込み試行
    for i in range(max_attemts):
        try:
            # ファイルを開き、CSVに書き込む
            with open(EXPORT_PATH + "/" + SOURCE_NAME + "_"  + str(dt_now.year) + "-" + str(dt_now.month) + "-" + str(dt_now.day) + "-" + str(i) + ".csv", "a", newline="", encoding="CP932", errors="replace") as f:
                writer = csv.writer(f)
                print(f"now exported page:{page}", f"extracted {len(csvlist)} stores")
                writer.writerows(csvlist)
                break
        except OSError as e:
            # エラーが発生した場合の処理
            if i < max_attemts - 1:
                time.sleep(delay_between_attempts)
                print(f"OSError: {e}. Retrying...")
                continue
            else:
                raise
                


# #### スクレイピング（メインコード）

# In[9]:


### config
startCityIndex = 0 # min 0
startClinicIndex = 0 # min 0
startPage = 1 # min 1
startStoreIndex = 0 # min 0
nCities = 1 # 千代田区で検索しても東京都全体が検索される
TARGET_CLINIC = ["歯科", "矯正歯科", "小児歯科", "歯科口腔外科"]


# In[ ]:


### open with selenium
driver = start_driver()
driver.maximize_window()
driver.get(START_URL)
time.sleep(WAIT_SEC + np.random.rand()*WAIT_SEC)  

### set csv format
args = ["最終更新日", "URL", "開設者種別", "開設者名", "管理者名", "歯科一般領域一覧", "歯科口腔外科領域一覧", "小児歯科領域一覧", "矯正歯科領域一覧", "施設状況一覧", "対応可能な麻酔治療一覧", "在宅医療", "連携の有無", "歯科医師（総数|常勤|非常勤）", "歯科技工士（総数|常勤|非常勤）", "歯科助手（総数|常勤|非常勤）", "歯科衛生士（総数|常勤|非常勤）", "前年度１日平均外来患者数", "緯度", "経度", "page"]
FLAG = startCityIndex == 0 and startClinicIndex == 0 and startPage == 1 and startStoreIndex == 0
csvlist_header = set_columns(FLAG, args)
csvlist = []

click_search_with_medical_dep(driver)
time.sleep(WAIT_SEC + np.random.rand()*WAIT_SEC)  
select_city_buttons(driver)

for cityIndex in range(startCityIndex, nCities):
    nCities = select_city(driver, cityIndex)

    start_clinic_index = startClinicIndex if cityIndex == startCityIndex else 0
    for clinicIndex in range(start_clinic_index, len(TARGET_CLINIC)):
        select_clinic_type(driver, clinicIndex)
        search_button(driver)
        
        ## initial paging
        for i in range(startPage - 1):
            flag, page = paging(driver, page)
            time.sleep(WAIT_SEC + np.random.rand()*WAIT_SEC)
          
        while True:
            ## get list info
            nClinics, latlon_list = get_page_info(driver) 
            start_store_index = startStoreIndex if page == startPage and clinicIndex == startClinicIndex and cityIndex == startCityIndex else 0
            
            for storeIndex in range(start_store_index, nClinics):                
                # scrape info
                time.sleep(WAIT_SEC + np.random.rand()*WAIT_SEC)  
                visit_stores(driver, storeIndex)
                original_window = switch_window(driver)
                
                basic_info = scrape_basic_info(driver)
                service_info = scrape_clinic_service(driver)
                result_info = scrape_result_info(driver)
                _row = basic_info + service_info + result_info + latlon_list[storeIndex] + [page]

                #Close the tab or window
                driver.close()
                driver.switch_to.window(original_window)

                ## store data
                csvlist.append(_row)

                ## record
                if FLAG:
                    FLAG = False
                    write_to_csv(EXPORT_PATH, SOURCE_NAME, dt_now, page, csvlist_header)
                else:
                    pass

                write_to_csv(EXPORT_PATH, SOURCE_NAME, dt_now, page, csvlist)
                csvlist = []

                latestCityIndex = cityIndex # min 0
                latestClinicIndex = clinicIndex # min 0
                latestPage = page # min 1
                latestStore = storeIndex # min 0

            #paging
            flag, page = paging(driver, page)

            if flag:
                pass
            else:
                print("going to the next category...")
                break

print("done")
driver.close


# In[ ]:




