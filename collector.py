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
# 正則表達式錯誤處理
class LogParseError(Exception):
    pass

class InvalidLogLevelError(Exception):
    pass

class MissingDataError(Exception):
    pass

# 支援的日誌級別
SUPPORTED_LEVELS = ['INFO', 'WARN', 'ERRO', 'DEBUG']

def parse_log(raw_log, split_rule):
    log_time_match = re.search(split_rule['log_time_regex'], raw_log)
    level_match = re.search(split_rule['level_regex'], raw_log)
    message_match = re.search(split_rule['message_regex'], raw_log)

    log_time = log_time_match.group(1)
    level = level_match.group(1).upper()
    message = message_match.group(1)

    if not all ([log_time_match, level_match, message_match]):
        error_message = f"Failed to parse log:"
        if not log_time_match:
            error_message += " log time not found"
        if not level_match:
            error_message += " level not found"
        if not message_match:
            error_message += " message not found"
        raise LogParseError(error_message)

    return log_time, level, message

def check_error(level):
    # 處理level
    if level in ('ERR', 'ERROR'):
        level = 'ERRO'
    elif level in ('NORMAL'):
        level = 'INFO'
    # 檢查並處理 log level
    if level not in SUPPORTED_LEVELS:
        raise InvalidLogLevelError(f"Invalid log level: {level}")
'''
WHITE_LISTED_IPS = ["192.168.1.1", "127.0.0.1"]# 設定 IP 白名單
def check_ip_whitelist():
    client_ip = request.remote_addr
    if client_ip not in WHITE_LISTED_IPS:
        return False
    return True

@app.before_request
def before_request():
    if not check_ip_whitelist():
        return jsonify({"error": "Forbidden", "message": "Your IP is not allowed to access this resource."}), 403
'''
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
        if not all([raw_log, split_rule, host_name, host_ip, system_type, process_name]):
            raise MissingDataError("Missing required fields in the request")

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
            return jsonify({"message": response.json().get('message','N/A'), "status": "Error"}), response.status_code


    except MissingDataError as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 400

    except InvalidLogLevelError as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 402

    except LogParseError as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
    # 201 : 成功
    # 401 : 錯誤regex
    # 400 : JSON 資料有缺失
    # 500 : 非上述異常
    # 缺失資料檢查：

    # 在處理 raw_log、split_rule、host_name、host_ip、system_type 和 process_name 等必需字段時，若有任何一個缺失，則引發 MissingDataError 並回傳 HTTP 狀態碼 400。
    # 無效的日誌級別：

    # 若解析出的 level 不在支持的日誌級別清單 (SUPPORTED_LEVELS) 中，則引發 InvalidLogLevelError 並回傳 HTTP 狀態碼 402。
    # 日誌解析錯誤：

    # 若解析 log 時出現問題（例如正則表達式匹配失敗），引發 LogParseError 並回傳 HTTP 狀態碼 500。
    # 一般錯誤處理：

    # 捕捉其他未預期的錯誤並回傳 HTTP 狀態碼 500。

