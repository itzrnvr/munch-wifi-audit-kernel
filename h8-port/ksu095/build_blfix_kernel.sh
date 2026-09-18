#!/bin/bash
# build_blfix_kernel.sh — clean kernel (no KSU) + bl_clone built-in
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
set -e
cd /root/sbx

# KSU OUT for this variant (bisect stage 2 = disabled) — but keep KSU linked
# out cleanly: CONFIG_KSU=n means no KSU objects at all.
./scripts/config --disable CONFIG_KSU --set-val CONFIG_KSU_BISECT_STAGE 0
yes '' | make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null 2>&1
grep -E "^CONFIG_KSU=|^# CONFIG_KSU|^CONFIG_BL_CLONE=" .config

cp /root/key_backup.pem certs/signing_key.pem 2>/dev/null
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image > /tmp/build_blfix.log 2>&1 || { tail -20 /tmp/build_blfix.log; exit 1; }
cp arch/arm64/boot/Image /mnt/d/kernel-build/Image-blfix
echo "STAGED Image-blfix"