# This file is part of Scapy
# See http://www.secdev.org/projects/scapy for more information
# Copyright (C) Nils Weiss <nils@we155.de>
# This program is published under a GPLv2 license

# scapy.contrib.description = Native CANSocket
# scapy.contrib.status = loads

"""
NativeCANSocket.
"""

import struct
import socket
import time
from scapy.config import conf
from scapy.supersocket import SuperSocket
from scapy.error import Scapy_Exception, warning
from scapy.layers.can import CAN
from scapy.packet import Padding
from scapy.arch.linux import get_last_packet_timestamp

conf.contribs['NativeCANSocket'] = {'channel': "can0"}

CAN_FRAME_SIZE = 16
CAN_INV_FILTER = 0x20000000


class NativeCANSocket(SuperSocket):
    desc = "read/write packets at a given CAN interface using PF_CAN sockets"
    nonblocking_socket = True

    def __init__(self, channel=None, receive_own_messages=False,
                 can_filters=None, remove_padding=True, basecls=CAN, **kwargs):
        bustype = kwargs.pop("bustype", None)
        if bustype and bustype != "socketcan":
            warning("You created a NativeCANSocket. "
                    "If you're providing the argument 'bustype', please use "
                    "the correct one to achieve compatibility with python-can"
                    "/PythonCANSocket. \n'bustype=socketcan'")

        self.basecls = basecls
        self.remove_padding = remove_padding
        self.channel = conf.contribs['NativeCANSocket']['channel'] if \
            channel is None else channel
        self.ins = socket.socket(socket.PF_CAN,
                                 socket.SOCK_RAW,
                                 socket.CAN_RAW)
        try:
            self.ins.setsockopt(socket.SOL_CAN_RAW,
                                socket.CAN_RAW_RECV_OWN_MSGS,
                                struct.pack("i", receive_own_messages))
        except Exception as exception:
            raise Scapy_Exception(
                "Could not modify receive own messages (%s)", exception
            )

        if can_filters is None:
            can_filters = [{
                "can_id": 0,
                "can_mask": 0
            }]

        can_filter_fmt = "={}I".format(2 * len(can_filters))
        filter_data = []
        for can_filter in can_filters:
            filter_data.append(can_filter["can_id"])
            filter_data.append(can_filter["can_mask"])

        self.ins.setsockopt(socket.SOL_CAN_RAW,
                            socket.CAN_RAW_FILTER,
                            struct.pack(can_filter_fmt, *filter_data))

        self.ins.bind((self.channel,))
        self.outs = self.ins

    def recv(self, x=CAN_FRAME_SIZE):
        try:
            pkt, sa_ll = self.ins.recvfrom(x)
        except BlockingIOError:  # noqa: F821
            warning("Captured no data, socket in non-blocking mode.")
            return None
        except socket.timeout:
            warning("Captured no data, socket read timed out.")
            return None
        except OSError:
            # something bad happened (e.g. the interface went down)
            warning("Captured no data.")
            return None

        # need to change the byte order of the first four bytes,
        # required by the underlying Linux SocketCAN frame format
        if not conf.contribs['CAN']['swap-bytes']:
            pkt = struct.pack("<I12s", *struct.unpack(">I12s", pkt))

        len = pkt[4]
        canpkt = self.basecls(pkt[:len + 8])
        canpkt.time = get_last_packet_timestamp(self.ins)
        if self.remove_padding:
            return canpkt
        else:
            return canpkt / Padding(pkt[len + 8:])

    def send(self, x):
        try:
            if hasattr(x, "sent_time"):
                x.sent_time = time.time()

            # need to change the byte order of the first four bytes,
            # required by the underlying Linux SocketCAN frame format
            bs = bytes(x)
            if not conf.contribs['CAN']['swap-bytes']:
                bs = bs + b'\x00' * (CAN_FRAME_SIZE - len(bs))
                bs = struct.pack("<I12s", *struct.unpack(">I12s", bs))
            return SuperSocket.send(self, bs)
        except socket.error as msg:
            raise msg

    def close(self):
        self.ins.close()


CANSocket = NativeCANSocket
