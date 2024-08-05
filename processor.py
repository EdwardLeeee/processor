import configparser
import subprocess
import requests
from datetime import datetime
#-----host name/ip-----
subprocess.run(['chmod', '+x', 'get_host_info.sh']) # 設定腳本權限
result = subprocess.run(['./get_host_info.sh'], capture_output=True, text=True) # 調用腳本並輸出

host_name = None
host_ip = None
for line in result.stdout.splitlines(): # 解析输出结果
    if line.startswith("HOST_NAME="):
        host_name = line.split('=', 1)[1].strip() # 只切一次，取後面
    elif line.startswith("HOST_IP="):
        host_ip = line.split('=', 1)[1].strip()

if not host_name or not host_ip:
    raise ValueError("HOST_NAME or HOST_IP not found in script output")

#----抓配置------
config = configparser.ConfigParser() # 讀配置文件
config.read('/home/oraclelee/Desktop/collector/config/test2.conf')

system_type = config.get('JSON', 'SYSTEM_TYPE')
process_name = config.get('JSON', 'PROCESS_NAME')
regex = config.get('JSON', 'REGEX') # 更正：获取 REGEX 配置

# 抓路徑
input_file_path = config.get('input', 'file_path')

# 打开原始 Big5 编码的日誌檔案並逐行讀取其內容
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

    response = requests.post('http://localhost:5050/log', json=log_data, headers=headers)

    # 输出响应内容
    print(f"Status Code: {response.status_code}")

