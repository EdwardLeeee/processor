import subprocess

# := 可在while 條件中直接賦值 然後可比較
while (input_file_path := input('input file path (or type "exit" to leave): ')) != 'exit':
    output_file_path = input('output file path: ')

    # 打開原始 Big5 編碼的日誌檔案並讀取其內容
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

