# from bs4 import BeautifulSoup
import requests
import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

base_url = 'http://www.mfis.pref.osaka.jp/apqq/qq/men/pwtpmenult01.aspx'
search_base_url = 'https://www.mfis.pref.osaka.jp/ap/qq/sho/pwdnkinosr07_001.aspx?serviceid=pwdnkinosr&shorikbn=1&servicename=%8a%ee%96%7b%8f%ee%95%f1%82%a9%82%e7%92T%82%b7'

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

def url_write(page, clinic_id):
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

def return_li(driver):
    list_li = []
    general_uls = driver.find_elements(By.XPATH, '//table[@id="ctl00_cphdrBody_uclSelectChiku1_tblChiku"]//ul[@class="search_keylist"]')
    for general_ul in general_uls:
        general_lis = general_ul.find_elements(By.XPATH, './li')
        list_li.extend(general_lis)

    return list_li

def eachPage_get_data(driver):
    try:
        page = driver.find_element(By.XPATH, '//a[@class="current"]').text.strip()
    except:
        page = 1

    general_divs = driver.find_elements(By.XPATH, '//div[@class="search_single"]')
    if len(general_divs) > 0:
        for general_div in general_divs:
            general_a = general_div.find_element(By.CLASS_NAME, 'search_single_ttl').find_element(By.TAG_NAME, "a")
            # print(general_a)

            if general_a.get_attribute('href'):
                href = general_a.get_attribute('href')
                pattern = r'kikancd=(\d+)'
                match = re.search(pattern, href)
                kikancd_value = match.group(1)
                
                url_write(page, kikancd_value)
                print(page, kikancd_value)

    try:
        current_li = driver.find_element(By.XPATH, '//a[@class="current"]/..')
        next_lis = current_li.find_elements(By.XPATH, "./following-sibling::li")
        if len(next_lis) > 0:
            current_li.find_element(By.XPATH, "./following-sibling::li").click()
            time.sleep(2)
            eachPage_get_data(driver)
        else:
            print("The end.")

    except:
        print('Only page end.')



def eachTown_get_url(driver, x):
    driver.execute_script("window.open('about:blank', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(search_base_url)
    time.sleep(2)

    list_li = return_li(driver)
    list_li[x].click()
    time.sleep(1)

    submit_btn = driver.find_element(By.XPATH, '//input[@type="submit" and @id="ctl00_cphdrBody_uclCommentButton_btnInput"]')
    submit_btn.click()
    time.sleep(3)

    eachPage_get_data(driver)
    time.sleep(3)

    driver.close()
    driver.switch_to.window(driver.window_handles[0])




def main():
    driver = start_driver()
    driver.maximize_window()
    driver.get(search_base_url)
    time.sleep(3)

    time.sleep(3)
    list_li = return_li(driver)
    list_count = len(list_li)
    time.sleep(2)

    for x in range(71, list_count):
        print('------------------------------>>', x)
        eachTown_get_url(driver, x)


if __name__ == '__main__':
    main()
