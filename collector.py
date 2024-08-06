from flask import Flask, request, jsonify
import json
from datetime import datetime
import re

app = Flask(__name__)

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

        # 檢查接收到的 JSON 資料是否包含所有必要的鍵
        required_keys = ['HOST_NAME', 'HOST_IP', 'SYSTEM_TYPE', 'PROCESS_NAME', 'REGEX', 'CONTENT', 'LOG_TIME']
        if not all(key in log_entry for key in required_keys):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # 驗證 LOG_TIME 格式
        try:
            datetime.strptime(log_entry['LOG_TIME'], '%Y%m%d%H%M%S')
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid LOG_TIME format"}), 400

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
            # 提取 log_time、level 和 message（假設正則表達式有捕獲組）
            log_time = match.group(1) if match.lastindex >= 1 else 'N/A'
            level = match.group(2) if match.lastindex >= 2 else 'N/A'
            content = match.group(3) if match.lastindex >= 3 else 'N/A'

            # 將提取的內容添加到日誌條目中
            log_entry['LOG_TIME'] = extracted_log_time
            log_entry['LEVEL'] = extracted_level
            log_entry['CONTENT'] = content
        else:
            return jsonify({"status": "error", "message": "wrong regex"}), 401

        # 紀錄日誌
        log_to_file(log_entry)

        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)

