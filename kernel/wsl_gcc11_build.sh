#!/bin/bash
set -e
mkdir -p /opt/gcc11 && cd /opt/gcc11
BASE=http://archive.ubuntu.com/ubuntu/pool/main/g/gcc-11-cross
for f in cpp-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb \
         gcc-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb \
         libgcc-11-dev-arm64-cross_11.4.0-1ubuntu1~22.04.3cross1_all.deb; do
  [ -f "$f" ] || wget -q "$BASE/$f"
done
ls /opt/gcc11/*.deb
for d in /opt/gcc11/*.deb; do dpkg -x "$d" /opt/gcc11/root; done
find /opt/gcc11/root -name "aarch64-linux-gnu-gcc-11" | head -1
GCCBIN=$(dirname "$(find /opt/gcc11/root -name "aarch64-linux-gnu-gcc-11" | head -1)")
# symlink plain name
ln -sf "$GCCBIN/aarch64-linux-gnu-gcc-11" "$GCCBIN/aarch64-linux-gnu-gcc"
export PATH="/opt/bu238/root/usr/bin:$GCCBIN:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
aarch64-linux-gnu-gcc --version | head -1
aarch64-linux-gnu-ld --version | head -1

cd /root/munch
make mrproper >/dev/null 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- munch_user_defconfig > /tmp/cfg11.log 2>&1
./scripts/config -e FEATURE_FRAME_INJECTION_SUPPORT -e FEATURE_MONITOR_MODE_SUPPORT
./scripts/config -d DYNAMIC_DEBUG
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >> /tmp/cfg11.log 2>&1
grep -E "QCA_CLD_WLAN=" .config || echo "NO_QCA_CLD"
nohup make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image.gz-dtb > /tmp/build11.log 2>&1 &
sleep 10
tail -2 /tmp/build11.log
echo GCC11_BUILD_STARTED
