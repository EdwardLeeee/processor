from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime

# 功能：
# 接收 Client 傳來的主機資訊及切割規則。
# 監聽 Client 傳來的原始 log 資料，依據規則切割取得所需欄位。
# 將處理後的 log 資料結合主機資訊和 SYSTEM_TYPE，然後發送至最終的儲存端點。

app = Flask(__name__)

# 自定義錯誤類別
class InvalidLogLevelError(Exception):
    pass

class MissingDataError(Exception):
    pass

def parse_log(raw_log, split_rule):
    log_time_match = re.search(split_rule['log_time_regex'], raw_log) if isinstance(split_rule['log_time_regex'], str) else None
    level_match = re.search(split_rule['level_regex'], raw_log) if isinstance(split_rule['level_regex'], str) else None
    message_match = re.search(split_rule['message_regex'], raw_log) if isinstance(split_rule['message_regex'], str) else None

    log_time = log_time_match.group(1) if log_time_match else ""
    message = message_match.group(1) if message_match else ""
    level = level_match.group(1).upper() if level_match else ""

    # Apply level_rule conversion (if provided)
    if split_rule.get('level_rule'):
      level = split_rule['level_rule'].get(level, level)

    return log_time, level, message
# 支援的日誌級別
SUPPORTED_LEVELS = ['INFO', 'WARN', 'ERRO', 'DEBUG', '']
def check_error(level):
    # 檢查並處理 log level
    if level not in SUPPORTED_LEVELS:
        raise InvalidLogLevelError(f"Invalid log level: {level}")

@app.route('/log', methods=['POST'])
def process_raw_log():
    try:
        raw_log = request.json.get('RAW_LOG')
        split_rule = request.json.get('REGEX')
        host_name = request.json.get("HOST_NAME")
        host_ip = request.json.get("HOST_IP")
        system_type = request.json.get("SYSTEM_TYPE")
        process_name = request.json.get("PROCESS_NAME")

        # 檢查必需的資料
        missing_fields = [field for field, value in {"raw_log": raw_log, "split_rule": split_rule, "host_name": host_name, "host_ip": host_ip, "system_type": system_type, "process_name": process_name}.items() if not value]

        if missing_fields:
            raise MissingDataError(f"Client missing required fields in the request: {', '.join(missing_fields)}")

        log_time, level, message = parse_log(raw_log, split_rule)

        check_error(level)
        # 組合最終的 log 資料
        log_data = {
            "HOST_NAME": host_name,
            "HOST_IP": host_ip,
            "SYSTEM_TYPE": system_type,
            "PROCESS_NAME": process_name,
            "LEVEL": level,
            "CONTENT": message,
            "LOG_TIME": f"{datetime.now().strftime('%Y-%m-%d')} {log_time}"
        }
        # 傳送 log 資料至最終儲存端點
        response = requests.post('http://localhost:5000/log', json=log_data)
        if response.status_code == 201:
            return jsonify({"message": "Log processed", "status": "success"}), 201
        else:
            print( response.json().get('message','N/A'))
            return jsonify({"message": response.json().get('message','N/A'), "status": "Error"}), response.status_code

    except requests.exceptions.ConnectionError:
        print("Failed to connect to the logger server. Please check if the server is running.")
        return jsonify({"message": "Failed to connect to the logger server"}), 502
    except MissingDataError as e:
        print(f"Error: {e}")
        return jsonify({"message": str(e)}), 400

    except InvalidLogLevelError as e:
        print(f"Error: {e}")
        return jsonify({"message": str(e)}), 402

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050,threaded = True)
    # 201 : 成功
    # 502 : 連不上server(logger)
    # 400 : JSON 資料有缺失
    # 500 : 非上述異常
    # 402 : log  level 格式非法
