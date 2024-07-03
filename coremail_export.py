import requests
import json
import csv
import random
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义全局变量用于存储总公司id和分公司id
total_company_ids = []
branch_company_ids = []

def getcompany(Director, branch):
    global companys, total_company_ids, branch_company_ids
    total_company_ids.append(Director['id'])  # 存储总公司的id
    branch_company_ids.append(branch['id'])  # 存储分公司的id
    companys[Director['id']+'/'+branch['id']] = Director['name'] + "*" + branch['name']
    if 'ou' in branch.keys():
        for branch1 in branch['ou']:
            getcompany(Director, branch1)

def fetch_data_for_company(company_id):
    listurl = f"{baseurl}/coremail/s/json?sid={cookiesid}&func=oab%3AlistEx"
    data = json.dumps({
        "dn": company_id,
        "returnAttrs": ["@location","@id", "@type", "gender", "true_name", "email", "mobile_number", "duty", "zipcode", ],
        "start": 0,
        "limit": 1000,
        "condition": {
            "field": "@type",
            "operator": "=",
            "operand": ["X", "U", "L"]
        }
    })

    try:
        response = requests.post(listurl, data=data, headers=headers).json()
        branchperson = response.get('var', [])
        return branchperson
    except Exception as e:
        logging.error(f"Error fetching data for company {company_id}: {e}")
        return []

def write_to_csv(company_id, writer):
    branchperson = fetch_data_for_company(company_id)
    Dname, Bname = companys[company_id].split("*")
    
    for person in branchperson:
        person['总公司'] = str(Dname)
        person['分公司'] = str(Bname)
        writer.writerow(person)
    
    logging.info(f"{companys[company_id]} 共有人员 {len(branchperson)} 个")
    time.sleep(0)  # 每次请求后进行sleep，防止IP被ban掉

def main():
    global companys, cookiesid, cookieCoremail, headers, baseurl
    
    baseurl = "" # 域名
    cookie = ""
    
    try:
        cookiesid = cookie.split("Coremail.sid=")[1].split(";")[0] # cookie或者url中去找到的
        cookieCoremail = cookie.split("Coremail=")[1].split(";")[0] # cookie中的Coremail字段
    except:
        logging.error("Cookie有问题?请检查")
        return
    
    logging.info(f"cookiesid: {cookiesid}, Coremail: {cookieCoremail}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0",
        "Accept": "text/x-json",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Content-Type": "text/x-json",
        "X-Requested-With": "XMLHttpRequest",
        "referrer": f"{baseurl}/coremail/XT5/index.jsp?sid={cookiesid}",
        "Cookie": f"face=auto; locale=zh_CN; Coremail={cookieCoremail};Coremail.sid={cookiesid}"
    }
    
    getDirectoriesurl = f"{baseurl}/coremail/s/json?sid={cookiesid}&func=oab%3AgetDirectories"
    
    body = "{\"attrIds\":[\"email\"]}"
    res = requests.post(getDirectoriesurl, data=body, headers=headers).json()['var']
    companys = {}
    for Director in res:  ## 多级子公司
        for branch in Director['ou']:
            getcompany(Director, branch)
    
    # 打印总公司id和分公司所有id
    logging.info(f"总公司id: {total_company_ids}")
    logging.info(f"分公司所有id: {branch_company_ids}")
    
    logging.info(f"共获取到子公司 {len(companys)} 个\n开始获取字段信息")
    
    # 生成一个随机的文件名
    filename = "".join(random.sample('zyxwvutsrqponmlkjihgfedcba', 5)) + ".csv"
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["总公司", "分公司", "@id", "@type", "gender", "true_name", "email", "mobile_number", "duty", "zipcode", "@location"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(write_to_csv, company_id, writer): company_id for company_id in companys}
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing companies"):
                future.result()  # 获取执行结果，处理异常
                
    logging.info(f"所有联系人信息已写入文件 {filename}")

if __name__ == "__main__":
    main()
