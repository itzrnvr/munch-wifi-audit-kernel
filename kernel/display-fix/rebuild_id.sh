#!/bin/bash
# Rebuild with stock kernel identity
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
export KBUILD_BUILD_USER=builder
export KBUILD_BUILD_HOST=pangu-build-component-vendor-495440-vdzxv-4wq8x-vjtnk

cd /root/sbx || exit 1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image > /tmp/build_id.log 2>&1
RC=$?
echo "BUILD_RC=$RC" >> /tmp/build_id.log
exit $RC