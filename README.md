## 0.总览
本SDK软件包功能为使用客户端-服务器形式实现主机与J30机载电脑通讯，使得能在不同操作系统平台上为J30的导航模块Diff-Planner发送*开始导航任务*/*起飞*/*指点飞行*/*降落*等命令，同时也给出了远程拉取和推送视频流的教程。

## 1.远程连接Diff-Planner方式
### 1.1 准备工作
1. 将J30与主机端连入同一局域网
2. 将软件包中服务器程序 [udp_server_new.cpython-38.pyc](udp_server_new.cpython-38.pyc) 文件下载到J30中，先运行roscore，再运行服务器程序
>- roscore  
>- python udp_server_new.cpython-38.pyc 

3. 保证Diff-planner/src/diff_planner/plan_manage/launch/include/advanced_param_exp.xml的中飞行模式参数fsm/flight_type为1。

4. [J30SDK_client_navigation.py](J30SDK_client_navigation.py)/[J30SDK_client_takeoff.py](J30SDK_client_takeoff.py)/[J30SDK_client_waypoint.py](J30SDK_client_waypoint.py)/[J30SDK_client_land.py](J30SDK_client_land.py)分别为发送*开始导航任务*/*起飞*/*指点飞行*/*降落*命令的客户端程序，将其下载到主机端，使用前需要将主机与J30连到同一局域网下，并将文件中 **send_command_request** 函数里如下一行的ip地址改为J30机载电脑的实际ip，端口号保持8765不变:
>- udp_transport.sendto(request_data, ('192.168.48.126', 8765))

5. 发送的消息格式为json类型，定义在对应.py文件下的 **create_xx_request** 函数中，形式如下:

```
{
    "version": "1.1.0",
    "title": "request_xx",（将xx改写成navigation_start/takeoff/waypoints_navigation/land 分别可以实现启动规划器/起飞/指点飞行/降落）
    "timestamp": generate_timestamp(),
    "guid": request_guid,
    "data": {
        "result": result
    }
}
```

5) 可以通过解析服务端返回的json格式消息中title字段的result值获取服务端响应情况，定义在各个.py文件下的 **handle_json_response** 函数中：
```
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
```

### 1.2 启动Diff-Planner
启动前请按照产品手册检查遥控器拨杆，保证其处于正确的位置：5、6、8通道在下，7通道在上。
在主机端运行 [J30SDK_client_navigation.py](J30SDK_client_navigation.py) 文件启动规划器：
> python J30SDK_client_navigation.py

启动后需要等待至少20s，保证所有节点都启动完毕。向服务器发送的json消息为：
```
{
    "version": "1.1.0",
    "title": "request_navigation_start",
    "timestamp": generate_timestamp(),
    "guid": generate_guid(),
    "data": {}
} 
```    

### 1.3 发送起飞指令
在主机端运行[J30SDK_client_takeoff.py](J30SDK_client_takeoff.py)文件：
> python J30SDK_client_takeoff.py

无人机自动起飞至预设高度后悬停。向服务器发送的json消息为：
```
request = {
    "version": "1.1.0",
    "title": "request_takeoff",
    "timestamp": generate_timestamp(),
    "guid": generate_guid(),
    "data": {}
}
```

### 1.4 发送指点导航指令
修改 [J30SDK_client_waypoint.py](J30SDK_client_waypoint.py) 文件中 **create_xx_request** 函数中传入的x/y/z值，作为指点飞行的目标点：
```
def create_waypoints_request(x=6.0, y=0.0, z=1.0): #修改此处传入的x/y/z为预设的目标点
    """创建发送waypoints请求消息"""
    request = {
        "version": "1.1.0",
        "title": "request_waypoints_navigation",
        "timestamp": generate_timestamp(),
        "guid": generate_guid(),
        "data": {
            "target": {
                "x": x,
                "y": y,
                "z": z
            }
        }
    }
    return json.dumps(request).encode('utf-8')
```
待无人机悬停稳定后，在主机端运行该文件以发送目标点：
> python J30SDK_client_waypoint.py

### 1.5 发送降落指令
待无人机到达目标点悬停稳定后，在主机端运行 [J30SDK_client_land.py](J30SDK_client_land.py) 文件使无人机自主降落：
> python J30SDK_client_land.py

