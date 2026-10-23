import spidev
import time
class WaterLevel:
    def __init__(self, channel, refVolt, resolution, range):
        self.channel = channel
        self.refVolt = refVolt
        self.range = range
        self.resolution = resolution

        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1350000
        self.spi.mode = 0

    def _getMcp3008(self):
        adc = self.spi.xfer2([1, (8 + self.channel) << 4, 0])
        data = ((adc[1] & 3) << 8) + adc[2]
        return data

    def _toVolt(self, data):
        max_adc = (1 << self.resolution) - 1  # 修正：2^10 - 1 = 1023
        return (data / max_adc) * self.refVolt

    def _toLevel(self, volts):
        return (volts / self.refVolt) * self.range

    def read(self, channel=None):
        if channel is not None:

            self.channel = channel

        data = self._getMcp3008()
        volt = self._toVolt(data)
        level = self._toLevel(volt)
        return level, volt


if __name__ == '__main__':
    waterLevel = WaterLevel(0, 3.3, 10, 48)
    while True:
        level, volt = waterLevel.read()
        print('电压:{:.1f}V, 液面:{:.1f}cm'.format(volt, level))
        time.sleep(3)