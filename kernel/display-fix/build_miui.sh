#!/bin/bash
# Build the MIUI-display kernel with the original GCC-11 toolchain
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"

which aarch64-linux-gnu-gcc
aarch64-linux-gnu-gcc --version | head -1

cd /root/sbx || exit 1

# Clean any wrong-toolchain objects
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- clean > /dev/null 2>&1

# Restore the original module-signing key so bl_clone.ko stays loadable
cp /root/key_backup.pem certs/signing_key.pem 2>/dev/null

# Build
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image.gz-dtb > /tmp/build_miui.log 2>&1
RC=$?
echo "BUILD_DONE_RC=$RC" >> /tmp/build_miui.log
exit $RC
