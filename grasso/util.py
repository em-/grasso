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

    def in_range(self, start, end):
        return self.chain_offset_start <= end and start <= self.chain_offset_end

    def __repr__(self):
        return 'FragmentInfo(number=%d, offset=%d, size=%d, chain_offset_start=%s, chain_offset_end=%d)' % (self.number, self.offset, self.size, self.chain_offset_start, self.chain_offset_end)

class FragmentedIO(object):
    def __init__(self, source, fragments, size):
        self.source = source
        self.fragments = list(fragments)
        self.size = size

        self.position = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def writable(self):
        return False

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_END:
            self.position = self.size + offset
        elif whence == io.SEEK_CUR:
            self.position = self.position + offset
        else:
            self.position = offset

    def read(self, count=None):
        if count is None:
            count = self.size
        remaining = self.size - self.tell()
        count = min(count, remaining)

        start = self.tell()
        end = start + count
        data = ''
        fragments = [f for f in self.fragments if f.in_range(start, end)]
        for fragment in fragments:
            skip = max(0, start - fragment.chain_offset_start)
            take = min(fragment.size, end - fragment.chain_offset_start - skip)
            position = fragment.offset + skip
            self.source.seek(position, io.SEEK_SET)
            data += self.source.read(take)
            self.seek(take, io.SEEK_CUR)
        return data
