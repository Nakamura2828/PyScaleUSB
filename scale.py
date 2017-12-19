from __future__ import print_function

import hid
import time
import sys
from struct import *

DEBUG = False

grams_per_oz = 28.3495

def restart_line():
    sys.stdout.write('\r')
    sys.stdout.flush()

class Scale:
    def __init__(self, vid=-1, pid=-1):
        self.vid = -1
        self.pid = -1
        if vid < 0 or pid < 0:
            for d in hid.enumerate():
                keys = list(d.keys())
                if d['vendor_id'] == 8755 and d['product_id'] == 25379:
                    self.myDevice = RadioShackScale()
                    return
                if ('usage' not in keys or 'usage_page' not in keys or not (
                        d['usage'] == 32 and d['usage_page'] == 141)):  # Find HID weighing devices
                    continue

                if DEBUG == True:
                    for key in keys:
                        print("%s : %s" % (key, d[key]))
                    print(str(d['vendor_id']) + ':' + str(d['product_id']))

                self.vid = d['vendor_id']
                self.pid = d['product_id']
                break
            if self.vid == -1 or self.pid == -1:
                raise OSError('No HID weighing device found')

        else:
            self.vid = vid
            self.pid = pid

        self.myDevice = StandardHIDScale(self.vid,self.pid)
        self.type = 'StandardHIDScale'

    def read(self):
        return self.myDevice.read()

class RadioShackScale(Scale):
    def __init__(self):
        self.vid = 8755
        self.pid = 25379

        self.device = hid.device()
        try:
            self.device.open(self.vid, self.pid)
        except OSError as ex:
            print(ex)
            print("Couldn't connect to scale")

    def read(self):
        tare_offset = 1363.6
        scale_factor = 2.571181854

        window_size = 5
        samples = []

        try:
            reading = self.device.read(64)
            if reading:
                # append new samples (each sample converts the last two bytes to an unsigned big-endian short)_
                samples.append(unpack('>h', pack('>H', reading[6] << 8 | reading[7]))[0])
                if (len(samples) > window_size):
                    samples.pop(0)  # remove old samples

                metric = False

                self.value = int((sum(samples) / len(samples) + tare_offset) / scale_factor)  # calculate moving average

                if metric:
                    self.unit = 'g'
                else:
                    self.unit = 'oz'
                    self.value = round(self.value / grams_per_oz, 1)

                #print(reading)
                return {'value':self.value,'unit':self.unit}
            else:
                return {'value':-1,'unit':'?'}
        except IOError as ex:
            print(ex)
            print("Couldn't read from scale")

class StandardHIDScale(Scale):
    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid

        self.device = hid.device()
        try:
            self.device.open(self.vid, self.pid)
        except OSError as ex:
            print(ex)
            print("Couldn't connect to scale")

    def read(self):
        try:
            reading = self.device.read(64)
            if reading:
                self.unit = {2:'g',11:'oz'}[reading[2]]
                self.value = reading[5] << 8 | reading[4]  # 5th bit MSD, 4th bit LSD
                if self.unit == 'oz':
                    self.value /= 10
                return {'value':self.value, 'unit':self.unit}
            else:
                return {'value':-1,'unit':'?'}
        except IOError as ex:
            print(ex)
            print("Couldn't read from scale")


def main():
    try:
        s = Scale()

        while True:
           weight = s.read()
           if weight:
                sys.stdout.write(str(weight['value']) + weight['unit'])
           else:
                raise IOError("Couldn't read from scale")
                break

           sys.stdout.flush()
           time.sleep(0.5)
           restart_line()
    except OSError as ex:
        print(ex);
        exit()
    except IOError as ex:
        print(ex)
        exit()

if __name__ == '__main__':
    main()