待无人机降落至地面后，将无人机7通下拨锁桨。向服务器发送的json消息为：
```
request = {
    "version": "1.1.0",
    "title": "request_land",
    "timestamp": generate_timestamp(),
    "guid": generate_guid(),
    "data": {}
}
```

### 1.6 点云、里程计、电池电量、飞行执行任务状态数据获取
在启动 [J30SDK_client_navigation.py](J30SDK_client_navigation.py) 后，主机能够接收由J30机载电脑传输的点云、里程计、电池电量、飞行状态数据，由json消息中的msg_type字段标识：
```
msg_type==10: 点云数据
msg_type==1 : 里程计数据
msg_type==11: 电池电量
msg_type==20: 飞行执行任务状态
```
数据的具体解析方法请参考 [J30SDK_client_navigation.py](J30SDK_client_navigation.py)中的 **datagram_received** 函数。

## 2 视频数据推流/拉流
### 2.1 准备工作
1. J30和主机端连接在同一局域网

2. 将本软件包下 [mediamtx_v1.13.0_linux_arm64.tar.gz](mediamtx_v1.13.0_linux_arm64.tar.gz) 压缩文件下载到J30上并解压，启动推流脚本：
```
cd mediamtx_v1.15.2_linux_arm64
chmod +x mediamtx
./mediamtx
```

### 2.2 使用TCP协议推流/拉流
#### 2.2.1 视频推流（J30上）
```
ffmpeg -re -f v4l2 -i /dev/video0 \ #video*为相机占用的端口号
-c:v libx264 -preset ultrafast -tune zerolatency \
-b:v 1M \
-f mpegts "tcp://192.168.48.126:8080?listen=1" #ip地址改为主机端ip
```
#### 2.2.2 视频拉流（主机端）
```
ffplay -fflags nobuffer -flags low_delay -framedrop udp://192.168.48.121:8080 #ip地址改为J30的ip
```
### 2.3 使用UDP协议推流/拉流
#### 2.3.1 视频推流（J30上）
```
ffmpeg -re -f v4l2 -i /dev/video0 \ #video*为相机占用的端口号
-c:v libx264 -preset ultrafast -tune zerolatency \
-b:v 1M -maxrate 1M -bufsize 2M \
-g 30 -keyint_min 30 \
-flags +global_header \
-f mpegts "udp://192.168.48.121:8080?pkt_size=1316" #ip地址改为主机端ip
```
#### 2.3.2 视频拉流（主机端）
```    
ffplay -fflags nobuffer -flags low_delay -framedrop udp://192.168.48.121:8080 #ip地址改为J30的ip
```

### 2.4 webrtc推流（稳定延迟低）
#### 2.4.1 准备步骤
1. 在J30上运行：
```
 openssl genrsa -out server.key 2048
 openssl req -new -x509 -sha256 -key server.key -out server.crt -days 3650 -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"
```
2. 在J30上 [mediamtx_v1.13.0_linux_arm64](mediamtx_v1.13.0_linux_arm64.tar.gz) 中的mediamtx.yaml中添加如下配置：
```
webrtc: yes

webrtcAddress: :8889

webrtcEncryption: no

webrtcAllowOrigin: '*'

webrtcLocalUDPAddress: :8189
webrtcLocalTCPAddress: ''

webrtcIPsFromInterfaces: yes

webrtcICEServers2:
- url: stun:stun.l.google.com:19302
- url: stun:stun1.l.google.com:19302

webrtcHandshakeTimeout: 5s
webrtcTrackGatherTimeout: 1s
webrtcSTUNGatherTimeout: 2s
```

#### 2.4.2 视频推流（J30上）：
```
ffmpeg -f v4l2 -framerate 30 -video_size 640x480 -i /dev/video0 \ #video*为相机占用的端口号
    -c:v libx264 -preset ultrafast -tune zerolatency -g 30 \
    -rtsp_transport tcp -f rtsp rtsp://192.168.48.126:8554/live/stream #ip改成J30的地址
    
```
#### 2.4.3 视频拉流（主机端）：
在谷歌浏览器上输入：
>- 192.168.48.126:8554/live/stream #ip需要改成J30的地址
