#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化鱼缸系统 - 实验4.1 & 4.2
功能：光照自动调节 + 液位自动调节 + 水温自动调节 + 华为云IoT接入
"""

import os
import time
import math
import threading
import traceback
import RPi.GPIO as GPIO
import spidev
import atexit
import sys
import random

# ====== 添加IoT模块路径 ======
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "test"))

# ====== 导入IoT模块 ======
try:
    from IoT_device.client.IoT_client_config import IoTClientConfig
    from IoT_device.client.IoT_client import IotClient
    from IoT_device.request.services_properties import ServicesProperties

    IOT_AVAILABLE = True
    print("✅ IoT模块导入成功")
except ImportError as e:
    print(f"❌ IoT模块导入失败: {e}")
    IOT_AVAILABLE = False

# ====== 导入其他模块 ======
try:
    import BH1750

    BH1750_AVAILABLE = True
except ImportError as e:
    print("导入 BH1750 失败，自动切换到模拟模式：", e)
    BH1750_AVAILABLE = False

from Step_water import Stepping_motor

# ====== 硬件引脚定义（BOARD编号） ======
# 执行器引脚
PIN_LED = 13  # BOARD 13 - LED灯
PIN_BUZZER = 15  # BOARD 15 - 蜂鸣器
PIN_HEATER = 11  # BOARD 11 - 加热器继电器

# 步进电机引脚（使用你的Step_water.py中的定义）
GPIO_PHASE_A = 32
GPIO_PHASE_B = 36
GPIO_PHASE_C = 38
GPIO_PHASE_D = 40

# ====== 系统参数配置 ======
# 光照参数
LIGHT_ON_LUX = 300  # 低于该值：打开LED
LIGHT_OFF_LUX = 700  # 高于该值：关闭LED

# 液位参数（单位：cm）
LEVEL_MIN_CM = 10.0  # 最低液位，开始补水
LEVEL_TARGET_CM = 30.0  # 目标液位，停止补水
LEVEL_CRITICAL_CM = 5.0  # 危险液位，报警

# 水温参数（单位：°C）
TEMP_TARGET_MIN = 18.0  # 目标最低温度
TEMP_TARGET_MAX = 20.0  # 目标最高温度
TEMP_CRITICAL_LOW = 15.0  # 危险低温，报警

# 监测周期（秒）
LIGHT_READ_PERIOD = 2.0
LEVEL_READ_PERIOD = 5.0
TEMP_READ_PERIOD = 3.0
IOT_REPORT_PERIOD = 10.0

# ====== MCP3008 ADC配置 ======
SPI_BUS = 0
SPI_DEVICE = 0
VREF = 3.3

# ====== 全局状态变量 ======
gpio_lock = threading.Lock()
stop_event = threading.Event()
system_status = {
    "light_level": 0,
    "water_level": 0,
    "water_temp": 0,
    "led_status": False,
    "heater_status": False,
    "tap_status": False,
    "alarm_status": False
}


# ====== IoT通信类 ======
class FishTankIoT:
    def __init__(self):
        if not IOT_AVAILABLE:
            self.client = None
            return

        try:
            server_ip = os.environ.get('IOT_SERVER_IP', 'your_server_ip')
            device_id = os.environ.get('IOT_DEVICE_ID', 'your_device_id')
            secret = os.environ.get('IOT_SECRET', 'your_secret')

            self.client_cfg = IoTClientConfig(
                server_ip=server_ip,
                device_id=device_id,
                secret=secret,
                is_ssl=False
            )
            self.client = IotClient(self.client_cfg)
            self.client.connect()
            self.client.start()
            print("✅ IoT平台连接成功")

        except Exception as e:
            print(f"❌ IoT平台连接失败: {e}")
            self.client = None

    def report_status(self, status):
        if not self.client:
            return

        try:
            properties = []
            # 上报所有状态数据
            properties.append(["LightData", 'luminance', status["light_level"]])
            properties.append(["WaterData", 'level', status["water_level"]])
            properties.append(["WaterData", 'temperature', status["water_temp"]])
            properties.append(["DeviceData", 'led_status', status["led_status"]])
            properties.append(["DeviceData", 'heater_status', status["heater_status"]])
            properties.append(["DeviceData", 'tap_status', status["tap_status"]])
            properties.append(["DeviceData", 'alarm_status', status["alarm_status"]])

            service_property = ServicesProperties()
            for prop in properties:
                service_property.add_service_property(
                    service_id=prop[0],
                    property=prop[1],
                    value=prop[2]
                )

            self.client.report_properties(
                service_properties=service_property.service_property,
                qos=1
            )
            print("📡 状态数据上报成功")

        except Exception as e:
            print(f"❌ 数据上报失败: {e}")


# ====== GPIO初始化 ======
def setup_gpio():
    """初始化所有GPIO引脚"""
    try:
        GPIO.cleanup()
        time.sleep(1)
    except:
        pass

    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    # 初始化输出引脚
    GPIO.setup(PIN_LED, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_HEATER, GPIO.OUT, initial=GPIO.LOW)

    print("✅ GPIO初始化完成")


# ====== 执行器控制函数 ======
def led_on():
    with gpio_lock:
        GPIO.output(PIN_LED, GPIO.HIGH)
        system_status["led_status"] = True


def led_off():
    with gpio_lock:
        GPIO.output(PIN_LED, GPIO.LOW)
        system_status["led_status"] = False


def buzzer_on():
    with gpio_lock:
        GPIO.output(PIN_BUZZER, GPIO.LOW)  # 有源蜂鸣器低电平触发


def buzzer_off():
    with gpio_lock:
        GPIO.output(PIN_BUZZER, GPIO.HIGH)


def heater_on():
    with gpio_lock:
        GPIO.output(PIN_HEATER, GPIO.HIGH)
        system_status["heater_status"] = True


def heater_off():
    with gpio_lock:
        GPIO.output(PIN_HEATER, GPIO.LOW)
        system_status["heater_status"] = False


def trigger_alarm(duration=5):
    """触发报警"""
    system_status["alarm_status"] = True
    print("🚨 系统异常，触发报警！")

    # 蜂鸣器报警
    buzzer_on()
    time.sleep(duration)
    buzzer_off()

    system_status["alarm_status"] = False


# ====== 传感器读取类 ======
class MCP3008:
    """MCP3008 ADC读取类"""

    def __init__(self, bus=SPI_BUS, device=SPI_DEVICE):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 50000
        self.spi.mode = 0b00

    def read_voltage(self, channel):
        """读取指定通道的电压值"""
        assert 0 <= channel <= 7, '通道必须在0-7之间'
        adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
        value = ((adc[1] & 3) << 8) + adc[2]
        return value * VREF / 1023


class SensorReader:
    """传感器数据读取类"""

    def __init__(self):
        try:
            self.mcp = MCP3008()
            self.adc_available = True
        except:
            self.adc_available = False
            print("⚠️ MCP3008不可用，使用模拟数据")

    def read_light_level(self):
        """读取光照强度"""
        if BH1750_AVAILABLE:
            try:
                return BH1750.readLight()
            except:
                pass
        # 模拟光照数据（200-800 lux范围内波动）
        base_light = 500
        variation = 300 * math.sin(time.time() / 15.0)
        noise = random.uniform(-50, 50)
        return max(0, base_light + variation + noise)

    def read_water_level(self):
        """读取液位高度"""
        if self.adc_available:
            try:
                # 假设液位传感器在通道0，每伏特对应10cm
                voltage = self.mcp.read_voltage(0)
                level = voltage * 10  # 转换为cm
                return max(0, min(50, level))
            except:
                pass
        # 模拟液位数据（5-35cm范围内缓慢变化）
        base_level = 20
        variation = 10 * math.sin(time.time() / 30.0)
        return max(0, base_level + variation)

    def read_water_temperature(self):
        """读取水温"""
        if self.adc_available:
            try:
                # 假设温度传感器在通道1
                voltage = self.mcp.read_voltage(1)
                # 模拟温度传感器：每伏特对应25°C
                temp = voltage * 25
                return max(10, min(30, temp))
            except:
                pass
        # 模拟温度数据（16-22°C范围内波动）
        base_temp = 19.0
        variation = 3.0 * math.sin(time.time() / 20.0)
        noise = random.uniform(-0.5, 0.5)
        return base_temp + variation + noise


# ====== 自动控制线程类 ======
class LightControlThread(threading.Thread):
    """光照自动控制线程"""

    def __init__(self, sensor_reader):
        super().__init__(daemon=True)
        self.sensor_reader = sensor_reader
        self.name = "LightControl"

    def run(self):
        print("[光照控制] 线程启动")
        while not stop_event.is_set():
            try:
                light_level = self.sensor_reader.read_light_level()
                system_status["light_level"] = light_level

                print(f"[光照] 强度: {light_level:.1f} lux")

                # 光照自动控制逻辑
                if light_level < LIGHT_ON_LUX:
                    if not system_status["led_status"]:
                        led_on()
                        print("💡 光线不足，打开LED")
                elif light_level > LIGHT_OFF_LUX:
                    if system_status["led_status"]:
                        led_off()
                        print("💡 光线充足，关闭LED")

            except Exception as e:
                print(f"[光照控制] 错误: {e}")

            stop_event.wait(LIGHT_READ_PERIOD)


class WaterLevelControlThread(threading.Thread):
    """液位自动控制线程"""

    def __init__(self, sensor_reader):
        super().__init__(daemon=True)
        self.sensor_reader = sensor_reader
        self.motor = Stepping_motor([GPIO_PHASE_A, GPIO_PHASE_B, GPIO_PHASE_C, GPIO_PHASE_D])
        self.name = "WaterLevelControl"
        self.last_level = 0

    def run(self):
        print("[液位控制] 线程启动")
        while not stop_event.is_set():
            try:
                water_level = self.sensor_reader.read_water_level()
                system_status["water_level"] = water_level

                print(f"[液位] 高度: {water_level:.1f} cm")

                # 液位自动控制逻辑
                if water_level < LEVEL_MIN_CM and self.last_level >= LEVEL_MIN_CM:
                    if not system_status["tap_status"]:
                        print("🚰 液位过低，开始补水")
                        self.motor.open_tap()
                        system_status["tap_status"] = True

                elif water_level >= LEVEL_TARGET_CM and self.last_level < LEVEL_TARGET_CM:
                    if system_status["tap_status"]:
                        print("🚰 液位达标，停止补水")
                        self.motor.close_tap()
                        system_status["tap_status"] = False

                # 危险液位报警
                if water_level < LEVEL_CRITICAL_CM:
                    print("⚠️ 危险：液位极低！")
                    trigger_alarm(3)

                self.last_level = water_level

            except Exception as e:
                print(f"[液位控制] 错误: {e}")

            stop_event.wait(LEVEL_READ_PERIOD)


class TemperatureControlThread(threading.Thread):
    """水温自动控制线程"""

    def __init__(self, sensor_reader):
        super().__init__(daemon=True)
        self.sensor_reader = sensor_reader
        self.name = "TemperatureControl"
        self.last_temp = 0

    def run(self):
        print("[水温控制] 线程启动")
        while not stop_event.is_set():
            try:
                water_temp = self.sensor_reader.read_water_temperature()
                system_status["water_temp"] = water_temp

                print(f"[水温] 温度: {water_temp:.1f} °C")

                # 水温自动控制逻辑
                if water_temp < TEMP_TARGET_MIN and self.last_temp >= TEMP_TARGET_MIN:
                    if not system_status["heater_status"]:
                        heater_on()
                        print("🔥 水温过低，开启加热器")
                elif water_temp > TEMP_TARGET_MAX and self.last_temp <= TEMP_TARGET_MAX:
                    if system_status["heater_status"]:
                        heater_off()
                        print("🔥 水温达标，关闭加热器")

                # 危险低温报警
                if water_temp < TEMP_CRITICAL_LOW:
                    print("⚠️ 危险：水温过低！")
                    trigger_alarm(3)

                self.last_temp = water_temp

            except Exception as e:
                print(f"[水温控制] 错误: {e}")

            stop_event.wait(TEMP_READ_PERIOD)


class IoTReportThread(threading.Thread):
    """IoT数据上报线程"""

    def __init__(self, iot_client):
        super().__init__(daemon=True)
        self.iot_client = iot_client
        self.name = "IoTReport"

    def run(self):
        if not self.iot_client.client:
            print("[IoT] 客户端不可用，跳过上报")
            return

        print("[IoT上报] 线程启动")
        while not stop_event.is_set():
            try:
                self.iot_client.report_status(system_status)
            except Exception as e:
                print(f"[IoT上报] 错误: {e}")

            stop_event.wait(IOT_REPORT_PERIOD)


# ====== 主程序 ======
def main():
    print("=" * 50)
    print("       自动化鱼缸系统 - 实验4.1 & 4.2")
    print("=" * 50)

    # 初始化系统
    setup_gpio()

    # 创建传感器读取器
    sensor_reader = SensorReader()

    # 创建IoT客户端
    iot_client = FishTankIoT()

    # 创建并启动所有控制线程
    threads = [
        LightControlThread(sensor_reader),
        WaterLevelControlThread(sensor_reader),
        TemperatureControlThread(sensor_reader),
    ]

    if iot_client.client:
        threads.append(IoTReportThread(iot_client))

    for thread in threads:
        thread.start()
        print(f"✅ 启动线程: {thread.name}")

    print("\n🎯 系统运行中... 按 Ctrl+C 退出")
    print("监控信息:")
    print("- 光照强度 (lux)")
    print("- 液位高度 (cm)")
    print("- 水温 (°C)")
    print("- 设备状态")
    if iot_client.client:
        print("- IoT数据上报")

    try:
        # 主循环
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号，正在关闭系统...")

    finally:
        # 清理资源
        stop_event.set()

        # 关闭所有执行器
        led_off()
        buzzer_off()
        heater_off()

        # 等待线程结束
        for thread in threads:
            thread.join(timeout=2)

        GPIO.cleanup()
        print("✅ 系统已安全关闭")


def cleanup():
    """程序退出时的清理函数"""
    try:
        stop_event.set()
        GPIO.cleanup()
    except:
        pass


atexit.register(cleanup)

if __name__ == '__main__':
    main()