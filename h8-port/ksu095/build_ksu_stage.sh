#!/bin/bash
# build_ksu_stage.sh <stage 0|1|2> — build KSU kernel at a bisect stage
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
STAGE="${1:-1}"
cd /root/sbx || exit 1
./scripts/config --set-val CONFIG_KSU_BISECT_STAGE "$STAGE"
yes '' | make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null 2>&1
grep -q "CONFIG_KSU_BISECT_STAGE=$STAGE" .config || { echo "STAGE_SET_FAILED"; exit 1; }
cp /root/key_backup.pem certs/signing_key.pem 2>/dev/null
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image > /tmp/build_stage.log 2>&1
RC=$?
echo "BUILD_STAGE${STAGE}_RC=$RC" >> /tmp/build_stage.log
tail -2 /tmp/build_stage.log
[ $RC -ne 0 ] && exit 1
cp arch/arm64/boot/Image "/mnt/d/kernel-build/Image-ksu-stage${STAGE}"
echo "STAGED Image-ksu-stage${STAGE}"
