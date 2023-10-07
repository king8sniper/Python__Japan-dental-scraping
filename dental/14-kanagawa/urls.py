# from bs4 import BeautifulSoup
import requests
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

base_url='http://www.iryo-kensaku.jp/kanagawa/kensaku/SimpleSearch.aspx?sy=m'
WAIT_SEC=20

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

def url_write(url, page):
  f.write(str(page)+","+url+",\n")

def get_urls(driver, page):
  for order in range(1, 51) :
    table_element=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_grvShisetsuIchiran')
    tr_elements=table_element.find_element(By.TAG_NAME, 'tbody').find_elements(By.XPATH, './tr')
    try:
      link=tr_elements[order].find_element(By.TAG_NAME, 'td').find_element(By.TAG_NAME, 'a')
      link.click()
      url=driver.current_url
      print(url)
      url_write(url, page)
      driver.back()
    except:
      print('error')

def loop_page(driver):
    for page in range(1, 96):
      get_urls(driver, page)
     
      table_element=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_grvShisetsuIchiran')
      if page % 10 != 0:
        next_page=table_element.find_element(By.XPATH, f"//a[text()='{page+1}']")
        next_page.click()
      else :
        last_page=table_element.find_element(By.XPATH, "//a[text()='最終ページへ']")
        parent_element = last_page.find_element(By.XPATH, "..")
        previous_sibling = parent_element.find_element(By.XPATH, "preceding-sibling::*[1]")
        next_ten=previous_sibling.find_element(By.TAG_NAME, 'a')
        next_ten.click()
    print('done')
    driver.close()


def search_data(driver):
    search1=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_SinryoList1_CheckBoxList1_25')
    search1.click()
    search2=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_SinryoList1_CheckBoxList1_26')
    search2.click()
    search3=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_SinryoList1_CheckBoxList1_27')
    search3.click()
    search4=driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_SinryoList1_CheckBoxList1_28')
    search4.click()
    submit_button = driver.find_element(By.ID, 'ctl00_ContentPlaceHolderContents_Button1')
    submit_button.click()

def select_50(driver):
   dropdown=driver.find_element(By.NAME, 'ctl00$ContentPlaceHolderContents$drpPageSize')
   select=Select(dropdown)
   select.select_by_value('50')

def main():
  driver=start_driver()
  driver.maximize_window()
  driver.get(base_url)
  search_data(driver)
  select_50(driver)
  loop_page(driver)
  time.sleep(5000) 

if __name__ == '__main__':
  main()