# -*- encoding: utf-8 -*-
#
# Grasso - a FAT filesystem parser
#
# Copyright 2011 Emanuele Aina <em@nerd.ocracy.org>
#
# Released under the term of a MIT-style license, see LICENSE
# for details.

import math, io, pprint
from struct import unpack
from .util import FragmentInfo, FragmentedIO

class BootSector(object):
    length = 36
    unpacker = "<3s8sHBHBHHBHHHLL"
    def __init__(self, filesystem):
        self.filesystem = filesystem
        self.offset = self.filesystem.source.tell()
        data = unpack(self.unpacker, self.filesystem.source.read(self.length))
        self.jump = list(data[0])
        self.oem = data[1]
        self.bytes_per_sector = data[2]
        self.sectors_per_cluster = data[3]
        self.reserved_sector_count = data[4]
        self.fat_count = data[5]
        self.max_root_entries_fat16 = data[6]
        self.total_sectors_fat16 = data[7]
        self.media_descriptor = data[8]
        self.sectors_per_fat_fat16 = data[9]
        self.sectors_per_track = data[10]
        self.head_count = data[11]
        self.hidden_sector_count = data[12]
        self.total_sectors_fat32 = data[13]

    @property
    def total_sectors(self):
        return self.total_sectors_fat16 or self.total_sectors_fat32 or 0

    @property
    def type(self):
        if self.total_sectors_fat32:
            return 'FAT32'
        elif self.total_sectors_fat16 >= 4085:
            return 'FAT16'
        else:
            return 'FAT16'

    @property
    def bytes_per_cluster(self):
        return self.bytes_per_sector * self.sectors_per_cluster

    def __repr__(self):
        return "BootSector(\n"              \
            " offset=%d,\n"                 \
            " length=%d,\n"                 \
            " jump=%s,\n"                   \
            " oem='%s',\n"                  \
            " bytes_per_sector=%d,\n"       \
            " sectors_per_cluster=%d,\n"    \
            " reserved_sector_count=%d,\n"  \
            " fat_count=%d,\n"              \
            " max_root_entries_fat16=%d,\n" \
            " total_sectors_fat16=%d,\n"    \
            " media_descriptor=%s,\n"       \
            " sectors_per_fat_fat16=%d,\n"  \
            " sectors_per_track=%d,\n"      \
            " head_count=%d,\n"             \
            " hidden_sector_count=%d,\n"    \
            " total_sectors_fat32=%d,\n"    \
            " total_sectors=%d,\n"          \
            " type=%s,\n"                   \
            " bytes_per_cluster=%d,\n"      \
            ")" % (
            self.offset,
            self.length,
            self.jump,
            self.oem,
            self.bytes_per_sector,
            self.sectors_per_cluster,
            self.reserved_sector_count,
            self.fat_count,
            self.max_root_entries_fat16,
            self.total_sectors_fat16,
            self.media_descriptor,
            self.sectors_per_fat_fat16,
            self.sectors_per_track,
            self.head_count,
            self.hidden_sector_count,
            self.total_sectors_fat32,
            self.total_sectors,
            self.type,
            self.bytes_per_cluster
            )

