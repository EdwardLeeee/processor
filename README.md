# Poccessor
## 簡介

`proccessor.py`是一個負責傳送客戶端各種 process 所產生的不同格式之 log 給資料庫的程式。
它會去讀資料夾 `config` 中的設定檔，
並依照給定設定傳送 JSON 格式資料給負責切割 Raw Data 的 microservice 。

`collector.py`是一個 microservice 。
負責去接收客戶打過來的初始資料，並依照客戶端提供 Regex 格式切割傳近來的 Raw Data ，
成功切割後 post 給負責將 data 寫入 data base 的 microservice。

本程式會使用 watchdog 套件來對 log 做即時監控,只要有新增的 log 便會 post 出去

## 執行

### server 端
>在運行此程式前需要先把負責寫入 DB 的server打開。

`python3 collector.py`

### client 端
`python3 proccessor.py`

### 示意圖
![image](https://github.com/user-attachments/assets/a12229c4-1ff3-4e8d-a03a-ae9e30aca0c7)
