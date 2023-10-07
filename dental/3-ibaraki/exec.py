from bs4 import BeautifulSoup
import requests
import csv
import jaconv
import re
import json
import csv
import time
import datetime
from dateutil.parser import parse
from normalize_japanese_addresses import normalize
import numpy as np





base_url='https://www.ibaraki-medinfo.jp/details/'

f = open("urls.txt", "r")

data=['timestamp', 'storename', 'address_original', 'address_normalize[0]', 'address_normalize[1]', '最終更新日', 'url', 
      '開設者種別', '開設者名', '管理者名', '歯科一般領域一覧', '歯科口腔外科領域一覧', '小児歯科領域一覧', '矯正歯科領域一覧',
      '施設状況一覧', '対応可能ﾅ麻酔治療一覧', '在宅医療', '連携ﾉ有無', '歯科医師(総数|常勤|非常勤)', '歯科技工士(総数|常勤|非常勤)', 
      '歯科助手(総数|常勤|非常勤)', '歯科衛生士(総数|常勤|非常勤)', '前年度1日平均外来患者数', '緯度', '経度', 'page', '診療科']

fc=open('ibaraki.csv', 'a', newline='',encoding='utf-8')
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





def get_page(id, category):
  response = requests.get(base_url+category+'/sb/'+id)
  return response

def get_base_data(html):
  soup = BeautifulSoup(html, 'lxml')
  timeStamp = datetime.date.today()

  span_items = soup.find("h3", {"class": "kikanMidashi"}).findAll("span")
  baseData={
    'storename': span_items[0].text.replace('\u3000', ' '),
    'updated_at': span_items[1].text.split('更新日：')[1].split('\n')[0],
  }
  table_items=soup.findAll("table", {"class", "input_info"})
  baseData['address']=table_items[3].findAll('tr')[2].find('td').text.replace('\u3000', ' ')
  try:
     storeAddressNormalize = "".join(list(normalize(baseData['address']).values())[0:4])
     baseData['address_normalize_1'] = _split_buildingName(storeAddressNormalize)[0]
     baseData['address_normalize_2'] = _split_buildingName(storeAddressNormalize)[1]
  except:
     baseData['address_normalize_1']=baseData['address_normalize_2']="na"
  baseData['founder_type']=table_items[1].find('tr').find('td').text.replace('\u3000', ' ')
  baseData['founder_name']=table_items[1].findAll('tr')[2].find('td').text.replace('\u3000', ' ')
  baseData['admin_name']=table_items[2].findAll('tr')[1].find('td').text.replace('\u3000', ' ')

  try:
    department_trs = soup.find("table", {"id": "tblShinryouKamoku"}).find_all('tr')
    medical_department = "["
    for department_tr in department_trs:
      try:
        medical_department += (department_tr.find('td').text.replace('\u3000', ' ') + ", ")
      except:
        a = 0
    medical_department += "]"
  except:
    medical_department = "na"

  baseData['timestamp'] = timeStamp
  baseData['medical_department'] = medical_department
       
  return baseData

def get_amenity_data(html):
  soup = BeautifulSoup(html, 'lxml')
  true_elements=soup.findAll('td', string='有')
  
  if len(true_elements) > 0 :
    amenityData=[]
    for t_el in true_elements :
      parent_true=t_el.find_parent('tr')
      amenityData.append(parent_true.find('th').text.strip())
  else :
    amenityData='na'
  
  return amenityData

