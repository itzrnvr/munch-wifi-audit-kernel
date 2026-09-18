#!/bin/bash
# KSU-Next v3.3 with bisect stage 2: manager (tracepoints) on, kprobe hook_init off
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
set -e
cd /root/sbx
ln -sfn /root/kernelsu-next/kernel drivers/kernelsu
./scripts/config --enable CONFIG_KSU --enable CONFIG_KPROBES --enable CONFIG_KPROBE_EVENTS --enable CONFIG_KRETPROBES --enable CONFIG_OVERLAY_FS --enable CONFIG_BL_CLONE --set-val CONFIG_KSU_BISECT_STAGE 2
yes '' | make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null 2>&1
grep -E "^CONFIG_KSU=|^CONFIG_KSU_BISECT|^CONFIG_KRETPROBES=|^CONFIG_BL_CLONE=" .config
cp /root/key_backup.pem certs/signing_key.pem 2>/dev/null
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image > /tmp/build_ksun2.log 2>&1 || { grep -E "error:" /tmp/build_ksun2.log | head -6; exit 1; }
cp arch/arm64/boot/Image /mnt/d/kernel-build/Image-ksunext-s2
echo STAGED_KSUNEXT_S2
