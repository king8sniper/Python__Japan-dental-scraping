from bs4 import BeautifulSoup
import requests

base_url='https://www.ibaraki-medinfo.jp/Search/Result/?hdnSearchKind=0&hdnAreaKind=0&hdnArea=&hdnBaseLat=&hdnBaseLng=&hdnKamoku=23%2C22%2C24%2C25&hdnNaiyou=&hdnSearchOrigin=&hdnDetails=&hdnOthers=&hdnOtherDetails%5B0%5D=&hdnOtherDetails%5B1%5D=&hdnOtherDetails%5B2%5D=&hdnOtherDetails%5B3%5D=&hdnOtherDetails%5B4%5D=&hdnOtherDetails%5B5%5D=&hdnOtherDetails%5B6%5D=&hdnOtherDetails%5B7%5D=&hdnOtherDetails%5B8%5D=&txtKeyword=&txtFreeword=&hdnKikanKubun=&chkTyoukaku=&chkShikaku=&chkKurumaisu=&chkKurumaisuWC=&chkParking=&chkPrescription=&Page='

f = open("urls.txt", "a")

def get_page(page):
   response = requests.get(base_url+page)
   return response

def get_list(html):
    soup = BeautifulSoup(html, 'lxml')
    _items = soup.find("table", {"class": "input_info"}).findAll("tr")
    return _items

for page in range(1, 69):
  # try:
    print(page)
    _page=get_page(str(page))
    if _page.status_code == 200:
      items=get_list(_page.text)
      for item in items[1:] : 
        id=item.find('a').get('onclick').split("ShowDetails('")[1].split("')")[0]
        f.write(str(page)+","+id+",\n")
f.close()
print('done')
  # except Exception as e:
  #     # handle the error here
  #     f.close()
  #     print(f"An error occurred: {str(e)}")
  #     break  # exit the loop if an error occurs

  # else:
  #     time.sleep(3000)
