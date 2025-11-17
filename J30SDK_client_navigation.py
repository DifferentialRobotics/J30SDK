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
import rospy
# 全局变量
udp_transport = None
current_state = 0

class UDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.last_send_time = None

    def connection_made(self, transport):
        global udp_transport
        self.transport = transport
        udp_transport = transport  # 设置全局transport变量
        print("客户端已连接到服务器")
        send_command_request("navigation_start")

    def handle_json_response(self, data, addr):
        """处理服务器返回的JSON响应"""
        try:
            message = json.loads(data.decode('utf-8'))
            title = message.get('title', '')
            guid = message.get('guid', '')
            timestamp = message.get('timestamp', 0)
            result = message.get('data', {}).get('result', '')
            
            print(f"收到来自 {addr} 的JSON响应: {title}")
            
            if title == "response_navigation_start":
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

    def datagram_received(self, data, addr):
        try:
            # 检查是否为JSON消息
            if data.startswith(b'{') and data.endswith(b'}'):
                self.handle_json_response(data, addr)
                return
                
            if len(data) >= 4:
                msg_type = struct.unpack('i', data[:4])[0]                    
                if msg_type == 1:  # 里程计消息
                    if len(data) >= 36:
                        msg_type, x, y, z, ox, oy, oz, ow, secs, nsecs = struct.unpack('ifffffffqq', data)
                        # self.visualizer.update_odom(x, y, z, ox, oy, oz, ow)
                        print(f"[odom] position: ({x:.2f}, {y:.2f}, {z:.2f}) orientation: ({ox:.2f}, {oy:.2f}, {oz:.2f}, {ow:.2f})")
                    else:
                        print("[odom] odom data length error")
                elif msg_type == 10:  # PointCloud2格式点云
                    try:
                        msg_type, num_points = struct.unpack('II', data[:8])
                        expected_length = 8 + num_points * 12  # 3 float × 4 bytes
                        if len(data) < expected_length:
                            print(f"点云数据长度不足，期望 {expected_length} 字节，实际 {len(data)}")
                            return
                        points = struct.unpack(f'{num_points * 3}f', data[8:expected_length])
                        points = np.array(points, dtype=np.float32).reshape(-1, 3)
                        for i in range(min(1, num_points)):
                            print(f"[pointcloud] 点云的坐标x: {points[i][0]}, y: {points[i][1]}, z: {points[i][2]}")
                    except Exception as e:
                        print(f"解析PointCloud2点云时出错: {e}")
                elif msg_type == 11:  # BatteryState电池消息
                    try:
                        if len(data) >= struct.calcsize('ifqq'):
                            msg_type, voltage, secs, nsecs = struct.unpack('ifqq', data)
                            timestamp = rospy.Time(secs, nsecs)
                            print(f"[battery] 电压: {voltage:.2f} V | 时间: {timestamp.secs}.{timestamp.nsecs}")
                            
                        else:
                            print("[battery] 电池数据长度错误")
                    except Exception as e:
                        print(f"解析BatteryState消息时出错: {e}")
                elif msg_type == 20:  # 飞机状态
                    try:
                        if len(data) >= struct.calcsize('ii'):
                           msg_type, current_state = struct.unpack('ii', data[:8])
                           if current_state == 0:
                               state_str = "待命"
                           elif current_state == 1:
                               state_str = "起飞"
                           elif current_state == 2:
                               state_str = "降落"
                           elif current_state == 3:
                               state_str = "导航中"
                           elif current_state == 4:
                               state_str = "指点飞行中"
                        #    elif current_state == 5:
                        #        state_str = "自动悬停中"
                           else:
                                state_str = "未知状态"
                        print(f"[plane] 飞机状态: {state_str}")
                    except Exception as e:
                        print(f"解析飞机状态时出错: {e}")

                else:
                    print(f"收到未知类型数据: {msg_type}")
                    return

                
        except Exception as e:
            print("解析数据时出错：", e)

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

def create_navigation_start_request():
    """创建导航开始请求消息"""
    request = {
        "version": "1.1.0",
        "title": "request_navigation_start",
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
        if command_type == "navigation_start":
            request_data = create_navigation_start_request()
            print("发送导航开始请求")
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

