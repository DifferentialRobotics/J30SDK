#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import time
import struct
import numpy as np
import threading
from collections import deque
import math
import random
import uuid
# 全局变量
udp_transport = None

class UDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.last_send_time = None

    def connection_made(self, transport):
        global udp_transport
        self.transport = transport
        udp_transport = transport  # 设置全局transport变量
        print("客户端已连接到服务器")
        send_command_request("land")

    def handle_json_response(self, data, addr):
        """处理服务器返回的JSON响应"""
        try:
            message = json.loads(data.decode('utf-8'))
            title = message.get('title', '')
            guid = message.get('guid', '')
            timestamp = message.get('timestamp', 0)
            result = message.get('data', {}).get('result', '')
            
            print(f"收到来自 {addr} 的JSON响应: {title}")
            
            if title == "response_takeoff":
                if result == "success":
                    print(f"✅ 起飞指令执行成功 (GUID: {guid})")
                else:
                    print(f"❌ 起飞指令执行失败: {result} (GUID: {guid})")
                    
            elif title == "response_land":
                if result == "success":
                    print(f"✅ 降落指令执行成功 (GUID: {guid})")
                else:
                    print(f"❌ 降落指令执行失败: {result} (GUID: {guid})")
                    
            elif title == "response_navigation_start":
                if result == "success":
                    print(f"✅ 导航开始指令执行成功 (GUID: {guid})")
                else:
                    print(f"❌ 导航开始指令执行失败: {result} (GUID: {guid})")
                    
            else:
                print(f"收到未知JSON响应类型: {title}")
                
        except json.JSONDecodeError as e:
            print(f"JSON响应解析错误: {e}")
        except Exception as e:
            print(f"处理JSON响应时出错: {e}")

    def error_received(self, exc):
        print(f"接收数据时出错: {exc}")

async def send_delay_data(transport, protocol):
    while True:
        now = time.time()
        protocol.last_send_time = now
        
        data = {
            "Type": "Delay",
            "Data": {
                "Delay": now
            }
        }
        msg = json.dumps(data)
        transport.sendto(msg.encode('utf-8'))
        print(f"send time: {now}")
        await asyncio.sleep(1)

async def udp_client():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPClientProtocol(),
        remote_addr=('192.168.48.126', 8765)
    )
    
    try:
        await send_delay_data(transport, protocol)
    except KeyboardInterrupt:
        print("客户端关闭")
    finally:
        transport.close()

def generate_guid():
    """生成唯一标识符"""
    return str(uuid.uuid4()).replace('-', '')

def generate_timestamp():
    """生成时间戳（毫秒）"""
    return int(time.time() * 1000)

def create_land_request():
    """创建降落请求消息"""
    request = {
        "version": "1.1.0",
        "title": "request_land",
        "timestamp": generate_timestamp(),
        "guid": generate_guid(),
        "data": {}
    }
    return json.dumps(request).encode('utf-8')
        
def send_command_request(command_type):
    """发送指令请求"""
    global udp_transport
    if udp_transport is None:
        print("UDP连接未建立，无法发送指令")
        return
    
    try:
        if command_type == "land":
            request_data = create_land_request()
            print("发送降落请求")
        else:
            print(f"未知的指令类型: {command_type}")
            return
            
        # 发送到服务器地址
        udp_transport.sendto(request_data, ('192.168.48.126', 8765))
        print(f"已发送{command_type}指令请求")
        
    except Exception as e:
        print(f"发送{command_type}指令时出错: {e}")

def main():

    
    time.sleep(1)
    
    try:
        asyncio.run(udp_client())
    except KeyboardInterrupt:
        print("程序被中断")
    finally:
        print("程序已退出")

if __name__ == "__main__":
    main() 

