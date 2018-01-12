# -*- encoding: utf-8 -*-
#
# Grasso - a FAT filesystem parser
#
# Copyright 2011 Emanuele Aina <em@nerd.ocracy.org>
#
# Released under the term of a MIT-style license, see LICENSE
# for details.

from struct import unpack

class ExtendedBIOSParameterBlock32(object):
    length = 476
    unpacker = "<IHHIHH12sBBB4s11s8s420sH"
    def __init__(self, filesystem):
        self.filesystem = filesystem
        self.offset = self.filesystem.source.tell()
        data = unpack(self.unpacker, self.filesystem.source.read(self.length))
        self.sector_per_fat = data[0]
        self.mirroring_flags = data[1]
        self.version = data[2]
        self.root_directory_cluster_number = data[3]
        self.file_system_information_sector_number = data[4]
        self.backup_boot_sector_number = data[5]
        self.reserved = list(data[6])
        self.physical_drive_number = data[7]
        self.reserved_flags = data[8]
        self.extended_boot_signature = data[9]
        self.volume_id = list(data[10])
        self.volume_label = data[11]
        self.file_system_type = data[12]
        self.boot_code = data[13]
        self.signature = data[14]

    def __repr__(self):
        return "ExtendedBIOSParameterBlock32(\n"            \
            " offset=%d,\n"                                 \
            " length=%d,\n"                                 \
            " sector_per_fat=%d,\n"                         \
            " mirroring_flags=%d,\n"                        \
            " version=%d,\n"                                \
            " root_directory_cluster_number=%d,\n"          \
            " file_system_information_sector_number=%d,\n"  \
            " backup_boot_sector_number=%d,\n"              \
            " reserved=%s,\n"                               \
            " physical_drive_number=%d,\n"                  \
            " reserved_flags=%d,\n"                         \
            " extended_boot_signature=%d,\n"                \
            " volume_id=%s,\n"                              \
            " volume_label='%s',\n"                         \
            " file_system_type='%s',\n"                     \
            " boot_code=[...],\n"                           \
            " signature=%d,\n"                              \
            ")" % (
            self.offset,
            self.length,
            self.sector_per_fat,
            self.mirroring_flags,
            self.version,
            self.root_directory_cluster_number,
            self.file_system_information_sector_number,
            self.backup_boot_sector_number,
            self.reserved,
            self.physical_drive_number,
            self.reserved_flags,
            self.extended_boot_signature,
            self.volume_id,
            self.volume_label,
            self.file_system_type,
            self.signature
            )

class FileSystemInformationSector32(object):
    length = 512
    unpacker = "<4s480s4sII12s4s"
    def __init__(self, filesystem):
        self.filesystem = filesystem
        self.offset = self.filesystem.source.tell()
        data = unpack(self.unpacker, self.filesystem.source.read(self.length))
        self.signature_1 = list(data[0])
        self.reserved_1 = list(data[1])
        self.signature_2 = list(data[2])
        self.free_cluster_count = data[3]
        self.most_recent_allocated_cluster_number = data[4]
        self.reserved_2 = list(data[5])
        self.signature_3 = list(data[6])

    def __repr__(self):
        return "FileSystemInformationSector32(\n"           \
            " offset=%d,\n"                                 \
            " length=%d,\n"                                 \
            " signature_1=%s,\n"                            \
            " reserved_1=[...],\n"                          \
            " signature_2=%s,\n"                            \
            " free_cluster_count=%d,\n"                     \
            " most_recent_allocated_cluster_number=%d,\n"   \
            " reserved_2=%s,\n"                             \
            " signature_3=%s,\n"                            \
            ")" % (
            self.offset,
            self.length,
            self.signature_1,
            self.signature_2,
            self.free_cluster_count,
            self.most_recent_allocated_cluster_number,
            self.reserved_2,
            self.signature_3
            )

class FAT32(object):
    def __init__(self, filesystem, length):
        self.length = length
        self.filesystem = filesystem
        self.offset = self.filesystem.source.tell()
        source = self.filesystem.source
        self.media_descriptor = unpack('<B', source.read(1))[0]
        self.ones = unpack('<BBB', source.read(3))
        self.end_of_cluster = unpack('<I', source.read(4))[0]
        self.next_clusters = {}
        self.bad_clusters = {}
        entries = self.length/4
        for i in range(2, entries):
            v = unpack('<I', source.read(4))[0] & 0x0FFFFFFF
            if not v:
                continue
            if 0x00000002 <= v and v <= 0x0FFFFFEF:
                self.next_clusters[i] = v
            if 0x0FFFFFF8 <= v and v <= 0x0FFFFFFF:
                self.next_clusters[i] = None
            if v == 0x0FFFFFF7:
                self.bad_clusters[i] = v

    def get_chain(self, cluster):
        c = cluster
        while c:
            yield c
            c = self.next_clusters[c]

    def __repr__(self):
        return "FAT32(\n"               \
            " offset=%d,\n"             \
            " length=%d,\n"             \
            " media_descriptor=%d,\n"   \
            " end_of_cluster=0x%X,\n"   \
            " next_clusters=[...],\n"   \
            " bad_clusters=[...],\n"    \
            ")" % (
            self.offset,
            self.length,
            self.media_descriptor,
            self.end_of_cluster,
            )
