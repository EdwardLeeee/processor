#!/bin/bash
# 确保使用 UTF-8 编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
# 檢查參數
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <log_file_path>"
    exit 1
fi

# 定義日誌文件路徑和 URL
log_file_path="$1"
url="http://localhost:5050/log"

# 獲取主機名稱和 IP 地址
host_name=$(hostname)
host_ip=$(hostname -I | awk '{print $1}')

# 讀取 UTF-8 編碼的日誌文件並發送每一行作為 POST 請求
while IFS= read -r line; do
    # 創建 JSON 格式的數據
    json_data=$(jq -n --arg hn "$host_name" --arg ip "$host_ip" --arg content "$line" \
        '{"HOST_NAME": $hn, "HOST_IP": $ip, "CONTENT": $content}')

    # 使用 curl 發送 POST 請求
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d "$json_data")

    # 檢查響應狀態碼
    if [ "$response" -eq 201 ] || [ "$response" -eq 200 ]; then
        echo "Log entry sent successfully"
    else
        echo "Failed to send log entry: $response, Content: $line"
    fi

done < "$log_file_path"
