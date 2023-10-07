from zenrows import ZenRowsClient
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium_recaptcha_solver import RecaptchaSolver

client = ZenRowsClient("c5ff3c28c9a920cdeca691553d642a65f5ca1490")
base_url = "https://www.biccamera.com/bc/item/"
server_url = "https://zzkk28.com/api/v1"
WAIT_SEC = 20


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


def postcode(jancode, bc_id):
    data = {
        'jan_code': jancode,
        'bc_id': bc_id
    }
    print(data)
    response = requests.post(server_url+'/jan_code', json=data)
    print(response.status_code)


def get_jancode(driver, solver, bc_id):
    # driver.find_element(By.TAG_NAME, 'body')
    # wait = WebDriverWait(driver, 10)
    # wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'bcs_single')))
    print(len(driver.find_elements(By.CLASS_NAME, 'h-captcha')))
    if len(driver.find_elements(By.CLASS_NAME, 'h-captcha')) > 0:
        print(driver.page_source)
        wait = WebDriverWait(driver, 30)
        wait.until(EC.visibility_of_element_located((By.ID, 'checkbox')))
        checkbox = driver.find_element(By.ID, 'checkbox')
        checkbox.click()
        hcaptcha_iframe = driver.find_element(
            By.XPATH, '//iframe[@title="Main content of the hCaptcha challenge"]')
        solver.click_recaptcha_v2(iframe=hcaptcha_iframe)
    content = driver.page_source
    print(len(content.split('bcs_single')))
    if len(content.split('bcs_single')) > 1:
        jancode = content.split("serGoodsStkNo : '")[1].split("'}")[0]
        postcode(jancode, bc_id)


def main():
    response = requests.get(server_url+'/products')
    json_data = response.json()
    print(response.status_code)
    if response.status_code == 200:
        driver = start_driver()
        driver.maximize_window()
        solver = RecaptchaSolver(driver=driver)
        for i in range(34377, len(json_data)):
            url = base_url+str(json_data[i]['bc_id'])
            driver.get(url)
            get_jancode(driver, solver, json_data[i]['bc_id'])
            # response = client.get(url)
            # if response.status_code == 200:
            #     jancode = get_jancode(response.text, json_data[i]['bc_id'])
    # driver.close()
    # time.sleep(len(json_data)*5)


if __name__ == '__main__':
    main()
