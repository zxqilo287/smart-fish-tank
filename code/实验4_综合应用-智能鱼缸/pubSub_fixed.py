#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
修复版 - 鱼缸IoT通信系统
'''
import sys
import os
import time

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "test"))

# 导入库
from IoT_device.client.IoT_client_config import IoTClientConfig
from IoT_device.client.IoT_client import IotClient
from IoT_device.request.services_properties import ServicesProperties


class PubSub_command:
    '''
    树莓派端，与华为云IOT 平台通信
    '''

    def __init__(self, server_ip, device_id, secret):
        self.server_ip = server_ip
        self.device_id = device_id
        self.secret = secret
        self.commandFromIot = 'REMOTEOFF'

        print(f"正在连接设备: {device_id}")

        try:
            # 客户端配置
            self.client_cfg = IoTClientConfig(
                server_ip=self.server_ip,
                device_id=self.device_id,
                secret=self.secret,
                is_ssl=False
            )
            # 创建设备
            self.iot_client = IotClient(self.client_cfg)
            self.iot_client.connect()  # 建立连接
            print("✅ MQTT连接成功")

            # 设置响应命令的回调
            self.iot_client.set_command_callback(self._command_callback)
            print("✅ 命令回调设置成功")

        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise

    def _command_callback(self, request_id, command):
        # 响应平台下发命令,取出命令参数
        self.iot_client.respond_command(request_id, result_code=0)
        _command = command.paras
        self.commandFromIot = list(_command.keys())[0] + list(_command.values())[0]
        print('📲 收到 IOT 平台命令：', self.commandFromIot)

    def report_properties(self, properties):
        # 属性上报
        service_property = ServicesProperties()
        for prop in properties:
            service_property.add_service_property(
                service_id=prop[0],
                property=prop[1],
                value=prop[2]
            )
        self.iot_client.report_properties(
            service_properties=service_property.service_property,
            qos=1
        )

    def get_command(self):
        return self.commandFromIot


def main():
    print("=" * 50)
    print("       鱼缸IoT通信系统")
    print("=" * 50)

    server_ip = os.environ.get('IOT_SERVER_IP', 'your_server_ip')
    device_id = os.environ.get('IOT_DEVICE_ID', 'your_device_id')
    secret = os.environ.get('IOT_SECRET', 'your_secret')

    try:
        # 创建IoT客户端
        comm_Iot = PubSub_command(server_ip, device_id, secret)
        comm_Iot.iot_client.start()  # 线程启动
        print("✅ IoT客户端启动成功")

        # 定时上报属性
        luminance = 1

        print("\n开始上报数据...")
        print("-" * 40)

        while True:
            properties = []
            properties.append(["BasicData", 'luminance', luminance])

            current_time = time.strftime('%H:%M:%S')
            print(f"[{current_time}] 📊 上报光照强度: {luminance} lux")

            comm_Iot.report_properties(properties)  # 上报属性
            commandFromIot = comm_Iot.get_command()  # 获取命令

            if commandFromIot != 'REMOTEOFF':
                print(f"    📲 收到远程命令: {commandFromIot}")

            time.sleep(3)
            luminance += 1

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()