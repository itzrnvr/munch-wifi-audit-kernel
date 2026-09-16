#!/bin/bash
set -e
# Transplant stock-era transport stack (s-oss) into the bootable
# SandboXimi tree: qrtr + cnss2 + mhi.
cd /root/munch
for f in net/qrtr/fifo.c net/qrtr/qrtr.c net/qrtr/smd.c net/qrtr/tun.c \
         drivers/net/wireless/cnss2/main.h drivers/net/wireless/cnss2/pci.c \
         drivers/net/wireless/cnss2/qmi.c drivers/net/wireless/cnss2/reg.h; do
  cp "/root/munch/$f" "/root/sbx/$f"
  echo "xplant $f"
done
cp -r /root/munch/drivers/bus/mhi/core /root/sbx/drivers/bus/mhi/
cp -r /root/munch/drivers/bus/mhi/controllers /root/sbx/drivers/bus/mhi/
cp -r /root/munch/drivers/bus/mhi/devices /root/sbx/drivers/bus/mhi/
echo "mhi stack copied"
cd /root/sbx
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image.gz-dtb > /tmp/buildhyb.log 2>&1
RC=$?
echo RC=$RC
ls -la arch/arm64/boot/Image 2>/dev/null
grep -aE "error:|Error [0-9]|dangerous" /tmp/buildhyb.log | head -6
exit $RC
