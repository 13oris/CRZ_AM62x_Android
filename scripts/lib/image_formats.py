"""Readers for the pinned SDK image formats and the vendor boot repacker."""

import bisect
import hashlib
import struct

from .common import require, run


def le(fmt, data, offset=0):
    return struct.unpack_from("<" + fmt, data, offset)


def align(size, boundary):
    return (size + boundary - 1) // boundary * boundary


class SparseImage:
    def __init__(self, stream):
        self.stream = stream
        magic, major, _, header_size, chunk_header, block, blocks, count, _ = le(
            "I4H4I", stream.read(28)
        )
        require((magic, major) == (0xED26FF3A, 1), "지원하는 Android sparse 이미지가 아닙니다.")
        require(header_size >= 28 and chunk_header >= 12 and block == 4096,
                "순정 super의 sparse 헤더가 예상과 다릅니다.")
        stream.seek(header_size)
        self.starts = []
        self.chunks = []
        self.block = block
        cursor = 0
        for _ in range(count):
            kind, _, num_blocks, total = le("HHII", stream.read(chunk_header))
            length = num_blocks * block
            pos = stream.tell()
            payload_sizes = {0xCAC1: length, 0xCAC2: 4, 0xCAC3: 0, 0xCAC4: 4}
            require(kind in payload_sizes and total - chunk_header == payload_sizes[kind],
                    "super sparse 청크 크기가 잘못됐습니다.")
            if kind != 0xCAC4:
                require(length > 0, "super sparse 청크가 비어 있습니다.")
                self.starts.append(cursor)
                self.chunks.append((cursor + length, kind, pos))
                cursor += length
            stream.seek(pos + total - chunk_header)
        require(cursor == blocks * block and cursor > 0, "super sparse 전체 크기가 일치하지 않습니다.")
        self.size = cursor

    def read(self, offset, count):
        require(0 <= offset <= self.size and 0 <= count <= self.size - offset,
                "super 이미지 범위를 벗어난 읽기 요청입니다.")
        data = bytearray()
        while count:
            index = bisect.bisect_right(self.starts, offset) - 1
            end, kind, pos = self.chunks[index]
            current = offset - self.starts[index]
            size = min(end - offset, count)
            if kind == 0xCAC1:
                self.stream.seek(pos + current)
                part = self.stream.read(size)
                require(len(part) == size, "super sparse RAW 청크가 잘렸습니다.")
                data.extend(part)
            elif kind == 0xCAC2:
                self.stream.seek(pos)
                fill = self.stream.read(4)
                require(len(fill) == 4, "super sparse FILL 청크가 잘렸습니다.")
                skip = current % 4
                data.extend((fill * ((skip + size + 3) // 4))[skip:skip+size])
            else:
                data.extend(bytes(size))
            offset += size
            count -= size
        return bytes(data)


class LogicalPartition:
    def __init__(self, image, name):
        self.image = image
        header_offset = 12288
        header = image.read(header_offset, 256)
        magic, major, _, size = le("IHHI", header)
        require(magic == 0x414C5030 and major == 10 and size in (128, 256),
                "super의 슬롯 A LP 메타데이터 헤더가 예상과 다릅니다.")
        unsigned = header[:12] + bytes(32) + header[44:size]
        require(hashlib.sha256(unsigned).digest() == header[12:44], "LP 헤더 SHA-256 불일치")
        table_size, = le("I", header, 44)
        require(table_size <= 65536 - size, "LP 테이블 크기 초과")
        table = image.read(header_offset + size, table_size)
        require(hashlib.sha256(table).digest() == header[48:80], "LP 테이블 SHA-256 불일치")

        def rows(descriptor, expected):
            start, count, width = le("III", header, descriptor)
            end = start + count * width
            require(width == expected and end <= len(table), "LP 테이블 행 형식 불일치")
            return [table[i:i+width] for i in range(start, end, width)]

        extents = rows(92, 24)
        for part in rows(80, 52):
            if part[:36].split(b"\0", 1)[0] != name.encode("ascii"):
                continue
            _, first, count, _ = le("IIII", part, 36)
            require(count > 0 and first + count <= len(extents), f"{name} extent 범위 오류")
            self.extents = []
            self.size = 0
            for extent in extents[first:first+count]:
                sectors, kind, sector, source = le("QIQI", extent)
                require(source == 0 and kind in (0, 1) and sectors > 0, f"지원하지 않는 {name} extent")
                require((sectors + sector) * 512 <= image.size, f"{name} extent 크기 초과")
                self.extents.append((self.size, sectors * 512, sector * 512 if kind == 0 else None))
                self.size += sectors * 512
            return
        raise ValueError(f"순정 super에서 {name}를 찾을 수 없습니다.")

    def __len__(self):
        return self.size

    def __getitem__(self, key):
        start, end, step = key.indices(self.size)
        require(step == 1, "연속적인 LP 범위만 읽을 수 있습니다.")
        if end <= start:
            return b""
        data = bytearray()
        for offset, length, physical in self.extents:
            a, b = max(start, offset), min(end, offset + length)
            if b > a:
                data.extend(self.image.read(physical + a - offset, b - a) if physical is not None else bytes(b-a))
        require(len(data) == end - start, "논리 파티션을 완전히 읽지 못했습니다.")
        return bytes(data)


def extract_vendor(path):
    with path.open("rb") as stream:
        return LogicalPartition(SparseImage(stream), "vendor_a")[:]


class Ext4Text:
    """Read regular config files from the pinned, unmounted ext4 image."""

    def __init__(self, data):
        self.data = data if isinstance(data, LogicalPartition) else memoryview(data)
        sb = self.data[1024:2048]
        require(le("H", sb, 56)[0] == 0xEF53, "vendor_a가 ext4가 아닙니다.")
        first, block_shift = le("II", sb, 20)
        require(block_shift == 2, "지원하지 않는 vendor ext4 블록 크기")
        self.block = 1024 << block_shift
        self.inodes_per_group, = le("I", sb, 40)
        self.inode_size, = le("H", sb, 88)
        self.desc_size = max(32, le("H", sb, 254)[0])
        self.desc_start = (first + 1) * self.block

    def inode(self, number):
        group, index = divmod(number - 1, self.inodes_per_group)
        offset = self.desc_start + group * self.desc_size
        descriptor = self.data[offset:offset+self.desc_size]
        block, = le("I", descriptor, 8)
        if self.desc_size >= 64:
            block += le("I", descriptor, 40)[0] << 32
        start = block * self.block + index * self.inode_size
        return self.data[start:start + self.inode_size]

    def extents(self, node):
        magic, count, _, depth, _ = le("4HI", node)
        require(magic == 0xF30A and depth <= 5 and 12 + count * 12 <= len(node),
                "지원하지 않는 ext4 extent 트리입니다.")
        for index in range(count):
            offset = 12 + index * 12
            if depth:
                _, lo, hi, _ = le("IIHH", node, offset)
                next_offset = (lo + (hi << 32)) * self.block
                child = self.data[next_offset:next_offset + self.block]
                require(le("H", child, 6)[0] == depth - 1, "ext4 extent 깊이 불일치")
                yield from self.extents(child)
            else:
                logical, length, hi, lo = le("IHHI", node, offset)
                if length <= 32768:
                    yield logical, length, lo + (hi << 32)

    def contents(self, inode):
        mode, = le("H", inode)
        require(mode & 0xF000 in (0x4000, 0x8000), "일반 파일이나 디렉터리만 읽을 수 있습니다.")
        size = le("I", inode, 4)[0] + (le("I", inode, 108)[0] << 32)
        require(size <= len(self.data), "ext4 파일 크기 초과")
        if not size:
            return b""
        require(le("I", inode, 32)[0] & 0x80000, "ext4 파일에 extent 플래그가 없습니다.")
        data = bytearray(size)
        for logical, length, physical in self.extents(inode[40:100]):
            start = logical * self.block
            offset = physical * self.block
            count = min(size - start, length * self.block)
            if count > 0:
                require(offset + count <= len(self.data), "ext4 extent 범위 초과")
                data[start:start+count] = self.data[offset:offset+count]
        return bytes(data)

    def read(self, name):
        node = self.inode(2)
        for component in name.split("/"):
            require(le("H", node)[0] & 0xF000 == 0x4000, f"vendor 경로가 디렉터리가 아닙니다: {name}")
            directory = self.contents(node)
            offset = 0
            while offset < len(directory):
                number, width, length, _ = le("IHBB", directory, offset)
                require(8 <= width <= len(directory) - offset and length <= width - 8,
                        "ext4 디렉터리 항목 크기가 잘못됐습니다.")
                if number and directory[offset+8:offset+8+length] == component.encode():
                    node = self.inode(number)
                    break
                offset += width
            else:
                raise FileNotFoundError(name)
        require(le("H", node)[0] & 0xF000 == 0x8000, f"vendor 일반 파일이 아닙니다: {name}")
        return self.contents(node)


class VendorBoot:
    def __init__(self, data):
        require(data[:8] == b"VNDRBOOT" and le("I", data, 8)[0] == 4, "vendor_boot v4가 필요합니다.")
        self.page = le("I", data, 12)[0]
        require(self.page == 4096, "vendor_boot 페이지 크기가 예상과 다릅니다.")
        ramdisk_size = le("I", data, 24)[0]
        header_size, dtb_size = le("II", data, 2096)
        table_size, count, width, config_size = le("4I", data, 2112)
        require((header_size, table_size, count, width) == (2128, 108, 1, 108),
                "vendor_boot ramdisk 테이블 형식이 예상과 다릅니다.")
        self.header = data[:header_size]
        cmdline, _, padding = self.header[28:2076].partition(b"\0")
        require(not padding.strip(b"\0"), "vendor_boot cmdline 뒤에 예상 밖 데이터가 있습니다.")
        self.cmdline = cmdline.decode("ascii")
        offset = align(header_size, self.page)
        self.ramdisk, self.dtb, self.table, self.bootconfig = [
            data[start:start+size] for start, size in (
                (offset, ramdisk_size),
                (offset + align(ramdisk_size, self.page), dtb_size),
                (offset + align(ramdisk_size, self.page) + align(dtb_size, self.page), table_size),
                (offset + align(ramdisk_size, self.page) + align(dtb_size, self.page)
                 + align(table_size, self.page), config_size),
            )
        ]
        require(le("3I", self.table) == (ramdisk_size, 0, 1), "vendor_boot ramdisk 속성이 예상과 다릅니다.")
        magic, total, _, self.entry_size, count, self.entries, _, _ = struct.unpack_from(">8I", self.dtb)
        require(magic == 0xD7B7AB1E and total == len(self.dtb) and count == 6 and self.entry_size >= 32,
                "vendor_boot DTB 테이블 형식이 예상과 다릅니다.")
        self.trees = []
        for index in range(count):
            size, offset = struct.unpack_from(">2I", self.dtb, self.entries + index * self.entry_size)
            blob = self.dtb[offset:offset+size]
            require(len(blob) == size and blob[:4] == bytes.fromhex("d00dfeed"), "잘못된 DTB 항목")
            self.trees.append(blob)

    def records(self):
        cpio = run("lz4", "-dc", data=self.ramdisk, capture=True)
        offset = 0
        while cpio[offset:offset+6] == b"070701":
            fields = [int(cpio[i:i+8], 16) for i in range(offset+6, offset+110, 8)]
            size, name_size = fields[6], fields[11]
            start = align(offset + 110 + name_size, 4)
            end = align(start + size, 4)
            name = cpio[offset+110:offset+110+name_size-1].decode()
            require(name_size > 0 and end <= len(cpio), "vendor ramdisk CPIO 항목이 잘렸습니다.")
            yield name, fields[0], cpio[offset:start], cpio[start:start+size]
            if name == "TRAILER!!!":
                require(not cpio[end:].strip(b"\0"), "vendor ramdisk CPIO 뒤에 예상 밖 데이터가 있습니다.")
                return
            offset = end
        raise ValueError("vendor ramdisk CPIO 종료 레코드가 없습니다.")

    def pack(self, first_dtb, replacements, additions, command_line):
        cpio = bytearray()
        entries = list(self.records())
        inode = max(entry[1] for entry in entries)
        names = {entry[0] for entry in entries}
        require(len(names) == len(entries) and replacements.keys() <= names and not additions.keys() & names,
                "vendor ramdisk 패치 대상이 순정 CPIO와 일치하지 않습니다.")

        def append(header, data):
            cpio.extend(header)
            cpio.extend(data)
            cpio.extend(bytes((-len(cpio)) % 4))

        for name, _, header, data in entries[:-1]:
            if name in replacements:
                data = replacements[name]
                header = header[:54] + f"{len(data):08x}".encode() + header[62:]
            append(header, data)
        for name, data in additions.items():
            inode += 1
            name_bytes = name.encode() + b"\0"
            fields = (inode, 0o100644, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name_bytes), 0)
            header = b"070701" + b"".join(f"{i:08x}".encode() for i in fields) + name_bytes
            append(header + bytes((-len(header)) % 4), data)
        append(entries[-1][2], entries[-1][3])
        cpio.extend(bytes((-len(cpio)) % 512))
        ramdisk = run("lz4", "-l", "-9", "-c", data=bytes(cpio), capture=True)

        dtbs = bytearray(self.dtb[:self.entries + len(self.trees) * self.entry_size])
        for index, blob in enumerate([first_dtb, *self.trees[1:]]):
            if index:
                dtbs.extend(bytes((-len(dtbs)) % 4))
            struct.pack_into(">2I", dtbs, self.entries + index * self.entry_size, len(blob), len(dtbs))
            dtbs.extend(blob)
        struct.pack_into(">I", dtbs, 4, len(dtbs))
        header = bytearray(self.header)
        struct.pack_into("<I", header, 24, len(ramdisk))
        struct.pack_into("<I", header, 2100, len(dtbs))
        command_line = command_line.encode("ascii")
        require(0 < len(command_line) < 2048 and b"\0" not in command_line and b"\n" not in command_line,
                "vendor_boot cmdline 형식이 잘못됐습니다.")
        header[28:2076] = command_line.ljust(2048, b"\0")
        table = struct.pack("<I", len(ramdisk)) + self.table[4:]
        image = bytearray()
        for data in (header, ramdisk, dtbs, table, self.bootconfig):
            image.extend(data)
            image.extend(bytes((-len(image)) % self.page))
        return bytes(image)
