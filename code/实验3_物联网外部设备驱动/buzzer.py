from config import *
import RPi.GPIO as GPIO
import time

GPIO_BUZZER = 11
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GPIO_BUZZER,GPIO.OUT)

class Buzzer:
    def __init__(self, pin):
        self.onebeepdelay = 0.05   # 每次鸣叫时长10ms
        self.betweenbeeps = 1      # 鸣叫间隔时间
        self.num = 10              # 鸣叫次数
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)  # 设置GPIO为输出模式

    def __oneBeep(self, delay):
        GPIO.output(self.pin, 1)
        time.sleep(delay)
        GPIO.output(self.pin, 0)

    def beep(self):
        for i in range(self.num):
            self.__oneBeep(self.onebeepdelay)
            time.sleep(self.betweenbeeps)

    def clean(self):
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        buzzer = Buzzer(GPIO_BUZZER)
        buzzer.beep()
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        buzzer.clean()
        print("GPIO已清理")
