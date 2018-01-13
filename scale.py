from __future__ import print_function

import hid
import time
import sys
from struct import *

DEBUG = False

scale_status = {1: 'Scale Status Fault',
                2: 'Scale Status Stable at Zero',
                3: 'Scale Status In Motion',
                4: 'Scale Status Weight Stable',
                5: 'Scale Status Under Zero',
                6: 'Scale Status Over Weight Limit',
                7: 'Scale Status Requires Calibration',
                8: 'Scale Status Requires Re-zeroing'}

scale_units = {1: 'mg',
               2: 'g',
               3: 'kg',
               4: 'Carats',
               5: 'Taels',
               6: 'Grains',
               7: 'Pennyweights',
               8: 'metric tons',
               9: 'avoir tons',
               10: 'troy oz',
               11: 'oz',
               12: 'lb'}

grams_per_oz = 28.3495


def restart_line():
    sys.stdout.write("\r")
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

        self.myDevice = StandardHIDScale(self.vid, self.pid)
        self.type = 'StandardHIDScale'

    def read(self):
        return self.myDevice.read()


class RadioShackScale(Scale):
    def __init__(self):
        self.vid = 8755
        self.pid = 25379

        self.status = ''
        self.unit = ''
        self.scale_factor = 0
        self.value = 0

        self.device = hid.device()
        try:
            self.device.open(self.vid, self.pid)
            self.device..set_nonblocking(1)
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
                if len(samples) > window_size:
                    samples.pop(0)  # remove old samples

                metric = False
                self.status = '?'
                self.value = int((sum(samples) / len(samples) + tare_offset) / scale_factor)  # calculate moving average

                if metric:
                    self.unit = 'g'
                else:
                    self.unit = 'oz'
                    self.value = round(self.value / grams_per_oz, 1)

                # print(reading)
                return {'value': self.value, 'unit': self.unit, 'status': self.status}
            else:
                return {'value': -1, 'unit': '?'}
        except IOError as ex:
            print(ex)
            print("Couldn't read from scale")


class StandardHIDScale(Scale):
    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid

        self.status = ''
        self.unit = ''
        self.scale_factor = 0
        self.value = 0

        self.device = hid.device()
        try:
            self.device.open(self.vid, self.pid)
            self.device..set_nonblocking(1)
        except OSError as ex:
            print(ex)
            print("Couldn't connect to scale")

    def read(self):
        try:
            reading = self.device.read(48)
            if reading[0] == 3:  # 1st byte = weight report
                self.status = scale_status[reading[1]]  # 2nd byte = status
                self.unit = scale_units[reading[2]]  # 3rd byte = unit
                self.scale_factor = unpack('b', pack('B', reading[3]))[0]  # 4th byte scale factor (signed)
                self.value = reading[5] << 8 | reading[4]  # 5th byte MSD, 4th byte LSD
                self.value *= 10 ** self.scale_factor  # apply scale factor
                if reading[1] == 5:  # status under zero
                    self.value *= -1
                # print(reading)
                # print(self.status)
                return {'value': self.value, 'unit': self.unit, 'status': self.status}
            else:
                return {'value': -1, 'unit': '?'}
        except IOError as ex:
            print(ex)
            print("Couldn't read from scale")


def main():
    try:
        s = Scale()

        while True:
            weight = s.read()
            if weight:
                if weight['unit'] != '?':
                    sys.stdout.write(str(weight['value']) + weight['unit'])# + ' Status: '+weight['status']+"\n")
                else:
                    continue
            else:
                raise IOError("Couldn't read from scale")
                break

            sys.stdout.flush()

            # blah = input('Sample')
            time.sleep(.5)

            restart_line()
    except OSError as ex:
        print(ex)
        exit()
    except IOError as ex:
        print(ex)
        exit()


if __name__ == '__main__':
    main()
