from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# 定義日誌文件路徑
log_file_path = 'received_logs.json'

# 紀錄日誌
def log_to_file(log_entry):
    with open(log_file_path, 'a',encoding='utf-8') as log_file:
        log_file.write(json.dumps(log_entry, ensure_ascii=False)+"\n")

@app.route('/log', methods=['POST'])
def receive_log():
    log_entry = request.get_json()

    # 將日誌紀錄到文件
    log_to_file(log_entry)

    return jsonify({"status": "success"}), 201

if __name__ == '__main__':
    app.run(debug=True ,host='0.0.0.0', port=5050)

