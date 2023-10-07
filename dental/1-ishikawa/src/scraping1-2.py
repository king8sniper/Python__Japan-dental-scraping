import requests
import json
import re
import time

# Global Variables
WAIT_SEC = 5




# Functions

def get_clinic_ids():
    getIds_post_url = "http://i-search.pref.ishikawa.jp/ajax/tableMake.php"
    simple_file = open("simple.txt", "ab")

    for x in range(1, 3):
        page_num = x
        body = {"sr_mode": "13", "sr_opt_outmode": "1", "sr_area_base": "0", "vl_page": page_num}
        response = requests.post(getIds_post_url, data = body, timeout = WAIT_SEC).content
        simple_file.write(response)
        time.sleep(WAIT_SEC)
    simple_file.close()

    clinic_ids = []
    pattern = re.compile(r'no:([^,]+)')
    with open('simple.txt', encoding='utf-8') as f:
        text_str = f.read()

    for id in re.finditer(pattern, text_str):
        no = int((id.group(1)).strip("'"))
        clinic_ids.append(no)

    # print(clinic_ids)
    return clinic_ids



clinic_ids = get_clinic_ids()

# print(type(clinic_ids))
# ids_file = open("ids.txt", "ab")
# for clinic_id in clinic_ids:
# 	ids_file.write(clinic_id+"\n")
# ids_file.close()
# http://i-search.pref.ishikawa.jp/detail.php?rd_no=506


# detailhtml_file = open("detailhtml.html", "ab")
# detailhtml_file.write(response)
# detailhtml_file.close()


# clinic_ids = [506, 559]    [139:] + clinic_ids[:139]
