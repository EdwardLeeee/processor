import subprocess
import os
import socket
import platform
import json
import requests
import yaml
import re
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 配置檔案路徑(全域變數)
config_file = '/home/edward/桌面/processor/config/config.cfg'
offsets_file = '/home/edward/桌面/processor/config/offsets.json'

# 讀取yaml格式之配置檔案
def load_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config

config = load_config(config_file)

# 保存偏移量
def save_offsets(offsets):
    with open(offsets_file, 'w') as f:
        # dump 是把資料結構轉成JSON
        json.dump(offsets, f, indent=4) # indent=4 是讓它可以一個key一行,比較好看

# 讀取偏移量
def load_offsets():
    if not os.path.exists(offsets_file):#指定路徑 該檔案是否存在
        return {}
    with open(offsets_file, 'r') as f:
        return json.load(f)

offsets = load_offsets()
print("offsets: ", offsets)

# 取得主機資訊
def get_host_info():
    subprocess.run(['chmod', '+x', 'get_host_info.sh']) # 設定腳本權限
    result = subprocess.run(['./get_host_info.sh'], capture_output=True, text=True) # 調用腳本並輸出host_name = None
    host_ip = None
    for line in result.stdout.splitlines(): # 解析输出结果
        if line.startswith("HOST_NAME="):
            host_name = line.split('=', 1)[1].strip() # 只切一次，取後面
        elif line.startswith("HOST_IP="):
            host_ip = line.split('=', 1)[1].strip()

    if not host_name or not host_ip:
        raise ValueError("HOST_NAME or HOST_IP not found in script output")
    return host_name , host_ip

host_name, ip_address = get_host_info()

# 檔案變更處理類
class LogHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config
        self.offsets = offsets

    def on_modified(self, event):
        if event.is_directory:
            return
        # print("New log data added.")
        self.process(event.src_path)

    def process(self, file_path):
        for log_config in self.config['logs']:
            if log_config['file_path'] == file_path:
                print("Now handling file:", file_path)
                self.handle_log(log_config)

    def handle_log(self, log_config):
        file_path = log_config['file_path']
        last_offset = self.offsets.get(file_path, 0)
        print("last_offset: ", last_offset)

        with open(file_path, 'r', encoding='big5', errors='ignore') as f:
            lines = f.readlines()
            print("lines length:", len(lines))

        new_lines = []  # 确保 new_lines 有默认值
        # 如果新行數大於上次記錄的偏移量，處理新增加的行
        if last_offset < len(lines):
            new_lines = lines[last_offset:]
            self.offsets[file_path] = len(lines)
            save_offsets(self.offsets)

        # 處理新增加的 log 行
        for line in new_lines:
            fields = log_config['fields']
            regex = {
                "log_time_regex": fields['log_time'],
                "level_regex": fields['level'],
                "message_regex": fields['content']
            }
            # 組合 Format A 的資料
            log_data = {
                "HOST_NAME": host_name,
                "HOST_IP": ip_address,
                "SYSTEM_TYPE": log_config['system_type'],
                "PROCESS_NAME": os.path.basename(log_config['file_path']).split('.')[0],
                "REGEX": regex,
                "RAW_LOG": line.strip(),
                "TIMESTAMP": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # 發送資料到 Collector
            self.send_to_collector(log_data)

    def send_to_collector(self, log_data):
        try:
            response = requests.post('http://localhost:5050/log', json=log_data)
            if response.status_code == 201:
                print(f"Success , {response.status_code} , messsage : {response.json().get('message','N/A')}" )
            else:
                print(f"Error , {response.status_code} , messsage : {response.json().get('message','N/A')}" )
        except requests.exceptions.RequestException as e:
            print('hello')
            print(f"Error sending log data to collector: {e}")

if __name__ == "__main__":
    config = load_config(config_file)
    event_handler = LogHandler(config)
    observer = Observer()

    # 為每個 log 文件監視變化
    for log_config in config['logs']:
        print("Content of the config: ")
        print("File Path:", log_config['file_path'])
        print("System Type:", log_config['system_type'])
        print("Regex:", log_config['fields'])
        print()
        observer.schedule(event_handler, path=os.path.dirname(log_config['file_path']), recursive=False)

    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
