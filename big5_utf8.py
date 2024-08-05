import configparser
import subprocess

# 读取配置文件
config = configparser.ConfigParser()
config.read('/home/oraclelee/Desktop/collector/config/test2.conf')

# 从配置文件中获取路径
input_file_path = config.get('input', 'file_path')
output_file_path = config.get('output', 'file_path')

# 打开原始 Big5 编码的日誌檔案並讀取其內容
with open(input_file_path, 'r', encoding='big5', errors='replace') as input_file:
    content = input_file.read()

# 將內容寫入新的 UTF-8 編碼的檔案
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(content)

print(f'The file has been converted and saved as {output_file_path}')
print()

# 设置 Shell 脚本的可执行权限
subprocess.run(['chmod', '+x', 'send_logs.sh'])

# 调用 Shell 脚本并传递参数
subprocess.run(['./send_logs.sh', output_file_path])


