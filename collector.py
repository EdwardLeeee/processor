from flask import Flask, request, jsonify
import json
from datetime import datetime
import re
import requests


app = Flask(__name__)

url = 'http://localhost:5000/log'

# 定義日誌文件路徑
log_file_path = 'received_logs.json'

# 紀錄日誌
def log_to_file(log_entry):
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

@app.route('/log', methods=['POST'])
def receive_log():
    try:
        log_entry = request.get_json()
        '''
        # 檢查接收到的 JSON 資料是否包含所有必要的鍵
        required_keys = ['HOST_NAME', 'HOST_IP', 'SYSTEM_TYPE', 'PROCESS_NAME', 'REGEX', 'CONTENT', 'LOG_TIME']
        if not all(key in log_entry for key in required_keys):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # 驗證 LOG_TIME 格式
        try:
            datetime.strptime(log_entry['LOG_TIME'], '%Y%m%d%H%M%S')
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid LOG_TIME format"}), 400
        '''
         # 提取 REGEX 並進行處理
        regex_pattern = log_entry['REGEX']
        try:
            pattern = re.compile(regex_pattern)  # 嘗試編譯正則表達式
        except re.error:
            return jsonify({"status": "error", "message": "Invalid REGEX pattern"}), 400

        # 使用正則表達式匹配 CONTENT
        content = log_entry['CONTENT']
        match = pattern.search(content)

        if match:
            # 提取 log_time、level 和 message（假設正則表達式有捕獲到 group）
            log_time = match.group('time')
            level = match.group('level')
            content = match.group('message')

            # 確保所有群組都被匹配
            if not (log_time and level and content):
                return jsonify({"status": "error", "message": "wrong content"}), 401

            # 將提取的內容添加到日誌條目中
            log_entry['LOG_TIME'] = log_time
            log_entry['LEVEL'] = level
            log_entry['CONTENT'] = content
        else:
            return jsonify({"status": "error", "message": "wrong regex"}), 401

        # 在记录日志之前删除 REGEX 键
        del log_entry['REGEX']

        # 紀錄日誌
        log_to_file(log_entry)

        response = requests.post(url, json=log_entry)
        if response.status_code == 201:
            print('success')
        else:
            message = response.json().get('message')
            print(f" Error: {message}")
            return jsonify({"status": "error", "message":message}), response.status_code

        return jsonify({"status": "success"}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
    # 201 : 成功
    # 401 : 錯誤regex
    # 400 : JSON 資料有缺失
    # 500 : 非上述異常