def get_actual_data(html):
  soup = BeautifulSoup(html, 'lxml')
  table_items=soup.findAll("table", {"class", "input_info"})
  dentist_element=table_items[0].find('div', string='歯科医師')
  actualData={}
  if not dentist_element is None:
    parent_dentist=dentist_element.find_parent('tr')
    den_total=parent_dentist.findAll('td')[1].find('div').text if parent_dentist.findAll('td')[1].find('div').text!='' else '-'
    den_full=parent_dentist.findAll('td')[2].find('div').text if parent_dentist.findAll('td')[2].find('div').text!='' else '-'
    den_part=parent_dentist.findAll('td')[3].find('div').text if parent_dentist.findAll('td')[3].find('div').text!='' else '-'
    actualData['dentist']=den_total+'|'+ den_full + '|' + den_part
  else:
    actualData['dentist']='na'

  hygienist_element=table_items[0].find('div', string='歯科衛生士')
  if not hygienist_element is None:
    parent_hygienist=hygienist_element.find_parent('tr')
    hyg_total=parent_hygienist.findAll('td')[1].find('div').text if parent_hygienist.findAll('td')[1].find('div').text!='' else '-'
    hyg_full=parent_hygienist.findAll('td')[2].find('div').text if parent_hygienist.findAll('td')[2].find('div').text!='' else '-'
    hyg_part=parent_hygienist.findAll('td')[3].find('div').text if parent_hygienist.findAll('td')[3].find('div').text!='' else '-'
    actualData['dental_hygienist']= hyg_total+'|'+ hyg_full + '|' + hyg_part
  else:
    actualData['dental_hygienist']='na'

  day_element=table_items[len(table_items)-1].find('div', string='前年度１日平均患者数')
  actualData['day_patients']='na'
  if not day_element is None:
    parent_day=day_element.find_parent('tr')
    actualData['day_patients']=parent_day.findAll('td')[1].find('div').text.split('人')[0] if parent_day.findAll('td')[1].find('div').text!='' else 'na'

  return actualData

def get_contents_data(html):
  soup = BeautifulSoup(html, 'lxml')
  contentsData={}

  general_div=soup.find("span", string="歯科領域").find_parent('div')
  general_element=general_div.find_next_sibling('table').findAll('tr')
  if len(general_element) > 1:
    general_dentistry=[]
    for g_el in general_element[1:]:
      general_dentistry.append(g_el.find('td').text)
  else :
    general_dentistry='na'
  contentsData['general_dentistry']=general_dentistry

  oral_div=soup.find("span", string="口腔外科領域").find_parent('div')
  oral_element=oral_div.find_next_sibling('table').findAll('tr')
  if len(oral_element) > 1:
    oral_surgery=[]
    for o_el in oral_element[1:]:
      oral_surgery.append(o_el.find('td').text)
  else :
    oral_surgery='na'
  contentsData['oral_surgery']=oral_surgery

  homecare_div=soup.find("span", string="対応することができる在宅医療（在宅医療）").find_parent('div')
  homecare_element=homecare_div.find_next_sibling('table').findAll('tr')
  if len(homecare_element) > 1:
    homecare=[]
    for h_el in homecare_element:
      homecare.append(h_el.find('td').text)
  else :
    homecare='na'      
  contentsData['homecare']=homecare

  collaboration_div=soup.find("span", string="対応することができる在宅医療（他施設との連携）").find_parent('div')
  collaboration_element=collaboration_div.find_next_sibling('table').findAll('tr')
  if len(collaboration_element) > 1:
    collaboration=[]
    for c_el in collaboration_element:
      collaboration.append(c_el.find('td').text)
  else :
    collaboration='na'   
  contentsData['collaboration']=collaboration

  return contentsData

index = 0
for line in f :
  page=line.split(',')[0]
  id=line.split(',')[1]
  data={}
  baseInfo=get_page(id, 'BaseInfo')
  if baseInfo.status_code == 200:
    baseData=get_base_data(baseInfo.text)

  amenityInfo=get_page(id, 'Amenity')
  if amenityInfo.status_code == 200:
    amenityData=get_amenity_data(amenityInfo.text)

  actualInfo=get_page(id, 'Actual')
  if actualInfo.status_code == 200:
    actualData=get_actual_data(actualInfo.text)

  contentsInfo=get_page(id, 'Contents')
  if contentsInfo.status_code == 200:
    contentsData=get_contents_data(contentsInfo.text)

  data=[
    baseData['timestamp'],
    baseData['storename'],
    baseData['address'],
    baseData['address_normalize_1'],
    baseData['address_normalize_2'],
    baseData['updated_at'],
    base_url+'BaseInfo'+'/sb/'+id,
    baseData['founder_type'],
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
  print(id, index)

fc.close()
