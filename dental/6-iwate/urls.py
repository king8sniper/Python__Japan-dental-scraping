# from bs4 import BeautifulSoup
import requests
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

base_url = 'http://www.med-info.pref.iwate.jp/imin/kikan/show-search-normal-form.do?by=skamoku'
WAIT_SEC = 30

f = open("urls.txt", "a")


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
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.97\\chromedriver.exe'), options=options)
        except:
            driver = webdriver.Chrome(service=Service(
                f'C:\\Users\\{USERNAME}\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.96\\chromedriver.exe'), options=options)

    # ブラウザウィンドウを最大化。
    driver.maximize_window()
    # ウェブドライバの待機時間を設定。
    wait = WebDriverWait(driver, WAIT_SEC)
    return driver


def url_write(url, page):
    f.write(str(page)+","+url+",\n")


def get_urls(driver, page):
    table_element = driver.find_element(
        By.CSS_SELECTOR, "table[class='table5']")
    tr_elements = table_element.find_elements(By.TAG_NAME, 'tr')[1:]
    print(len(tr_elements))
    for tr_el in tr_elements:
        url = tr_el.find_element(By.TAG_NAME, 'td').find_element(
            By.TAG_NAME, 'a').get_attribute('href')
        print(url)
        url_write(url, page)
    # driver.quit()


def loop_page(driver):
    page = 1
    while len(driver.find_elements(By.CSS_SELECTOR, "td[class='midasi']")) > 0:
        get_urls(driver, page)
        print(len(driver.find_elements(
            By.XPATH, "//a[contains(text(), '次へ')]")))
        if len(driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")) > 0:
            next_button = driver.find_element(
                By.XPATH, "//a[contains(text(), '次へ')]")
            next_button.click()
            page += 1
        else:
            driver.close()
    driver.close()


def search_data(driver):
    department_elements = driver.find_elements(By.NAME, 'f.shinryoKmk')
    for d_el in department_elements:
        d_el.click()
    city_elements = driver.find_elements(By.NAME, 'f.skcss')
    for c_el in city_elements:
        c_el.click()
    submit_button = driver.find_element(By.NAME, 'kensaku_sub')
    submit_button.click()


def main():
    driver = start_driver()
    driver.maximize_window()
    driver.get(base_url)
    search_data(driver)
    loop_page(driver)
    # table_elements=driver.find_elements(By.CSS_SELECTOR, "table[class='comTblGyoumuCommon']")
    # total_page=table_elements[5].find_element(By.TAG_NAME,'tr').find_element(By.TAG_NAME,'td').text
    # total_page=int(total_page.split('全')[1].split('ページ中')[0])
    # get_urls(driver, total_page)
    time.sleep(10000)


if __name__ == '__main__':
    main()
