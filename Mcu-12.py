import serial
import threading
import time
from threading import Timer
import math
import struct
import binascii
import random
from array import array

import socket
import sys
from _thread import *
import abc


#def ByteToHex(byteStr):
#    """
#    Convert a byte string to it's hex string representation e.g. for output.
#    """

    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #
    # hex = []
    # for aChar in byteStr:
    # hex.append\( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()

#    return ''.join(["0x" + "%02X" % ord(x) + ", " for x in byteStr])


def int2hex(intList):
    return ''.join(["0x" + "%02X" % x + ", " for x in intList])


class McuInterpret(threading.Thread):
    def mcuInterpreter(self):  # interpret command and reply

        print("received: {0} {1} {2} ".format(self.ReceivedCorrect, str(self.ThreadID),
                                              str(int2hex(self.ReceivedData))))

        time.sleep(.01)
        if self.ReceivedData[3] == int('1B', 16):  # install mode
            print("install mode".rjust(21))
            if self.ReceivedData[4] == int('01',16):  # install mode on
                print("on")
                time.sleep(1)
                self.generate_command([0x12, 0x03])
            elif self.ReceivedData[4] == int('02', 16):  # install mode off
                print("off")
                self.generate_command([0x12, 0x04])
        # MCU Update
        elif self.ReceivedData[3] == int('11', 16):
            # 4.1.1 Direct DSP access without additional info
            address = self.ReceivedData[5] * 256
            address += self.ReceivedData[6]

            if self.ReceivedData[4] == int('01', 16):  # only dsp addr and bytes
                print("4.1.1 direct dsp command".rjust(21))
                print("Write: address: " + str(address))
                self.Eeprom[address * 4: address * 4 + 4] = [self.ReceivedData[7:11]]
                self.generate_command([0x12, 0x01])
            # 4.1.4 DSP Save Load
            elif self.ReceivedData[4] == int('06', 16):
                print("4.1.4 dsp safe load")
                amount = self.ReceivedData[7]  #number of params(1-5)
                print("Write: amount: " + str(amount) + "address: " + str(address))
                #put data in E2prom

                self.Eeprom[address * 4:address * 4 + amount * 4] = self.ReceivedData[8:8 + amount * 4]

                self.generate_command([0x12, 0x01])
                for z in [self.ReceivedData[8 + x:8 + x + 4] for x in range(amount)]:

                    #n+= z[0] * 256 ** 3
                    n = z[1] * 256 ** 2
                    n += z[2] * 256
                    n += z[3]

                    gain = n / (2 ** 23)
                    if gain > 0:
                        db = 20 * math.log10(gain)
                        print(str(db))
                    else:
                        print("unknown gain value")
            else:
                print("not a valid command")
        elif self.ReceivedData[3] == int('16', 16):
            # 4.3 Routing table update
            print("routing table update received".rjust(21))
            self.generate_command([0x12, 0x01])
        elif self.ReceivedData[3] == int('15', 16):
            # 4.4 Name update
            print("Name update".rjust(21))
            whichName = self.ReceivedData[4]
            if 0 < whichName < 40:
                print("name {0} => {1}".format(whichName, str(self.ReceivedData[5:18])))
                self.generate_command([0x12, 0x01])
            else:
                print("incorrect name addressed")
        elif self.ReceivedData[3] == int('17', 16) and len(self.ReceivedData) > 6:  # 4.5 Preset Select
            print("preset select".rjust(21))
            Preset = self.ReceivedData[4]
            Channel = self.ReceivedData[5]
            print("Channel:{0} - Preset:{1}".format(Channel, Preset))
            if 0x00 < Channel < 385 and 0x00 < Preset < 17:
                print("OK")
                self.generate_command([0x12, 0x01])
            else:
                print("channel or preset out of bounds")
        elif self.ReceivedData[3] == int('19', 16):
            # 4.6 Button or File Programming
            print("button or file programming")
            if len(self.ReceivedData) == 35:
                self.generate_command([0x12, 0x0E])

                print("FirePanel\t\t{0}".format(str(int2hex(self.ReceivedData[6:14]))))
                print("Evacuation Panel\t\t{0}".format(str(int2hex(self.ReceivedData[14:22]))))
                print("Fire Detection\t\t{0}".format(str(int2hex(self.ReceivedData[22:30]))))
            else:
                print("not right length {0}".format(len(self.ReceivedData)))
        elif self.ReceivedData[3] == int('14', 16) and self.bytesToReceive > 5:
            # 4.8 Password sending
            sendpas = self.ReceivedData[5:-1]

            print("password => {0}".format(str(sendpas)).rjust(21))
            if self.ReceivedData[4] == int('01', 16):
                print("send")
                if sendpas == self.password:
                    print("password OK")
                    self.password = sendpas
                    self.generate_command([0x12, 0x01])
                else:
                    print("Wrong password: {0} ! = {1}".format(str(self.password), str(sendpas)))
                    self.generate_command([0x12, 0x05])
            elif self.ReceivedData[4] == int('02', 16):
                print("change")
                self.generate_command([0x12, 0x01])
                self.password = sendpas
            else:
                print("unknown")
        elif self.ReceivedData[3] == int('1C', 16) and self.bytesToReceive > 4:
            # 4.9 Measurement
            print("Measurement")
            if self.ReceivedData[4] == int('01', 16):
                #4.9.1 Calibrate Zone
                print("calibrate zone")
                time.sleep(6)
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('02', 16):
                #4.9.2 Get 1KHz or/and 22 KHz measurement load
                print("22 khz and 1 khz")
                time.sleep(4)
                self.generate_command([0x12, 0x00, 0x3A, 0x00, 0xAC, 0x00, 0x36, 0x00, 0xB9, 0x60, 0x00,
                                      0x00, 0x39, 0x00, 0xAF, 0x00, 0x36, 0x00, 0xB9, 0x60, 0x00, 0x00, 0x74, 0x00,
                                      0x56,
                                      0x00, 0x6B, 0x00, 0x5D, 0x60, 0x00])
            elif self.ReceivedData[4] == int('03', 16):
                #4.9.3 Set Deviation
                print("4.9.3 Set Deviation")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('04', 16):
                #4.9.4 Play test tone
                print("4.9.4 Play test tone")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('05', 16):
                #4.9.5 Activate test mode
                print("4.9.5 Activate test mode")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('06', 16):
                #4.9.6   1 KHz Measurement enable/disable
                print("1 khz measurement")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('07', 16):
                #4.9.7  Set measurement parameters - measurement interval and amount of errors
                print("Set measurement parameters")
                print(str(self.ReceivedData[5:8]))
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('09', 16):
                #4.9.2 Get 1KHz or/and 22 KHz measurement load
                print("Get 1KHz or/and 22 KHz")

            else:
                print("unknown")

        elif self.ReceivedData[3] == int('1D',16) and self.bytesToReceive > 4:
            # 4.10 Get VU meter value
            print("vu received")
            self.db_meter_returned_counter += 1
            feedback = [0x12, 0x06]
            value = [x for x in struct.pack('H', int(math.fabs(math.sin(self.db_meter_returned_counter)) * 1000))[::-1]]
            self.generate_command(feedback + value)

        elif self.ReceivedData[3] == int('10', 16) and self.bytesToReceive > 5:
            # 4.12 Global Unit commands
            print("global unit command".rjust(21))

            if self.ReceivedData[4] == int('01', 16):
                #4.12.1 Calibrate the unit
                print("Calibrate unit")
                time.sleep(5)
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('02', 16):
                #4.12.2 Get installation tree
                print("get installation tree")
                self.generate_command(
                    [0x12, 0x0B, 0x21, 0x42, 0x42, 0x42, 0x42, 0x42, 0x34, 0x24, 0x42, 0x42, 0x42, 0x42, 0x42, 0x42,
                     0x42])

            elif self.ReceivedData[4] == int('04', 16):
                #4.12.4 Get number of tracks from both cards
                print("Sd Message card")
                self.generate_command([0x12, 0x0C, 8, 4])


            elif self.ReceivedData[4] == int('05', 16):
                #4.12.5 Get name of tracks x from card x
                print("Sd Message card name")
                sdcard = self.ReceivedData[5]
                messageN = self.ReceivedData[6]

                self.generate_command([0x12, 0x0b, 0x05,
                                      sdcard + 47,
                                      0x3E, 0x3E, 0x3E,
                                      messageN // 100 % 10 + 48,
                                      messageN // 10 % 10 + 48,
                                      messageN % 10 + 48,
                                      0x33, 0x33, 0x33])  #3 extension
            elif self.ReceivedData[4] == int('06',16):
                print("getE2PROM")
                #offset += self.ReceivedData[5] * 256 ** 3 this bytes is never used as eeprom is 128k
                offset = self.ReceivedData[6] * 256 ** 2
                offset += self.ReceivedData[7] * 256
                offset += self.ReceivedData[8]

                amount = self.ReceivedData[9]

                print("offset = " + str(offset) + " amount = " + str(amount))
                command = [0x12, 0x0E]
                self.generate_command(command + self.Eeprom[offset: offset + amount])

            elif self.ReceivedData[4] == int('0E', 16) or self.ReceivedData[4] == int('08', 16):
                #4.12.8 set eeprom
                #offset += self.ReceivedData[5] * 256 ** 3 this bytes is never used as eeprom is 128k
                offset = self.ReceivedData[6] * 256 ** 2
                offset += self.ReceivedData[7] * 256
                offset += self.ReceivedData[8]

                amount = self.ReceivedData[2] - 10
                print("E2prom Update, amount: " + str(amount) + "offset: " + str(offset))
                #put data in E2prom
                self.Eeprom[offset:offset + amount] = self.ReceivedData[9:amount + 9]

                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('0A', 16):
                print("Set sensitivity")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('0F', 16):
                print("keep alive")
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('0B', 16):
                self.generate_command([0x12, 0x10, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x01, 0x01, 0x01, 0x01])
            elif self.ReceivedData[4] == int('0C',16):
                print("set bose version")
                self.bose_version = self.ReceivedData[5:14]
                self.generate_command([0x12, 0x01])
            elif self.ReceivedData[4] == int('0D', 16):
                print("get bose version")
                self.generate_command([0x12, 0x11] + self.bose_version)
            else:
                print("unknown")

        else:
            print("not known command".rjust(21))  # unknowm

    def isCorrectLength(self, length):
        if len(self.ReceivedData) <= length:
            if len(self.ReceivedData) > 0:
                print("corrupted data: {0}".format(str(self.ReceivedData)))
            return False
        return True

    def checksum(self, arr):
        counter = 0
        for item in arr:
            counter += item
        return counter % 256

    #def getBytesChecksum(self, arr):
    #    counter = 0
    #    for item in arr[0:len(arr) - 1]:
    #        counter += int.from_bytes(item, byteorder='big')
    #    return bytes((counter % 256,))

    # generates command based on protocol byte 4(3) till end
    def generate_command(self, p):
        # deliberately make things difficult. Sometimes I don't respond :p
        # if random.randrange(50) == 9:
        #    return

        #source
        p.insert(0, self.ThreadID)
        #destination
        p.insert(1, 0x81)
        #amount
        p.insert(2, len(p) + 2)
        #checksum
        p += [self.checksum(p)]

        print("writing:{0}".format(str(int2hex(p))))
        self.send_data(p)

    @abc.abstractmethod
    def send_data(self, data):
        raise "this method should be override"

    def insert_into_eeprom(self, offset, data):
        self.Eeprom[offset: offset+len(data)] = data

    def genEeprom(self):
        self.Eeprom = [0 for i in range(131072)]

        # RoutingTable start @0x8000
        for z in range(216):
            x = z * 6 + 0x8000
            self.Eeprom[x] = 0x0F
            self.Eeprom[x + 1] = 0xFF
            self.Eeprom[x + 2] = 0x00
            self.Eeprom[x + 3] = 0x00
            self.Eeprom[x + 4] = 0xFF
            self.Eeprom[x + 5] = 0xFF

        # presetNames
        names = [[62, 62, 62, x // 10 % 10 + 48, x % 10 + 48, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 124]
                 for x in range(39)]

        names_combined = [item for sub_list in names for item in sub_list]
        self.insert_into_eeprom(40960, names_combined)

        #the sd card message positions are downloaded from the eeprom file. This sets their positions
        self.insert_into_eeprom(41984, [x + 1 for x in range(2+8+8+8+4)])

        #ALARM.ALARM_MP_MIC_1_hold
        self.insert_into_eeprom(303 * 4, [0x00, 0x00, 0x01, 0xE0])

        #ALARM.ALARM_MP_MIC_1_decay
        self.insert_into_eeprom(304 * 4, [0x00, 0x00, 0x00,	0x12])

        print("EEPROM data generated")

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.Eeprom = list()
        self.ThreadID = threadID
        self.name = name
        self.genEeprom()

        self.password = [ord(x) for x in [b'5', b'7', b'9', b'A', b'C', b'E']]
        self.bose_version = []
        self.bytesToReceive = 0
        self.ReceivedData = []
        self.stop = 0
        self.ReceivedCorrect = 0
        self.db_meter_returned_counter = 0
        self.exit = False

    def run(self):
        print(self.name + " running")

        while (1):
            if self.exit: return
            self.ReceivedData.clear()
            # if time > 0:
            # print("done: " + str(time) + ", ok: " + str(receivedCorrect))

            while len(self.ReceivedData) <= 3:
                res = self.read_data()
                if res == b'' or res is None:
                    break
                else:
                    self.ReceivedData += res

            if not self.isCorrectLength(3):
                continue
                ## self.receivedData.append(1)

            self.bytesToReceive = self.ReceivedData[2]
            if self.bytesToReceive > 127 or self.bytesToReceive < 5:
                print("not the right amount of bytes:" + str(self.bytesToReceive))
                continue

            while len(self.ReceivedData) <= self.bytesToReceive - 1:
                res = self.read_data()
                if res == b'':
                    break
                else:
                    self.ReceivedData += res
            if len(self.ReceivedData) < 1:
                continue
            if len(self.ReceivedData) != self.bytesToReceive:
                print(
                    "incorrect amount expected:" + str(self.bytesToReceive) + " actual:" + str(len(self.ReceivedData)))
                continue

            if self.ReceivedData[-1] != self.checksum(self.ReceivedData[:-1]):
                print("incorrect checksum: {0}".format(str(self.ReceivedData)))
                continue

            self.ReceivedCorrect += 1

            self.mcuInterpreter()

    @abc.abstractmethod
    def read_data(self):
        raise "this method should be override"


class McuInterpretCom(McuInterpret):
    def __init__(self, threadID, name, port):
        super().__init__(threadID, name)
        self.ser = serial.Serial(port, 38400, timeout=1)


    def send_data(self, data):
        self.ser.write(data)

    def read_data(self):
        return self.ser.read()


class McuInterpretNet(McuInterpret):
    def __init__(self, threadID, name, conn):
        super().__init__(threadID, name)
        self.conn = conn

    def send_data(self, data):
        conn.sendall(bytes(data))

    def read_data(self):
        try:
            data = self.conn.recv(1024)
        except socket.error as message:
            print("connection closed: {0} detail: {1}".format(str(message[0]), str(message[1])))
            self.conn.close()
            self.exit = True
            return None
        return data

mcuId = 1
for cPort in [11, 13, 15]:
   McuInterpretCom(mcuId, "thread" + str(cPort), cPort).start()
   mcuId += 1

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('', 1002))
    print('socket bind complete')
except socket.error as inst:
    print('socket bind failed. No network available:', inst)
else:
    s.listen(10)
    print('socket now listening')
    while 1:
        conn, address = s.accept()
        print('Connected with ' + address[0] + ':' + str(address[1]))
        last_ip_digit = int(conn.getsockname()[0].split('.')[3])
        McuInterpretNet(last_ip_digit, "mcu", conn).start()