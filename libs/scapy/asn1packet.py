# This file is part of Scapy
# See http://www.secdev.org/projects/scapy for more information
# Copyright (C) Philippe Biondi <phil@secdev.org>
# This program is published under a GPLv2 license

"""
ASN.1 Packet

Packet holding data in Abstract Syntax Notation (ASN.1).
"""

from __future__ import absolute_import
from scapy.base_classes import Packet_metaclass
from scapy.packet import Packet
import scapy.modules.six as six


class ASN1Packet_metaclass(Packet_metaclass):
    def __new__(cls, name, bases, dct):
        if dct["ASN1_root"] is not None:
            dct["fields_desc"] = dct["ASN1_root"].get_fields_list()
        return super(ASN1Packet_metaclass, cls).__new__(cls, name, bases, dct)


class ASN1_Packet(six.with_metaclass(ASN1Packet_metaclass, Packet)):
    ASN1_root = None
    ASN1_codec = None

    def self_build(self):
        if self.raw_packet_cache is not None:
            return self.raw_packet_cache
        return self.ASN1_root.build(self)

    def do_dissect(self, x):
        return self.ASN1_root.dissect(self, x)
