import os
import time
import hashlib
import subprocess
import json
import requests
import yaml
from datetime import datetime

class ConfigLoader:
    def __init__(self, config_path, offsets_path):
        self.config_path = config_path
        self.offsets_path = offsets_path

    def save_offsets(self, offsets):
        with open(self.offsets_path, 'w') as f:
            json.dump(offsets, f, indent=4)

    def load_config(self):
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def load_offsets(self):
        if not os.path.exists(self.offsets_path):
            return {}
        with open(self.offsets_path, 'r') as f:
            return json.load(f)

class HostInfo:
    @staticmethod
    def get_host_info():
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
        return host_name, host_ip

class LogHandler:
    def __init__(self, config, host_info, offsets, save_offsets_func):
        self.config = config
        self.host_info = host_info
        self.offsets = offsets
        self.save_offsets = save_offsets_func
        self.file_hashes = {}

    def monitor_logs(self):
        while True:
            for log_config in self.config['logs']:
                self.process(log_config['file_path'])
            time.sleep(1)

    def process(self, file_path):
        if os.path.exists(file_path):
            current_hash = self.get_file_hash(file_path)
            if file_path not in self.file_hashes or self.file_hashes[file_path] != current_hash:
                self.file_hashes[file_path] = current_hash
                self.handle_log(file_path)

    def get_file_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def handle_log(self, file_path):
        for log_config in self.config['logs']:
            if log_config['file_path'] == file_path:
                last_offset = self.offsets.get(file_path, 0)
                with open(file_path, 'r', encoding='big5', errors='ignore') as f:
                    lines = f.readlines()
                new_lines = []
                if last_offset < len(lines):
                    new_lines = lines[last_offset:]
                    self.offsets[file_path] = len(lines)
                    self.save_offsets(self.offsets)
                for line in new_lines:
                    log_data = self.format_log_data(log_config, line.strip())
                    self.send_to_collector(log_data)

    def format_log_data(self, log_config, line):
        fields = log_config['fields']
        regex = {
            "log_time_regex": fields['log_time'],
            "level_regex": fields['level'],
            "message_regex": fields['content']
        }
        return {
            "HOST_NAME": self.host_info[0],
            "HOST_IP": self.host_info[1],
            "SYSTEM_TYPE": log_config['system_type'],
            "PROCESS_NAME": os.path.basename(log_config['file_path']).split('.')[0],
            "REGEX": regex,
            "RAW_LOG": line,
            "TIMESTAMP": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def send_to_collector(self, log_data):
        try:
            response = requests.post('http://localhost:5050/log', json=log_data)
            if response.status_code == 201:
                print(f"Success, {response.status_code}, message: {response.json().get('message','N/A')}")
            else:
                print(f"Error, {response.status_code}, message: {response.json().get('message','N/A')}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending log data to collector: {e}")

def main():
    config_file = '/home/edward/桌面/processor/config/config.cfg'
    offsets_file = '/home/edward/桌面/processor/config/offsets.json'

    config_loader = ConfigLoader(config_file, offsets_file)
    config = config_loader.load_config()
    offsets = config_loader.load_offsets()
    save_offsets_func = config_loader.save_offsets
    host_info = HostInfo.get_host_info()

    log_handler = LogHandler(config, host_info, offsets, save_offsets_func)
    log_handler.monitor_logs()

if __name__ == "__main__":
    main()

