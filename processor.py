import configparser
import subprocess
import requests
from datetime import datetime
import time

url = 'http://localhost:5050/log'
#-----host name/ip-------------
subprocess.run(['chmod', '+x', 'get_host_info.sh']) # 設定腳本權限
result = subprocess.run(['./get_host_info.sh'], capture_output=True, text=True) # 調用腳本並輸出
for line in result.stdout.splitlines(): # 解析输出结果
    if line.startswith("HOST_NAME="):
        host_name = line.split('=', 1)[1].strip() # 只切一次，取後面
    elif line.startswith("HOST_IP="):
        host_ip = line.split('=', 1)[1].strip()
if not host_name or not host_ip:
    raise ValueError("HOST_NAME or HOST_IP not found in script output")

#----抓配置-----------------
config = configparser.ConfigParser() # 讀配置文件

config.read('/home/edward/桌面/processor/config/config.cfg')
num_sections = len(config.sections())
for i in range(1,num_sections+1):
    system_type = config.get(f'LOG{i}', 'SYSTEM_TYPE')
    process_name = config.get(f'LOG{i}', 'PROCESS_NAME')
    regex = config.get(f'LOG{i}', 'REGEX')
    # 抓路徑
    input_file_path = config.get(f'LOG{i}', 'file_path')

    # 讀寫big5編碼之log
    with open(input_file_path, 'r', encoding='big5', errors='replace') as input_file:
        lines = input_file.readlines()

    # 設置 Content-Type 頭為 application/json; charset=utf-8
    headers = {
    'Content-Type': 'application/json; charset=utf-8'
    }

    for line in lines:
        content = line.strip() # 去除行尾的空白字符

        log_time = datetime.now().strftime('%Y%m%d%H%M%S')
        log_data = {
            'HOST_NAME': host_name,
            'HOST_IP': host_ip,
            'SYSTEM_TYPE': system_type,
            'PROCESS_NAME': process_name,
            'REGEX': regex,
            'CONTENT': content,
            'LOG_TIME': log_time
        }

        response = requests.post(url, json=log_data, headers=headers)

        # 输出响应内容
        print(f"Status Code: {response.status_code} , Message : {response.json().get('message','N/A')}")
        #print(f"Status Code: {response.status_code} ")
        time.sleep(1)
