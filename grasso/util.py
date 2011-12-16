# -*- encoding: utf-8 -*-
#
# Grasso - a FAT filesystem parser
#
# Copyright 2011 Emanuele Aina <em@nerd.ocracy.org>
#
# Released under the term of a MIT-style license, see LICENSE
# for details.

import io
from struct import unpack

class FragmentInfo(object):
    def __init__(self, number, offset, size, chain_offset=0):
        self.number = number
        self.offset = offset
        self.size = size
        self.chain_offset_start = chain_offset
        self.chain_offset_end = chain_offset + size

    def __repr__(self):
        return 'FragmentInfo(number=%d, offset=%d, size=%d, chain_offset_start=%s, chain_offset_end=%d)' % (self.number, self.offset, self.size, self.chain_offset_start, self.chain_offset_end)

class FragmentedIO(object):
    def __init__(self, source, fragments, size):
        self.source = source
        self.fragments = list(fragments)
        self.size = size

        self.offset = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def writable(self):
        return False

    def tell(self):
        return self.offset

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_END:
            self.offset = self.size + offset
        elif whence == io.SEEK_CUR:
            self.offset = self.offset + offset
        else:
            self.offset = offset

    def read(self, to_read=None):
        if to_read is None:
            to_read = self.size
        remaining = self.size - self.offset
        to_read = min(to_read, remaining)

        offset_start = self.offset
        offset_end = offset_start + to_read
        cluster_offset = offset_start
        data = ''
        for c in self.fragments:
            if c.chain_offset_end < offset_start:
                cluster_offset -= c.size
                continue
            if offset_end < c.chain_offset_start:
                break
            self.source.seek(c.offset + cluster_offset, io.SEEK_SET)
            cluster_to_read = min(to_read, c.size - cluster_offset)
            data += self.source.read(cluster_to_read)
            to_read -= cluster_to_read
            self.offset += cluster_to_read
            cluster_offset = 0
        return data
