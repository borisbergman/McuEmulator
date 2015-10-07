import socket
import time
import serial
import Interpreter


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




class McuInterpretCom(Interpreter.Interpreter):
    def __init__(self, threadID, name, port):
        super().__init__(threadID, name)
        self.ser = serial.Serial(port, 38400, timeout=1)


    def send_data(self, data):
        self.ser.write(data)

    def read_data(self):
        return self.ser.read()


class McuInterpretNet(Interpreter.Interpreter):
    def __init__(self, threadID, name, conn):
        super().__init__(threadID, name)
        self.conn = conn

    def send_data(self, data):
        conn.sendall(bytes(data))
        #conn.close()


    def read_data(self):
        try:
            data = self.conn.recv(1024)
        except socket.error:
            print("connection closed")
            self.conn.close()
            self.exit = True
            return None
        return data

#mcuId = 1
#for cPort in [5, 7, 9]:
#   McuInterpretCom(mcuId, "thread" + str(cPort), cPort).start()
#   mcuId += 1

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
        if(last_ip_digit) > 31:
            last_ip_digit = 2

        McuInterpretNet(last_ip_digit, "mcu", conn).start()