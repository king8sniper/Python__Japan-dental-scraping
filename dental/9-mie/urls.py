# from bs4 import BeautifulSoup
import requests
import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

base_url = 'http://www.qq.pref.mie.jp/WP0101/RP010101BL.do'
search_base_url = 'https://www.qq.pref.mie.lg.jp/qq24/qqport/kenmintop/hospital/fk9127.php'

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

        table_element = driver.find_element(By.CSS_SELECTOR, 'table[style*="font-size:90%"][class="tblConclusion"]')
        a_elements = table_element.find_elements(By.XPATH, '//a[@title="地図"]')

        for a_element in a_elements:
            clinic_id = a_element.get_attribute('href').split("'")[1]
            url_write(clinic_id, page)
            
        if len(driver.find_elements(By.XPATH, "//a[text()='次のページ']")) > 0:
            btn_next = driver.find_element(By.XPATH, "//a[text()='次のページ']")
            btn_next.click()
        else :
            driver.close()





def main():
    driver = start_driver()
    driver.maximize_window()
    driver.get(search_base_url)

    time.sleep(3)
    # driver.find_element(By.XPATH, '//a[@href="/qq15/qqport/kenmintop/hospital/fk9117.php" and @class="link-box b-cl"]').click()
    # time.sleep(3)
    element = driver.find_element(By.XPATH, '//img[@alt="診療科目から探す" and @title="診療科目から探す"]')
    element.click()
    time.sleep(3)

    checkbox1 = driver.find_element(By.XPATH, '//input[@id="TimeS3"]')
    checkbox2 = driver.find_element(By.XPATH, '//input[@type="checkbox" and @name="kamoku[]" and @value="z43" and @id="kamoku43" and @class="big"]')
    checkbox1.click()
    time.sleep(1)
    checkbox2.click()
    time.sleep(3)

    next_btn = driver.find_element(By.XPATH, '//input[@type="image" and @alt="次へ進む" and @title="次へ進む"]')
    next_btn.click()
    time.sleep(5)

    try:
        total_page_element = driver.find_element(By.XPATH, "//a[text()='最後のページ']")
        onclick_value = total_page_element.get_attribute('onclick')
        total_page = int(onclick_value.split(',')[1].strip().replace(');', '')) + 1
    except:
        print("not selected.")
        total_page = 41

    get_urls(driver, total_page)

    


if __name__ == '__main__':
    main()
