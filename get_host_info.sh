#!/bin/bash

# 获取主机名称和 IP 地址
host_name=$(hostname)
host_ip=$(hostname -I | awk '{print $1}')

# 输出结果
echo "HOST_NAME=$host_name"
echo "HOST_IP=$host_ip"

