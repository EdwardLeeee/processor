import sys
import subprocess
import os
import json
import requests
import yaml
import platform
from datetime import datetime , date
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ServerConnectionError(Exception):
    """自定義異常類型，用於處理伺服器連接錯誤"""
    pass

class ConfigLoader:
    def __init__(self, config_path, offsets_path):
        self.config_path = config_path
        self.offsets_path = offsets_path

    def load_config(self):
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)  # 讀取yaml格式的config,做成dictionary

    def save_offsets(self, offsets):
        with open(self.offsets_path, 'w') as f:  # w 是覆寫
            json.dump(offsets, f, indent=4)  # dump 是把資料用JSON存起來, indent是讓一個key:value就一行

    def load_offsets(self):
        if not os.path.exists(self.offsets_path):
            return {}
        with open(self.offsets_path, 'r') as f:
            return json.load(f)  # 把json做成dictionary

class APIManager:
    def __init__(self, collector_url):
        self.collector_url = f"{collector_url}/verify-whitelist"

    def load_api_token(self):
        print("Loading API token...")
        api_key_data = self.get_api_token()
        return api_key_data

    def get_api_token(self):
        response = requests.get(self.collector_url)
        #print("Response:", response.json())
        if response.status_code == 200:
            return response.json()
        else:
            print("Error:", response.json().get("mesage","N/A"))
            sys.exit(1)
            return None

class HostInfo:
    @staticmethod
    def get_host_info():
        system_type = platform.system()  # 判斷系統類型
        if system_type == "Windows":
            # Windows 系統的處理方式
            name = platform.uname()
            host_name = name.node
            host_ip = socket.gethostbyname(socket.gethostname())
        elif system_type == "Linux":
            # Linux 系統的處理方式
            subprocess.run(['chmod', '+x', 'get_host_info.sh'])
            result = subprocess.run(['./get_host_info.sh'], capture_output=True, text=True)
            host_name = None
            host_ip = None
            for line in result.stdout.splitlines():
                if line.startswith("HOST_NAME="):
                    host_name = line.split('=', 1)[1].strip()
                elif line.startswith("HOST_IP="):
                    host_ip = line.split('=', 1)[1].strip()
            if not host_name or not host_ip:
                raise ValueError("HOST_NAME or HOST_IP not found in script output")
        else:
            raise ValueError(f"Unsupported system type: {system_type}")

        return host_name, host_ip

