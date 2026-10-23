from config import *
import smbus2 as smbus
import time


# 定义Bh1750类
class Bh1750:
    def __init__(self, addr):
        self.ADDR = addr
        self.PWR_ON = 0X01
        self.THRES = 0x20
        self.bus = smbus.SMBus(1)

    def measure(self):
        self.bus.write_byte(self.ADDR, self.PWR_ON)
        self.bus.write_byte(self.ADDR, self.THRES)
        time.sleep(0.2)
        res = self.bus.read_word_data(self.ADDR, 0)
        res = ((res >> 8) & 0xff) | ((res << 8) & 0xff00)
        res = round(res / 1.2, 1)
        return res


def main():
    light = Bh1750(I2C_ADDR)
    while True:
        res = light.measure()
        print("当前环境光照强度为:{}".format(res))
        time.sleep(3)



if __name__ == '__main__':
    main()