import RPi.GPIO as GPIO
import time

LED_PIN = 7  # 物理引脚7

def setup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(LED_PIN, GPIO.OUT)

def led_blink():
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(0.4)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(0.6)

def cleanup():
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        setup()
        led_blink()
    except KeyboardInterrupt:
        cleanup()
