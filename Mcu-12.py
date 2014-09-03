import serial
import threading
import time
from threading import Timer
import math
import struct
import binascii
import random
from array import array

def ByteToHex(byteStr):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """

    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #
    #    hex = []
    #    for aChar in byteStr:
    #        hex.append\( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()

    return ''.join( ["0x" + "%02X" % ord(x) + ", " for x in byteStr])

def IntToHex(intList):
    return ''.join( ["0x" + "%02X" % x + ", " for x in intList])



class McuInterpret(threading.Thread):
    def mcuInterpreter(self): #interpret command and reply
        print("received: {0} {1} {2} ".format(self.receivedCorrect, str(self.threadID), str(ByteToHex(self.receivedData)) ))

        time.sleep(.01)
        if self.receivedData[3] == bytes.fromhex('1B'):     #install mode
            print("install mode".rjust(21))
            if self.receivedData[4] == bytes.fromhex('01'): # install mode on
                print("on".rjust(22))
                time.sleep(1)
                self.generateCommand([0x12,0x03])
            elif self.receivedData[4] == bytes.fromhex('02'): # install mode off
                print("off".rjust(22))
                self.generateCommand([0x12,0x04])
        #MCU Update
        elif self.receivedData[3] == bytes.fromhex('11'):
            # 4.1.1 Direct DSP access without additional info
            address = struct.unpack('H',  b''.join(reversed(self.receivedData[5:7])))[0]
            if self.receivedData[4] == bytes.fromhex('01'): #only dsp addr and bytes
                print("4.1.1 direct dsp command".rjust(21))
                print("Write: address: " + str(address))
                self.EEPROM[address*4 : address*4 + 4] = [struct.unpack('B', x)[0] for x in self.receivedData[7:11]]
                self.generateCommand([0x12,0x01])
            #4.1.4 DSP Save Load
            elif self.receivedData[4] == bytes.fromhex('06'):
                print("4.1.4 dsp safe load")
                amount = struct.unpack('B', self.receivedData[7])[0] #number of params(1-5)
                print("Write: amount: " + str(amount) + "address: " + str(address) )
                #put data in E2prom

                print ("EPL1: " + str(len(self.EEPROM)))
                self.EEPROM[address*4:address*4 + amount * 4] = [struct.unpack('B', x)[0] for x in self.receivedData[8:8+amount*4]]
                print ("EPL2: " + str(len(self.EEPROM)))

                self.generateCommand([0x12,0x01])
                for z in [self.receivedData[8+x:8+x+4] for x in range(amount)]:
                    n = struct.unpack('I', b''.join(reversed(z)))[0]
                    gain = n/(2**23)
                    if gain > 0:
                        db = 20 * math.log10(gain)
                        print(str(db))
                    else:
                        print("unknown gain value")
            else:
                print("not a valid command".rjust(22))
        elif self.receivedData[3] == bytes.fromhex('16'):
            #4.3 Routing table update
            print("routing table update received".rjust(21))
            self.generateCommand([0x12,0x01])
        elif self.receivedData[3] == bytes.fromhex('15'):
            #4.4 Name update
            print("Name update".rjust(21))
            whichName = int.from_bytes(self.receivedData[4], byteorder='big')
            if 0 < whichName < 40:
                print("name {0} => {1}".format(whichName, str(self.receivedData[5:18]).rjust(22)))
                self.generateCommand([0x12,0x01])
            else:
                print("incorrect name addressed")
        elif self.receivedData[3] == bytes.fromhex('17') and len(self.receivedData) > 6:        #4.5 Preset Select
            print("preset select".rjust(21))
            Preset = int.from_bytes(self.receivedData[4], byteorder='big')
            Channel = int.from_bytes(self.receivedData[5], byteorder='big')
            print("Channel:{0} - Preset:{1}".format(Channel, Preset))
            if 0x00 < Channel < 385 and 0x00 < Preset < 17:
                print("OK".rjust(22))
                self.generateCommand([0x12,0x01])
            else:
                print("channel or preset out of bounds".rjust(22))
        elif self.receivedData[3] == bytes.fromhex('19'):
            #4.6 Button or File Programming
            print("button or file programming".rjust(21))
            if len(self.receivedData) == 35 :
                self.generateCommand([0x12,0x0E,0xFF,0xFF,0xFF,0xFF,0x01,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,
                                      0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x01,0xFF,0xFF,0xFF,0xFF])
                print("alarm {0}".format(self.receivedData[4:12]))
                print("alert {0}".format(self.receivedData[12:20]))
                print("fds {0}".format(self.receivedData[20:28]))
                print("preann {0}".format(self.receivedData[28:32]))
            else:
                print("not right length {0}".format(len(self.receivedData)) )
        elif self.receivedData[3] == bytes.fromhex('14') and self.bytesToReceive > 5:
            #4.8 Password sending
            sendpas = self.receivedData[5:len(self.receivedData)-1]

            print("password => {0}".format(str(sendpas)).rjust(21))
            if self.receivedData[4] == bytes.fromhex('01'):
                print("send".rjust(22))
                if sendpas == self.password:
                    print("password OK")
                    self.password = sendpas
                    self.generateCommand([0x12,0x01])
                else:
                    print("Wrong password: {0} ! = {1}".format(str(self.password), str(sendpas)))
                    self.generateCommand([0x12,0x05])
            elif self.receivedData[4] == bytes.fromhex('02'):
                print("change".rjust(22))
                self.generateCommand([0x12,0x01])
                self.password = sendpas
            else:
                print("unknown".rjust(22))
        elif self.receivedData[3] == bytes.fromhex('1C') and self.bytesToReceive > 4:
            #4.9 Measurement
            print("Measurement".rjust(21))
            if self.receivedData[4] == bytes.fromhex('01'):
                #4.9.1 Calibrate Zone
                print("calibrate zone".rjust(22))
                time.sleep(6)
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('02'):
                #4.9.2 Get 1KHz or/and 22 KHz measurment load
                print("22 khz and 1 khz".rjust(22))
                time.sleep(4)
                self.generateCommand([0x12,0x00,0x3A,0x00,0xAC,0x00,0x36,0x00,0xB9,0x60,0x00,
                                      0x00,0x39,0x00,0xAF,0x00,0x36,0x00,0xB9,0x60,0x00,0x00,0x74,0x00,0x56,
                                      0x00,0x6B,0x00,0x5D,0x60,0x00])
            elif self.receivedData[4] == bytes.fromhex('03'):
                #4.9.3 Set Deviation
                print("set deviation".rjust(22))
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('04'):
                #4.9.4 Play test tone
                print("play testtone".rjust(22))
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('05'):
                #4.9.5 Activate Testmode
                print("testmode".rjust(22))
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('06'):
                #4.9.6   1 KHz Measurement enable/disable
                print("1 khz measurement".rjust(22))
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('07'):
                #4.9.7  Low impedance on/off
                print("low impedance".rjust(22))
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('09'):
                #4.9.2 Get 1KHz or/and 22 KHz measurement load
                print("Get 1KHz or/and 22 KHz")

            else:
                print("unknown")

        elif self.receivedData[3] == bytes.fromhex('1D') and self.bytesToReceive > 4:
            #4.10 Get VU meter value
            print("vu received".rjust(21))
            self.generateCommand([0x12,0x06,0x00,0x40])

        elif self.receivedData[3] == bytes.fromhex('1e') and len(self.bytesToReceive) > 4:
            #4.11 GUI keep alive
            self.generateCommand([0x12,0x01])

        elif self.receivedData[3] == bytes.fromhex('10') and self.bytesToReceive > 5:
            #4.12 Global Unit commands
            print("global unit command".rjust(21))

            if self.receivedData[4] == bytes.fromhex('01'):
                #4.12.1 Calibrate the unit
                print("Calibrate unit".rjust(22))
                time.sleep(5)
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('02'):
                #4.12.2 Get installation tree
                print("get installation tree".rjust(22))
                self.generateCommand([0x12,0x0B,0x21,0x00,0x00,0x00,0x42,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x02,0x00])

            elif self.receivedData[4] == bytes.fromhex('04'):
                #4.12.4 Get number of tracks from both cards
                print("Sd Message card")
                self.generateCommand([0x12,0x0C,8,4])


            elif self.receivedData[4] == bytes.fromhex('05'):
                #4.12.5 Get name of tracks x from card x
                print("Sd Message card name")
                sdcard =struct.unpack('B', self.receivedData[5])[0]
                messageN = struct.unpack('B', self.receivedData[6])[0]

                self.generateCommand([0x12,0x0b,0x05,
               sdcard + 47,
               0x3E,0x3E,0x3E,
               messageN // 100 % 10 + 48,
               messageN // 10 % 10 + 48,
               messageN % 10 + 48,
                0x33,0x33,0x33]) #3 extension
            elif self.receivedData[4] == bytes.fromhex('06'):
                print("getE2PROM")

                amount = struct.unpack('B', self.receivedData[9])[0]
                offset = struct.unpack('I', b''.join(reversed(self.receivedData[5:9])))[0]

                print("offset = " + str(offset) + " amount = " + str(amount))
                command = [18, 14]
                command.extend(self.EEPROM[offset: offset+amount])
                self.generateCommand(command)
            elif self.receivedData[4] == bytes.fromhex('08'):
                #4.12.8 set eeprom
                offset = struct.unpack('I',  b''.join(reversed(self.receivedData[5:9])))[0]
                amount = struct.unpack('B', self.receivedData[9])[0]
                print("E2prom Write, amount: " + str(amount) + "offset: " + str(offset) )
                #put data in E2prom
                self.EEPROM[offset:offset + amount] = [struct.unpack('B', x)[0] for x in self.receivedData[8:amount+8]]
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('0A'):
                print ("Set sensitivity")
                self.generateCommand([0x12,0x01])
            elif self.receivedData[4] == bytes.fromhex('0B'):
                self.generateCommand([0x12,0x10,0x03,0x03,0x03,0x03,0x03,0x03,0x03,0x03,0x01,0x01,0x01,0x01])
            else:
                print("unknown")
        else:
            print("not known command".rjust(21))  #unknowm

    def isCorrectLength(self, length):
        if len(self.receivedData) <= length:
            if len(self.receivedData) > 0:
                print("corrupted data: {0}".format(str(self.receivedData)))
            return False
        return True

    def getChecksum(self,arr):
        counter = 0
        for item in arr:
            counter += item
        return counter % 256

    def getBytesChecksum(self,arr):
        counter = 0
        for item in arr[0:len(arr)-1]:
            counter += int.from_bytes(item, byteorder='big')
        return bytes((counter % 256,))

    #generates command based on protocol byte 4(3) till end
    def generateCommand(self,p):
        #source
        p.insert(0, self.threadID)
        #destination
        p.insert(1, 0x81)
        #amount
        p.insert(2, len(p) + 2)
        #checksum
        p.append(self.getChecksum(p))

        # if 1:
        #     self.ser.write(p[0:3])
        #     time.sleep(0.1)
        #     self.ser.write(p[3:len(p)])

        print("writing:{0}".format(str(IntToHex(p))))
        self.ser.write(p)

    def genEeprom(self):
        for i in range(131072):
            self.EEPROM.append(0)

        #RoutingTable start @0x8000
        for z in range(216):
            x = z*6+0x8000
            self.EEPROM[x] = 0x0
            self.EEPROM[x+1] = 0xF
            self.EEPROM[x+2] = 0x0
            self.EEPROM[x+3] = 0x0
            self.EEPROM[x+4] = 0xF
            self.EEPROM[x+5] = 0xF

        #presetNames
        offset = 40960
        amount = 39 * 16

        names = []
        for q in [[62,62,62, x // 10 % 10 + 48, x % 10 + 48,60,60,60,60,60,60,60,60,60,60,124] for x in range(39)]:
            names.extend(q)

        self.EEPROM[offset: offset + amount] = names

        sdmessagesoffset = 41984;
        self.EEPROM[sdmessagesoffset: sdmessagesoffset + 20] = [x+1 for x in range(20)]
        self.EEPROM[sdmessagesoffset + 20: sdmessagesoffset + 30] = [0x01 for x in range(10)]

        print("EEPROM data generated")

    def __init__(self, threadID, name, port):
        threading.Thread.__init__(self)
        self.EEPROM = list()
        self.threadID = threadID
        self.name = name
        self.genEeprom()

        self.password = [b'5', b'7', b'9', b'A', b'C', b'E']

        self.bytesToReceive = 0
        self.receivedData = []
        self.stop = 0
        self.receivedCorrect = 0


        self.ser = serial.Serial(port, 38400, timeout=1)

    def run(self):
        print (self.name + " running")

        while(1):
            self.receivedData.clear()
            #if time > 0:
            #    print("done: " + str(time) + ", ok: " + str(receivedCorrect))

            while len(self.receivedData) <= 3:
                res =self.ser.read()
                if(res == b''):
                    break
                else:
                    self.receivedData.append(res)

            if not self.isCorrectLength(3):
                continue
               ## self.receivedData.append(1)

            self.bytesToReceive = int.from_bytes(self.receivedData[2], byteorder='big')
            if(self.bytesToReceive > 127 or self.bytesToReceive < 5):
                print("not the right amount of bytes:"+ str(self.bytesToReceive))
                continue

            while len(self.receivedData) <= self.bytesToReceive -1:
                res =self.ser.read()
                if(res == b''):
                    break
                else:
                    self.receivedData.append(res)
            if len(self.receivedData) < 1:
                continue
            if len(self.receivedData) != (self.bytesToReceive):
                print("incorrect amount expected:" + str(self.bytesToReceive) + " actual:" + str(len(self.receivedData)))
                continue

            if self.receivedData[len(self.receivedData) -1] != self.getBytesChecksum(self.receivedData):
                print("incorrect checksum:" + str(self.receivedData[len(self.receivedData) -1]) + "!=" + str(self.getBytesChecksum(self.receivedData)))
                continue
            ##print(str(int.from_bytes(self.receivedData[len(self.receivedData) -1], byteorder='big') == 1)  + "dddl")
            ##print (str(self.getChecksum(self.receivedData)) + "lll")

            self.receivedCorrect+=1
            #self.StopStopListening()


            self.mcuInterpreter()


class Hawk(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        print ("lala")
    def run(self):
        print ("run")


#p = McuInterpret(1)
mcuId = 1
for cPort in [1, 9, 11, 13, 15, 17, 19, 21]:
    McuInterpret(mcuId, "thread" + str(cPort), cPort).start()
    mcuId += 1

#thread1 = Hawk()
#thread2 = Hawk()

#thread1.start()
#thread2.start()
