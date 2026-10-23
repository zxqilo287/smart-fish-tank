import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

GPIO_BUZZER = 11  # 控制针脚


class Buzzer:
    def __init__(self, pin):
        self.onebeepdelay = 0.1  # 每次鸣叫时长100ms
        self.betweenbeeps = 0.9  # 间隔时间
        self.num = 10  # 鸣叫次数
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.HIGH)  # 初始静音（高电平）

    def __oneBeep(self, delay):
        GPIO.output(self.pin, GPIO.LOW)  # 低电平触发 -> 响
        time.sleep(delay)
        GPIO.output(self.pin, GPIO.HIGH)  # 高电平 -> 停
        time.sleep(self.betweenbeeps)

    def beep(self):
        for i in range(self.num):
            self.__oneBeep(self.onebeepdelay)
        self.clean()

    def clean(self):
        GPIO.cleanup()


if __name__ == "__main__":
    buzzer = Buzzer(GPIO_BUZZER)
    buzzer.beep()
