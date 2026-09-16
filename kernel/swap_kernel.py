#!/usr/bin/env python3
"""Swap the kernel blob in a boot-img-v3 image (Magisk-patched debug-boot.img).

Keeps header/ramdisk/cmdline byte-identical; only kernel_size and blob layout
change. Output padded to the original file (partition) size.
"""
import struct
import sys
import hashlib

PAGE = 4096


def round_up(x, a):
    return (x + a - 1) // a * a


def main():
    boot_in, kernel_in, boot_out = sys.argv[1], sys.argv[2], sys.argv[3]
    data = open(boot_in, 'rb').read()
    kern = open(kernel_in, 'rb').read()

    assert data[:8] == b'ANDROID!', 'bad magic'
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from('<IIII', data, 8)
    header_version = struct.unpack_from('<I', data, 40)[0]
    assert header_version == 3, f'expected v3 header, got {header_version}'
    assert header_size == 1580, f'unexpected header_size {header_size}'

    kernel_off = PAGE
    ramdisk_off = PAGE + round_up(kernel_size, PAGE)
    ramdisk = data[ramdisk_off:ramdisk_off + ramdisk_size]
    assert len(ramdisk) == ramdisk_size, 'ramdisk short read'

    # sanity: old blob + new blob must look like arm64 Image headers
    for name, blob in (('old', data[kernel_off:kernel_off + 32]), ('new', kern[:32])):
        text_off, image_sz, flags = struct.unpack_from('<QQQ', blob, 8)
        print(f'{name} kernel: text_offset={text_off:#x} image_size={image_sz:#x} flags={flags:#x}')
    text_off = struct.unpack_from('<Q', kern, 8)[0]
    assert text_off == 0x80000, f'new kernel text_offset {text_off:#x} != 0x80000 (not a raw Image?)'

    hdr = bytearray(data[:PAGE])
    struct.pack_into('<I', hdr, 8, len(kern))
    out = bytearray(data)  # keeps original full length + untouched trailing bytes
    out[0:PAGE] = hdr
    old_ramdisk_end = ramdisk_off + ramdisk_size
    out[PAGE:old_ramdisk_end] = b'\0' * (old_ramdisk_end - PAGE)
    out[PAGE:PAGE + len(kern)] = kern
    roff = PAGE + round_up(len(kern), PAGE)
    out[roff:roff + ramdisk_size] = ramdisk

    open(boot_out, 'wb').write(out)
    print(f'kernel {kernel_size} -> {len(kern)} bytes; ramdisk {ramdisk_size} kept; '
          f'out {len(out)} bytes')
    print('sha256(out) =', hashlib.sha256(out).hexdigest())
    print('sha256(kern) =', hashlib.sha256(kern).hexdigest())


if __name__ == '__main__':
    main()
