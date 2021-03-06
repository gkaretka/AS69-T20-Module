import base64
import hashlib
import serial
import sys
import threading
import time
import binascii
from Crypto import Random
from Crypto.Cipher import AES

KEY = "KEY"
PORT = sys.argv[1]
MSG_END = "\n"

CONFIG = False
if len(sys.argv) > 2:
    if sys.argv[2] == "config":
        CONFIG = True


class AESCipher(object):

    def __init__(self, key):
        self.bs = 16
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]


class AS69Operator:
    cypher = AESCipher(KEY)
    ser = serial.Serial()

    def __init__(self):
        self.init()

        if CONFIG:
            self.get_parameters()
            self.set_default_parameters()
            self.get_parameters()

        self.print_received()
        self.write_received()

    def init(self):
        self.ser.baudrate = 9600
        self.ser.port = PORT
        self.ser.open()

    def send_string(self, string):
        string = self.cypher.encrypt(string)
        self.ser.write(string+MSG_END.encode())

    def set_default_parameters(self):
        time.sleep(0.5)
        print("SETTING DEFAULT PARAMETERS")
        cmd = bytes.fromhex("C01234180043")
        self.ser.write(cmd)
        print("STATUS:" + self.ser.read(4).decode())
        time.sleep(0.5)

    def get_parameters(self):
        print("CURRENT PARAMETERS")
        cmd = bytes.fromhex("C1C1C1")
        self.ser.write(cmd)
        print(binascii.hexlify(self.ser.read(6)))

    def read_packet(self):
        string = ""
        end_counter = 0

        while end_counter < 1:
            helper = self.ser.read_all().decode()
            if helper == '\n':
                end_counter = end_counter + 1
            else:
                string += helper

        return self.cypher.decrypt(bytes(string.encode()))

    def _print_received(self):
        while True:
            time.sleep(0.5)
            string = self.read_packet()
            if string:
                print(string)

    def _write_received(self):
        while True:
            msg = repr(input())
            self.send_string(string=msg)

    def write_received(self):
        thread = threading.Thread(target=self._write_received, args=())
        thread.daemon = True
        thread.start()

    def print_received(self):
        thread = threading.Thread(target=self._print_received, args=())
        thread.daemon = True
        thread.start()


operator = AS69Operator()

if not CONFIG:
    while True:
        time.sleep(0.5)
