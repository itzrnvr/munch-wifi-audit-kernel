#!/bin/bash
# kernel_id_fix.sh — make the kernel report the stock POCO F4 identity
# Stock: Linux version 4.19.157-perf-g045c5942d886
# Ours:  4.19.300-sandboX-outerspace-v1.0
# Banking/Play Integrity reads uname; matching stock removes the flag.
set -e
cd /root/sbx

# where does the -sandboX suffix come from?
grep -rn "sandboX-outerspace" Makefile scripts/setlocalversion 2>/dev/null | head -3 || true
grep -n "EXTRAVERSION" Makefile | head -2

# set version + stock-style localversion
sed -i 's/^SUBLEVEL = 300/SUBLEVEL = 157/' Makefile
sed -i 's/^EXTRAVERSION =.*/EXTRAVERSION = -perf-g045c5942d886/' Makefile
grep -E "^VERSION|^PATCHLEVEL|^SUBLEVEL|^EXTRAVERSION" Makefile
echo "---"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- include/config/kernel.release 2>&1 | tail -2
cat include/config/kernel.release 2>/dev/null