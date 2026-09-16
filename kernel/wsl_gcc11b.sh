#!/bin/bash
set -e
for t in as ld ar nm objcopy objdump strip ranlib readelf size strings addr2line; do
  ln -sf "/opt/bu238/root/usr/bin/aarch64-linux-gnu-$t" "/opt/bu238/root/usr/bin/$t"
done
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
aarch64-linux-gnu-gcc --version | head -1
as --version | head -1
cd /root/munch
./scripts/config -e QCA_CLD_WLAN -e FEATURE_FRAME_INJECTION_SUPPORT -e FEATURE_MONITOR_MODE_SUPPORT
./scripts/config -d DYNAMIC_DEBUG
./scripts/config --set-str QCA_CLD_WLAN_PROFILE qca6390
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > /tmp/cfg12.log 2>&1
grep -E "QCA_CLD_WLAN" .config
nohup make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image.gz-dtb > /tmp/build12.log 2>&1 &
sleep 15
tail -2 /tmp/build12.log
echo BUILD12_STARTED
