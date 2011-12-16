# -*- encoding: utf-8 -*-
#
# Grasso - a FAT filesystem parser
#
# Copyright 2011 Emanuele Aina <em@nerd.ocracy.org>
#
# Released under the term of a MIT-style license, see LICENSE
# for details.

import math
from struct import unpack
from .util import FragmentInfo, FragmentedIO
from .fat import BootSector, DirectoryEntry, LabelEntry,   \
    DeletedEntry, PathEntry, SubdirectoryEntry, FileEntry, \
    RootEntry, LongFileNameEntry
from .fat16 import ExtendedBIOSParameterBlock16
from .fat32 import ExtendedBIOSParameterBlock32, FileSystemInformationSector32, FAT32

class Directory(FragmentedIO):
    def __init__(self, filesystem, entry):
        self.filesystem = filesystem
        self.entry = entry
        self.clusters = list(filesystem.fat.get_chain(entry.first_cluster_number))
        fragments = filesystem.get_chain_items(self.clusters)
        size = len(self.clusters) * filesystem.boot_sector.bytes_per_cluster
        super(Directory, self).__init__(filesystem.source, fragments, size)

        self.entries = []
        i = 0
        entry_count = size / DirectoryEntry.length
        while i < entry_count:
            entry = self.read_entry()
            if not entry:
                break
            i += 1
            if type(entry) is LongFileNameEntry:
                assert(entry.is_last)
                lfns = []
                lfns.append(entry)
                for j in range(lfns[0].sequence_number-1, 0, -1):
                    entry = self.read_entry()
                    lfns.append(entry)
                entry = self.read_entry()
                entry.long_file_name_entries = lfns
                i += lfns[0].sequence_number
            self.entries.append(entry)
        self.seek(0)

    @property
    def name(self):
        return self.entry.name

    @property
    def files(self):
        for e in self.entries:
            if type(e) is FileEntry:
                yield e

    @property
    def directories(self):
        for e in self.entries:
            if type(e) is SubdirectoryEntry:
                yield e

    def read_entry(self):
        raw = self.read(DirectoryEntry.length)
        data = unpack('<B10xB20x', raw)
        start = data[0]
        file_attributes = data[1]

        if start == 0:
            return None
        elif start == 0xE5:
            return DeletedEntry(self.filesystem, raw)
        elif file_attributes == DirectoryEntry.LONGFILENAME:
            return LongFileNameEntry(self.filesystem, raw)
        elif file_attributes & DirectoryEntry.LABEL:
            return LabelEntry(self.filesystem, raw)
        elif file_attributes & DirectoryEntry.DIRECTORY:
            return SubdirectoryEntry(self.filesystem, raw)
        else:
            return FileEntry(self.filesystem, raw)

    def __iter__(self):
        for d in self.directories:
            yield Directory(self.filesystem, d)
        for f in self.files:
            yield File(self.filesystem, f)

    def __getitem__(self, name):
        entry = self.get_entry(name)
        t = type(entry)
        if t is SubdirectoryEntry:
            item = Directory(self.filesystem, entry)
        if t is FileEntry:
            item = File(self.filesystem, entry)
        return item

    def get_entry(self, name):
        for e in self.entries:
            t = type(e)
            if t is not FileEntry and t is not SubdirectoryEntry:
                continue
            if e.name.lower() == name.lower():
                return e
        return None

    def __repr__(self):
        return "Directory(\n"           \
            " clusters=%s,\n"           \
            " size=%d,\n"               \
            " name='%s',\n"             \
            " entries=[%s]\n"           \
            " directories=[%s]\n"       \
            " files=[%s]\n"             \
            ")" % (
            self.clusters,
            self.size,
            self.name,
            '\n  '.join([''] + [repr(e).replace('\n', '\n  ') for e in self.entries]),
            '\n  '.join([''] + [repr(d).replace('\n', '\n  ') for d in self.directories]),
            '\n  '.join([''] + [repr(f).replace('\n', '\n  ') for f in self.files])
            )

class File(FragmentedIO):
    def __init__(self, filesystem, entry):
        self.filesystem = filesystem
        self.entry = entry
        self.clusters = list(filesystem.fat.get_chain(entry.first_cluster_number))
        fragments = filesystem.get_chain_items(self.clusters)
        size = entry.file_size
        super(File, self).__init__(filesystem.source, fragments, size)

    @property
    def name(self):
        return self.entry.name

    def __repr__(self):
        return "File(\n"           \
            " clusters=%s,\n"           \
            " size=%d,\n"               \
            " name='%s',\n"             \
            ")" % (
            self.clusters,
            self.size,
            self.name,
            )

class FATFileSystem(object):
    def __init__(self, fd):
        self.source = fd
        self.boot_sector = BootSector(self)
        if self.type == 'FAT32':
            b = self.boot_sector
            self.extended_bios_parameter_block = ExtendedBIOSParameterBlock32(self)
            ebpb = self.extended_bios_parameter_block
            fd.seek(ebpb.file_system_information_sector_number * b.bytes_per_sector)
            self.file_system_information_sector = FileSystemInformationSector32(self)
            fd.seek(b.reserved_sector_count * b.bytes_per_sector)
            self.fat = FAT32(self, ebpb.sector_per_fat * b.bytes_per_sector)
            self.root = Directory(self, RootEntry(self))
        else:
            self.extended_bios_parameter_block = ExtendedBIOSParameterBlock16(self)
            raise NotImplementedError('Sorry, FAT12/16 support not yet finished')

    @property
    def type(self):
        return self.boot_sector.type

    @property
    def system_area_size(self):
        b = self.boot_sector
        ebpb = self.extended_bios_parameter_block
        if self.type == 'FAT32':
            return b.reserved_sector_count + b.fat_count * ebpb.sector_per_fat
        else:
            return b.reserved_sector_count + b.fat_count * b.sectors_per_fat_fat16 \
                   + math.ceil(DirectoryEntry.length * b.max_root_entries_fat16 / b.bytes_per_sector)

    def cluster_number_to_logical_sector_number(self, cn):
        lsn = self.system_area_size + (cn - 2) * self.boot_sector.sectors_per_cluster
        return lsn

    def get_chain_items(self, clusters):
        b = self.boot_sector
        chain_offset = 0
        for c in clusters:
            offset = self.cluster_number_to_logical_sector_number(c) * b.bytes_per_sector
            yield FragmentInfo(c, offset, b.bytes_per_cluster, chain_offset)
            chain_offset += b.bytes_per_cluster

    def __getitem__(self, path):
        item = self.root
        curr, sep, tail = path.lstrip('/').partition('/')
        while curr:
            entry = item.get_entry(curr)
            t = type(entry)
            if not entry:
                raise IOError('file "'+path+'" not found')
            if sep and t is not SubdirectoryEntry:
                raise IOError('file "'+path+'" not found')
            curr, sep, tail = tail.partition('/')
            if t is SubdirectoryEntry:
                item = Directory(self, entry)
            if t is FileEntry:
                item = File(self, entry)
        return item

    def __str__(self):
        s = ""
        s += repr(self.boot_sector)
        s += "\n"
        s += repr(self.extended_bios_parameter_block)
        if self.file_system_information_sector:
            s += "\n"
            s += repr(self.file_system_information_sector)
        s += "\n"
        s += repr(self.fat)
        s += "\n"
        s += repr(self.root)
        return s
