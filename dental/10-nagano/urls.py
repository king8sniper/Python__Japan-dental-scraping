# from bs4 import BeautifulSoup
import requests
import time
import re
import math
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

base_url = 'http://www.qq.pref.nagano.lg.jp/qq20/WP0101/RP010101BL.do'
search_base_url = 'http://www.qq.pref.nagano.lg.jp/pb_dt_index'

WAIT_SEC = 20

f = open("urls.txt", "a")

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

def url_write(clinic_id, page):
    f.write(str(page)+","+clinic_id+",\n")

def get_urls(driver, total_page):
    for page in range(1, total_page + 1):

        a_elements = driver.find_elements(By.XPATH, '//img[@src="http://www.qq.pref.nagano.lg.jp/static/images/view_atr.gif?da8dd462a122025612bec462c349366c"]/..')
        print(page, len(a_elements))
        for a_element in a_elements:
            clinic_url = a_element.get_attribute('href')
            url_write(clinic_url, page)

        time.sleep(2)

        next_elements = driver.find_element(By.XPATH, "//ul[@class='pagination pagination-sm']/li[@class='active']").find_elements(By.XPATH, "./following-sibling::li")
        print(len(next_elements))
        time.sleep(1)
        if len(next_elements) > 0:
            next_btn = driver.find_element(By.XPATH, "//ul[@class='pagination pagination-sm']/li[@class='active']/following-sibling::li[1]/a")
            next_btn.click()
            time.sleep(2)
            
        else :
            print('not found')
            driver.close()





def main():
    driver = start_driver()
    driver.maximize_window()
    driver.get(search_base_url)
    time.sleep(3)

    date_checkbox = driver.find_element(By.XPATH, "//input[@type='radio' and @id='select_inst3']")
    date_checkbox.click()
    time.sleep(1)

    location_select = driver.find_element(By.XPATH, "//select[@name='BLOCK_CODE']")
    location_select.find_element(By.XPATH, "//option[text()='上記以外']").click()
    time.sleep(2)

    distance_select = driver.find_element(By.XPATH, "//select[@name='area2']")
    distance_select.find_element(By.XPATH, "//option[text()='すべて']").click()
    time.sleep(2)

    department_checkbox = driver.find_element(By.XPATH, "//div[@id='kamoku1_title2']")
    department_checkbox.click()
    time.sleep(1)

    next_btn = driver.find_element(By.XPATH, '//a[@id="btn_type02"]')
    next_btn.click()
    time.sleep(3)

    try:
        page_size = 10
        total_items = int(driver.find_element(By.XPATH, '//div[@class="col-xs-12 col-sm-12 col-md-12 col-lg-12"]/strong[1]').text)
        total_page = math.ceil(total_items / page_size)
        print(total_page)
    except:
        print("not selected.")
        total_page = 106

    get_urls(driver, total_page)

    


if __name__ == '__main__':
    main()
