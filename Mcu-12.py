import socket

import Interpreter
from multiprocessing import Process

class McuInterpretCom(Interpreter.Interpreter):
    def __init__(self, threadID, name, port):
        super().__init__(threadID, name)
        self.ser = serial.Serial(port, 38400, timeout=1)


    def send_data(self, data):
        self.ser.write(data)

    def read_data(self):
        return self.ser.read()


class McuInterpretNet(Interpreter.Interpreter):
    def __init__(self, threadid, name, conn):
        super().__init__(threadid, name)
        self.conn = conn

    def send_data(self, data):
        if conn:
            conn.sendall(bytes(data))
            peer = self.conn.getpeername()
            print("Wrote to: " + str(peer[0]) + ":" + str(peer[1]))

    def read_data(self):
        try:
            data = self.conn.recv(1024)
        except socket.error:
            print("connection closed")
            self.conn.close()
            self.exit = True
            return None
        return data

while 1:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 1002))
        s.listen(5)
        print('socket bind complete')
    except socket.error as inst:
        print('socket bind failed. No network available:', inst)

    print('socket now listening')
    conn, address = s.accept()
    print('Connected with ' + address[0] + ':' + str(address[1]))
    last_ip_digit = int(conn.getsockname()[0].split('.')[3])
    if 31 < last_ip_digit:
        last_ip_digit = 2

    threat = McuInterpretNet(last_ip_digit, "mcu", conn)
    threat.start()

