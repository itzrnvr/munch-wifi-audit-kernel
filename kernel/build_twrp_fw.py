#!/usr/bin/env python3
"""Append qca6390 firmware as an extra cpio archive to the TWRP boot ramdisk.

Kernel initramfs supports concatenated cpio archives, so we gunzip the stock
ramdisk, append our archive (lib/firmware/...), regzip, and rebuild the
boot-img v3 with the same kernel + grown ramdisk.
"""
import gzip
import hashlib
import struct
import subprocess
import sys

PAGE = 4096


def round_up(x, a):
    return (x + a - 1) // a * a


def main():
    boot_in, kernel, fw_dir, cpio_new, boot_out = sys.argv[1:6]
    data = open(boot_in, 'rb').read()
    kern = open(kernel, 'rb').read()
    kernel_size, ramdisk_size = struct.unpack_from('<II', data, 8)
    ramdisk = data[PAGE + round_up(kernel_size, PAGE):][:ramdisk_size]

    # build the firmware cpio (newc format) via the cpio binary
    staging = '/tmp/stage'
    subprocess.run(['rm', '-rf', staging], check=True)
    subprocess.run(['mkdir', '-p', staging + '/lib/firmware/qca6390'], check=True)
    subprocess.run(['cp', '-r', fw_dir + '/.', staging + '/lib/firmware/qca6390/'], check=True)
    with open(cpio_new, 'wb') as f:
        listing = subprocess.run(['find', '.'], cwd=staging,
                                 capture_output=True, check=True).stdout
        subprocess.run(['cpio', '-H', 'newc', '-o'], cwd=staging,
                       input=listing, stdout=f, stderr=subprocess.DEVNULL,
                       check=True)

    raw = gzip.decompress(ramdisk) if ramdisk[:2] == b'\x1f\x8b' else ramdisk
    newraw = raw + open(cpio_new, 'rb').read()
    newrd = gzip.compress(newraw, 6)
    print(f'ramdisk: {ramdisk_size} -> {len(newrd)} bytes (raw {len(raw)} + fw cpio {len(newraw)-len(raw)})')

    hdr = bytearray(data[:PAGE])
    struct.pack_into('<I', hdr, 8, len(kern))
    struct.pack_into('<I', hdr, 12, len(newrd))
    out = bytearray(data)
    end = PAGE + round_up(kernel_size, PAGE) + round_up(ramdisk_size, PAGE)
    out[end:] = b'\0' * (len(out) - end)
    out[0:PAGE] = hdr
    out[PAGE:PAGE + len(kern)] = kern
    roff = PAGE + round_up(len(kern), PAGE)
    out[roff:roff + len(newrd)] = newrd
    open(boot_out, 'wb').write(out)
    print('wrote', boot_out, len(out))
    print('sha256 =', hashlib.sha256(out).hexdigest())


if __name__ == '__main__':
    main()
