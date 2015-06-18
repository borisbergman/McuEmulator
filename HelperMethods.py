__author__ = 'asuspc'


def int2hex(intList):
    return ''.join(["0x" + "%02X" % x + ", " for x in intList])
