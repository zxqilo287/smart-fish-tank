from config import *
import RPi.GPIO as GPIO
import time


class Led:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 1000)
        self.pwm.start(0)

    def on(self):
        self.pwm.ChangeDutyCycle(100)

    def off(self):
        self.pwm.ChangeDutyCycle(0)

    def set_brightness(self, level):
        duty_cycle = level * 10
        self.pwm.ChangeDutyCycle(duty_cycle)

    def blink(self):
        try:
            while True:
                self.on()
                time.sleep(0.2)
                self.off()
                time.sleep(0.8)
        except KeyboardInterrupt:
            pass

    def fade_in(self):
        try:
            while True:
                for level in range(10):
                    self.set_brightness(level)
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
    def cleanup(self):
        if hasattr(self, 'pwm'):
            self.pwm.stop()
            del self.pwm
        GPIO.cleanup()

if __name__ == "__main__":
    led = None
    try:
        led = Led(GPIO_LED)

        print("选择功能：")
        print("1. LED闪烁（亮0.2秒，灭0.8秒）")
        print("2. LED渐变亮度")

        choice = input("请输入选择（1或2）: ")

        if choice == "1":
            print("LED闪烁")
            led.blink()
        elif choice == "2":
            print("LED渐变亮度")
            led.fade_in()
        else:
            print("无效")

    except KeyboardInterrupt:
        pass
