import time
from config import *
import RPi.GPIO as GPIO


class Stepping_motor:
    def __init__(self, pin):
        self.pulse = [
            (1, 0, 0, 1),
            (0, 0, 0, 1),
            (0, 0, 1, 1),
            (0, 0, 1, 0),
            (0, 1, 1, 0),
            (0, 1, 0, 0),
            (1, 1, 0, 0),
            (1, 0, 0, 0)
        ]
        self.phaseA, self.phaseB, self.phaseC, self.phaseD = pin
        GPIO.setup(self.phaseA, GPIO.OUT)
        GPIO.setup(self.phaseB, GPIO.OUT)
        GPIO.setup(self.phaseC, GPIO.OUT)
        GPIO.setup(self.phaseD, GPIO.OUT)

        self.__set_step((0, 0, 0, 0))

    def __set_step(self, pulseIn):
        p1, p2, p3, p4 = pulseIn
        GPIO.output(self.phaseA, p1)
        GPIO.output(self.phaseB, p2)
        GPIO.output(self.phaseC, p3)
        GPIO.output(self.phaseD, p4)

    def rotate_90_clockwise(self):
        """顺时针90度"""
        delay = 3 / 1000.0
        steps = 128
        for i in range(steps):
            for j in range(len(self.pulse)):
                self.__set_step(self.pulse[j])
                time.sleep(delay)
        self.__set_step((0, 0, 0, 0))

    def rotate_90_counterclockwise(self):
        """逆时针90度"""
        delay = 5 / 1000.0
        steps = 128
        for i in range(steps):
            for j in range(len(self.pulse) - 1, -1, -1):
                self.__set_step(self.pulse[j])
                time.sleep(delay)
        self.__set_step((0, 0, 0, 0))

    def rotate(self, direction=0):
        delay = 5 / 1000.0
        try:
            if direction == 1:
                while True:
                    for j in range(len(self.pulse) - 1, -1, -1):
                        self.__set_step(self.pulse[j])
                        time.sleep(delay)
            else:
                while True:
                    for j in range(len(self.pulse)):
                        self.__set_step(self.pulse[j])
                        time.sleep(delay)
        except KeyboardInterrupt:
            self.__set_step((0, 0, 0, 0))
            print("电机已停止")

    def clean(self):
        self.__set_step((0, 0, 0, 0))
        GPIO.cleanup()


if __name__ == '__main__':

    motor = Stepping_motor((GPIO_PHASE_A, GPIO_PHASE_B, GPIO_PHASE_C, GPIO_PHASE_D))
    try:
        while True:
            try:
                direction = int(input("请输入 0（顺时针） or 1（逆时针） or 2（持续旋转）: "))
                if direction == 0:
                    print("顺时针旋转90度")
                    motor.rotate_90_clockwise()
                    print("旋转完成")
                elif direction == 1:
                    print("逆时针旋转90度")
                    motor.rotate_90_counterclockwise()
                    print("旋转完成")
                elif direction == 2:
                    dir_continuous = int(input("请输入 0（顺时针） or 1（逆时针）: "))
                    print("持续旋转中... Ctrl+C停止")
                    motor.rotate(direction=dir_continuous)
                else:
                    print("输入无效，请输入0、1或2")
            except ValueError:
                print("输入无效，请输入数字")
            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break

    except Exception as e:
        print('An exception has happened:', e)
    finally:
        motor.clean()

