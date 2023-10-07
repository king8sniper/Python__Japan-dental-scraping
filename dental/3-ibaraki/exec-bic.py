# from bs4 import BeautifulSoup
import requests
import time
import json
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

server_url = "https://zzkk28.com/api/v1"
test_url = "http://127.0.0.1:8000/api/v1"
WAIT_SEC = 30
base_url = 'https://www.biccamera.com/bc/category/001/'

# f = open("urls.txt", "a")
urls = []

f = open("test.txt", "a")


def make_urls(selected_categories):
    for s_category in selected_categories:
        if s_category['makers'] != None:
            maker_string = ''
            s_makers = json.loads(s_category['makers'])
            for s_maker in s_makers:
                if s_maker['status'] == 1:
                    japanese_text = s_maker['value']
                    encoded_string = ''
                    for i in range(0, len(japanese_text)):
                        char = japanese_text[i]
                        if re.match(r"[^\x00-\x7F]+", char):
                            encoded_bytes = char.encode("shift-jis")
                            encoded_char = "".join(
                                [f"%{byte:02X}" for byte in encoded_bytes])
                            encoded_string += encoded_char
                        else:
                            encoded_string += char
                    maker_string += ('|' +
                                     encoded_string) if maker_string != '' else encoded_string
            # print(maker_string)
            url = base_url+s_category['category_id']+'/' + \
                s_category['bc_id']+'/?entr_nm='+maker_string+'&rowPerPage=100'
            # url_write(url)
            urls.append(url)


def start_driver():
    # Selenium用のウェブドライバーを初期化し、さまざまなオプションで安定した最適なパフォーマンスを得る。
    # Selenium用のChromeドライバーオプションを設定。
    options = webdriver.ChromeOptions()
    # クリーンなブラウジングセッションのためにブラウザ拡張を無効にする。
    # options.add_argument("--headless")
    options.add_argument('--disable-extensions')
    # ブラウザを最大化したウィンドウで開始。参考: https://stackoverflow.com/a/26283818/1689770
    options.add_argument('--start-maximized')
    # 互換性向上のためにサンドボックスを無効にする。参考: https://stackoverflow.com/a/50725918/1689770
    options.add_argument('--no-sandbox')
    # より安定した動作のためにこのオプションを追加。参考: https://stackoverflow.com/a/50725918/1689770
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--ignore-certificate-errors")

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


def get_page_data(url, driver, category_id):
    print('detail_page', url)
    driver.get(url)
    items = driver.find_element(
        By.CLASS_NAME, 'bcs_listItem').find_elements(By.CLASS_NAME, 'prod_box')
    products = []
    print(len(items))
    for item in items:
        product = {}
        product["name"] = item.find_element(
            By.CLASS_NAME, 'bcs_title').text.replace('\u3000', ' ')
        product["bc_id"] = int(item.get_attribute('data-item-id'))
        product["category_id"] = category_id
        product["price"] = {}
        product["price"]["value"] = int(item.find_element(By.CLASS_NAME, 'bcs_price').text.split('円')[0].replace(',', '')) if len(item.find_elements(By.CLASS_NAME, 'bcs_price')) > 0 else int(
            item.find_element(By.CLASS_NAME, 'bcs_price_soldout').text.split('円')[0].replace(',', '')) if len(item.find_elements(By.CLASS_NAME, 'bcs_price_soldout')) > 0 else None
        product["price"]["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        product["image_link"] = item.find_element(
            By.CSS_SELECTOR, "p[class='bcs_image']").get_attribute('innerHTML').strip()
        products.append(product)
        f.write(json.dumps(products))
    response = requests.post(
        test_url+'/test', json=json.dumps(products), headers={"Content-Type": "application/json"})
    print(response.status_code, response.reason)


def loop_url(driver, url, category_id):
    driver.get(url)
    print('loop', url)
    if len(driver.find_elements(By.CLASS_NAME, 'bcs_pager')) > 0:
        pagination = driver.find_element(By.CLASS_NAME, 'bcs_pager')
        page_num = int(pagination.find_elements(By.TAG_NAME, 'li')[-2].text)
        print('total_page', page_num)
        for i in range(1, page_num+1):
            page_url = url+'&p='+str(i)
            get_page_data(page_url, driver, category_id)


def main():
    response = requests.get(test_url+'/categories')
    if response.status_code == 200:
        # f.truncate(0)
        selected_categories = response.json()
        max_index = len(selected_categories)
        make_urls(selected_categories)
        print(len(urls))
        if len(urls) > 0:
            driver = start_driver()
            driver.maximize_window()
            for i in range(0, len(urls)):
                loop_url(driver, urls[i], selected_categories[i]['id'])


if __name__ == '__main__':
    main()
