# -*- encoding: utf-8 -*-
#
# Grasso - a FAT filesystem parser
#
# Copyright 2011 Emanuele Aina <em@nerd.ocracy.org>
#
# Released under the term of a MIT-style license, see LICENSE
# for details.

from struct import unpack

class ExtendedBIOSParameterBlock16(object):
    length = 476
    unpacker = "<BBB4s11s8s448sH"
    def __init__(self, filesystem):
        self.filesystem = filesystem
        self.offset = self.filesystem.source.tell()
        data = unpack(self.unpacker, self.filesystem.source.read(self.length))
        self.physical_drive_number = data[0]
        self.reserved_flags = data[1]
        self.extended_boot_signature = data[2]
        self.volume_id = data[3]
        self.volume_label = data[4]
        self.file_system_type = data[5]
        self.boot_code = data[6]
        self.signature = data[7]
