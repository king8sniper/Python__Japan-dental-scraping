import requests
import json
import pickle
import re

URL = "http://i-search.pref.ishikawa.jp/ajax/tableMake.php"
body = {"sr_mode": "13", "sr_opt_outmode": "1", "sr_area_base": "0", "vl_page": "1"}
headers={
    'content-type': 'application/json'
}

# response = requests.post(URL, headers = headers, data = json.dumps(body)).text
response = requests.post(URL, data = body).content


f = open("read.txt", "ab")
# f.write(response)
f.close()
f = open("read.txt", "r")

with open('read.txt', encoding='utf-8') as f:
    text_str = f.read()

company_id = []
pattern = re.compile(r'no:([^,]+)')

for id in re.finditer(pattern, text_str):
  no = int((id.group(1)).strip("'"))
  company_id.append(no)

print(company_id)


# for item in jsonData['data']:
#     clinic_id = item['no']
#     print(clinic_id)

# print(jsonData)