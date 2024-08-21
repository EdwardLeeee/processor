from flask import Flask, request, jsonify
import requests
import requests.exceptions
import sys
import json
import re
import hashlib
import secrets
from datetime import datetime, timedelta

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
class PermissionError(Exception):
    pass

# 用戶 API 金鑰的到期時間（例如24小時）
TOKEN_EXPIRATION_HOURS = 1
def generate_api_key(ip_address):
    # 用OS提供的密碼學安全偽隨機數生成器（CSPRNG) 生成 32 Byte 的隨機數字(32*8 bit = 64個16進位字符)
    # e.g. 00000000 01000100 11111111.... = 0x0044FF.....
    api_key = secrets.token_hex(32)

    #將生成的 API 金鑰和傳入的 IP 地址拼接成一個字符串，然後進行 SHA-256 哈希加密。
    #最後，使用 hexdigest() 將哈希結果轉換為 64 字符的十六進制字符串。
    hashed_key = hashlib.sha256((api_key + ip_address).encode()).hexdigest()
    expiration_date = datetime.now() + timedelta(seconds=TOKEN_EXPIRATION_HOURS)# 到期時間
    return hashed_key, expiration_date

# 讀取 IP白名單 JSON 檔案
with open('config/whitelist.json', 'r') as f:
    data = json.load(f)
whitelist_ips = data['ips']# 獲取 IP 白名單

API_TOKENS = {}# 允許的 API 金鑰列表和對應的到期日期
# 壓測用
API_TOKENS["202408testing"] = datetime.now() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
#
@app.route('/verify-whitelist', methods=['GET'])
def verify_and_generate_key():
    client_ip = request.remote_addr
    #print("IP:", client_ip)
    if client_ip in whitelist_ips:
        hashed_key, expiration_date = generate_api_key(client_ip)# 拿到token 和到期時間
        API_TOKENS[hashed_key] = expiration_date
        #print("API_TOKENS:", API_TOKENS)
        # 回傳API Key給client
        return jsonify({
            "collector-api-key": hashed_key,
            "expire-time": expiration_date.isoformat()
        }),200
    else:
        return jsonify({"mesage": "IP not in whitelist"}), 403

def validate_api_token(f):# f 是原函數
    def decorator(*args, **kwargs):#*args 和 **kwargs 允許裝飾器接收任意數量的位置參數和關鍵字參數
        api_key = request.headers.get('collector-api-key')
        expiration_date = API_TOKENS.get(api_key)# = API_TOKENS[api_key] or None
        if not api_key or not expiration_date:#
            return jsonify({"message": "Unauthorized access (Wrong key or collector restarted). Please delete old key and acquire new key."}), 401
        if datetime.now() > expiration_date:
            return jsonify({"message": "API key expired. Please delete old key and acquire new key."}), 401
        return f(*args, **kwargs)
    return decorator

# 藉由正則表達式切割raw data
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
@validate_api_token
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
        response = requests.post('http://172.20.10.3:5000/log', json=log_data)

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

    except PermissionError as e:
        print(f"Error: {e}")
        return jsonify({"message": str(e)}), 403

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({"message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050,threaded = True)
    # 201 : 成功
    # 200 : get key 成功
    # 502 : 連不上server(logger)
    # 400 : JSON 資料有缺失
    # 401 : key 過期了
    # 402 : log  level 格式非法
    # 403 : IP 不在白名單
    # 500 : 非上述異常