class DirectoryEntry(object):
    READONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    LABEL = 0x08
    DIRECTORY = 0x10
    ARCHIVE = 0x20
    LONGFILENAME = READONLY | HIDDEN | SYSTEM | LABEL

    length = 32
    unpacker = "<8s3sBBBHHHHHHHI"
    def __init__(self, filesystem, raw):
        self.filesystem = filesystem
        data = unpack(self.unpacker, raw)
        self.dos_file_name_flagged = data[0]
        self.dos_file_extension = data[1]
        self.file_attributes = data[2]
        self.reserved = data[3]
        self.create_time_fine = data[4]
        self.create_time = data[5]
        self.create_date = data[6]
        self.last_access_date = data[7]
        self.ea_index_fat16 = data[8]
        self.first_cluster_number_high_fat32 = data[8]
        self.modified_time = data[9]
        self.modified_date = data[10]
        self.first_cluster_number_fat16 = data[11]
        self.first_cluster_number_low_fat32 = data[11]
        self.file_size = data[12]
        self.long_file_name_entries = []

    @property
    def first_cluster_number_fat32(self):
        return self.first_cluster_number_high_fat32 << 16 | self.first_cluster_number_low_fat32

    @property
    def first_cluster_number(self):
        if self.filesystem.type == 'FAT32':
            return self.first_cluster_number_fat32
        else:
            return self.first_cluster_number_fat16

    @property
    def long_file_name(self):
        if not self.long_file_name_entries:
            return None
        r = ''
        for n in reversed(self.long_file_name_entries):
            r += n.name
        return r

    @property
    def is_available(self):
        return ord(self.dos_file_name_flagged[0]) == 0

    @property
    def is_dot(self):
        return ord(self.dos_file_name_flagged[0]) == 0x2E

    @property
    def is_deleted(self):
        return ord(self.dos_file_name_flagged[0]) == 0xE5

    @property
    def dos_file_name(self):
        n = self.dos_file_name_flagged
        if ord(n[0]) == 0:
            return None
        if ord(n[0]) == 0x05:
            n[0] = chr(0xE5)
        return n.rstrip(' ')

    @property
    def is_readonly(self):
        return bool(self.file_attributes & DirectoryEntry.READONLY)

    @property
    def is_hidden(self):
        return bool(self.file_attributes & DirectoryEntry.HIDDEN)

    @property
    def is_system(self):
        return bool(self.file_attributes & DirectoryEntry.SYSTEM)

    @property
    def is_label(self):
        return bool(self.file_attributes & DirectoryEntry.LABEL)

    @property
    def is_directory(self):
        return bool(self.file_attributes & DirectoryEntry.DIRECTORY)

    @property
    def is_archive(self):
        return bool(self.file_attributes & DirectoryEntry.ARCHIVE)

    def __repr__(self):
        return self.__class__.__name__ +"(\n"           \
            " length=%d,\n"                             \
            " dos_file_name_flagged='%s',\n"            \
            " dos_file_extension='%s',\n"               \
            " file_attributes=0x%X,\n"                  \
            " reserved=%d,\n"                           \
            " create_time_fine=%d,\n"                   \
            " create_time=%d,\n"                        \
            " create_date=%d,\n"                        \
            " last_access_date=%d,\n"                   \
            " ea_index_fat16=%d,\n"                     \
            " first_cluster_number_high_fat32=%d,\n"    \
            " modified_time=%d,\n"                      \
            " modified_date=%d,\n"                      \
            " first_cluster_number_fat16=%d,\n"         \
            " first_cluster_number_low_fat32=%d,\n"     \
            " file_size=%d,\n"                          \
            " first_cluster_number=%d,\n"               \
            " long_file_name='%s',\n"                   \
            " dos_file_name='%s',\n"                    \
            ")" % (
            self.length,
            self.dos_file_name_flagged,
            self.dos_file_extension,
            self.file_attributes,
            self.reserved,
            self.create_time_fine,
            self.create_time,
            self.create_date,
            self.last_access_date,
            self.ea_index_fat16,
            self.first_cluster_number_high_fat32,
            self.modified_time,
            self.modified_date,
            self.first_cluster_number_fat16,
            self.first_cluster_number_low_fat32,
            self.file_size,
            self.first_cluster_number,
            self.long_file_name,
            self.dos_file_name
            )

class LabelEntry(DirectoryEntry):
    pass

class PathEntry(DirectoryEntry):
    @property
    def name(self):
        return self.long_file_name or (self.dos_file_name + '.' + self.dos_file_extension).lower()

class SubdirectoryEntry(PathEntry):
    pass

class FileEntry(PathEntry):
    pass

class RootEntry(PathEntry):
    def __init__(self, filesystem):
        self.filesystem = filesystem

    @property
    def first_cluster_number(self):
        if self.filesystem.type == 'FAT32':
            return self.filesystem.extended_bios_parameter_block.root_directory_cluster_number
        else:
            raise NotImplementedError('sorry, FAT12/16 support not yet finished')

    @property
    def name(self):
        return ''

class DeletedEntry(DirectoryEntry):
    pass

class LongFileNameEntry(DirectoryEntry):
    LAST = 0x40

    length = 32
    unpacker = "<B10sBBB12sH4s"
    def __init__(self, filesystem, raw):
        self.filesystem = filesystem
        data = unpack(self.unpacker, raw)
        self.flagged_sequence_number = data[0]
        self.name0 = data[1]
        self.file_attributes = data[2]
        self.reserved = data[3]
        self.dos_name_checksum = data[4]
        self.name1 = data[5]
        self.first_cluster_number_fat16 = data[6]
        self.name2 = data[7]

    @property
    def is_last(self):
        return self.flagged_sequence_number & self.LAST

    @property
    def sequence_number(self):
        return self.flagged_sequence_number ^ self.LAST

    @property
    def name(self):
        n = self.name0 + self.name1 + self.name2
        if '\0\0' in n:
            n = n.rpartition('\0\0')[0]
        return n.decode('utf-16')

    def __repr__(self):
        return self.__class__.__name__ +"(\n"       \
            " length=%d,\n"                         \
            " flagged_sequence_number='%s',\n"      \
            " name0='%s',\n"                        \
            " file_attributes='%s',\n"              \
            " reserved='%s',\n"                     \
            " dos_name_checksum='%s',\n"            \
            " name1='%s',\n"                        \
            " first_cluster_number_fat16='%s',\n"   \
            " name2='%s',\n"                        \
            " name='%s',\n"                         \
            ")" % (
            self.length,
            self.flagged_sequence_number,
            self.name0,
            self.file_attributes,
            self.reserved,
            self.dos_name_checksum,
            self.name1,
            self.first_cluster_number_fat16,
            self.name2,
            self.name
            )
