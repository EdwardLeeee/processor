# 使用官方 Python 3.9 Alpine 作為基礎映像，這是一個較小的映像
FROM python:3.9-alpine

# 設定工作目錄
WORKDIR /app

# 複製應用程式代碼到容器內
COPY . .

# 安裝 Flask 和 requests 依賴
# 這裡合併了安裝和清理步驟，以減少層數
RUN pip install --no-cache-dir Flask==3.0.3 requests==2.25.1 && \
    # 清理不必要的檔案和緩存
    rm -rf /root/.cache

# 設定環境變數
ENV FLASK_APP=collector.py \
    FLASK_RUN_HOST=0.0.0.0

# 開放端口
EXPOSE 5050

# 設定容器啟動時執行的命令
CMD ["flask", "run", "--host=0.0.0.0", "--port=5050"]