class LogHandler(FileSystemEventHandler):  # 繼承FileSystemEventHandler
    def __init__(self, config, host_info, offsets, save_offsets_func, collector_url,api_key_data):
        self.config = config  # dictionary
        self.host_info = host_info
        self.offsets = offsets  # dictionary
        self.save_offsets = save_offsets_func  # 一個function
        self.collector_url = collector_url  # 新增collector_url變數
        self.api_key_data = api_key_data
        # 初始化,更新一遍所有log狀態
        for log_config in self.config['logs']:
            self.process(log_config['file_path'])

    def on_modified(self, event):  # event 是繼承來的
        if event.is_directory:  # 涉及目錄 否則就是涉及檔案
            return
        self.process(event.src_path)  # event.src_path是改變的file/directory的路徑

    def process(self, file_path):
        for log_config in self.config['logs']:
            if log_config['file_path'] == file_path:
                self.handle_log(log_config)

    def handle_log(self, log_config):
        file_path = log_config['file_path']  # 要處理的檔案的絕對路徑

        # 用了 Python 字典的 get 方法來獲取key對應的值，如果該鍵不存在，則返回預設值 0。
        last_offset = self.offsets.get(file_path, 0)
        with open(file_path, 'r', encoding='big5', errors='ignore') as f:
            lines = f.readlines()

        if last_offset < len(lines):  # 代表有新增log
            for i in range(last_offset , len(lines)):
                line = lines[i].strip()# .strip()是去除首尾空白（含tab, \n）
                log_data = self.format_log_data(log_config , line)
                self.send_to_collector(log_data)

                # 更新 offset，將其保存到文件中
                self.offsets[file_path] = i + 1
                self.save_offsets(self.offsets)

    def format_log_data(self, log_config, line):
        fields = log_config['fields']
        level_rule = log_config['level_rule']
        regex = {
            "log_time_regex": fields['log_time'],
            "level_regex": fields['level'],
            "message_regex": fields['content'],
            "level_rule": level_rule
        }
        return {
            "HOST_NAME": self.host_info[0],
            "HOST_IP": self.host_info[1],
            "SYSTEM_TYPE": log_config['system_type'],
            "PROCESS_NAME": os.path.basename(log_config['file_path']).split('.')[0],
            "REGEX": regex,
            "RAW_LOG": line
            #"TIMESTAMP": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def send_to_collector(self, log_data):
        try:
            headers={"collector-api-key": self.api_key_data['collector-api-key']}
            response = requests.post(f'{self.collector_url}/log', json=log_data , headers = headers)
            if response.status_code == 401:# 如果401，重新请求新的API Key
                print(f"API key error: {response.status_code}, {response.json().get('message','N/A')}")
                api_manager = APIManager(self.collector_url)
                self.api_key_data = api_manager.load_api_token()

                if self.api_key_data:
                    headers={"collector-api-key": self.api_key_data['collector-api-key']}
                    response = requests.post(f'{self.collector_url}/log', json=log_data,headers=headers)
                else:
                    print("Failed to load API token.")
                    sys.exit(1)  # 退出程序以防止继续运行没有API key

            elif response.status_code == 201:
                print(f"Log sent successfully: {response.status_code}")
            elif response.status_code == 400:
                print(f"Log error (Data missing): {response.status_code}, {response.json().get('message','N/A')}")
                print('Please check sent data and config of log. If a column does not exist, send an empty string.')
                sys.exit(1)
            elif response.status_code == 402:
                print(f"Log error (Format issue): {response.status_code}. {response.json().get('message','N/A')}")
                print('Please check the config of log.')
                sys.exit(1)
            elif response.status_code == 403:
                print(f"Permission error: {response.status_code}. {response.json().get('message','N/A')}")
                sys.exit(1)
            elif response.status_code == 500:
                print(f"Error: {response.status_code}. {response.json().get('message','N/A')}")
                sys.exit(1)
            elif response.status_code == 502:
                print(f"Server connection error: {response.status_code}. Please restart the logger.")
                sys.exit(1)
            else:
                print(f"Unexpected error: {response.status_code}, {response.json().get('message','N/A')}")
                sys.exit(1)

        except requests.exceptions.ConnectionError :# collector沒開
            print("Failed to connect to the collector server. Please check if the server is running.")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"Error sending log data to collector: {e}")
            sys.exit(1)  # 中止程式，傳回碼 1 表示異常退出

def main():
    config_file = '/home/oraclelee/Desktop/collector/config/config.cfg'
    offsets_file =f'/home/oraclelee/Desktop/collector/config/offsets{date.today()}.json'
    collector_url = 'http://localhost:5050'  # 將URL變成參數

    config_loader = ConfigLoader(config_file, offsets_file)

    config = config_loader.load_config()  # dictionary
    offsets = config_loader.load_offsets()  # dictionary
    save_offsets_func = config_loader.save_offsets  # save_offsets 就等於是ConfigLoader的save_offsets函式
    host_info = HostInfo.get_host_info()# [ host_name , host_ip]

    api_manager = APIManager( collector_url)
    api_token_data = api_manager.load_api_token()

    # 設好監視處理程序
    event_handler = LogHandler(config, host_info, offsets, save_offsets_func, collector_url,api_token_data)
    observer = Observer()
    # 為每個檔案設立監視器
    for log_config in config['logs']:
        observer.schedule(event_handler, path=os.path.dirname(log_config['file_path']), recursive=False)

    observer.start()
    # 中斷條件
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()

    observer.join()  # 停止後釋放資源

if __name__ == "__main__":
    main()
