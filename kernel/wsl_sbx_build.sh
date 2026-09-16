#!/bin/bash
set -x
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
cd /root
if [ ! -d /root/sbx/.git ]; then
  git clone --depth 1 -b oni-1.0-staging --single-branch https://github.com/sandboXimi/android_kernel_xiaomi_munch.git /root/sbx >/dev/null 2>&1
fi
cd /root/sbx
echo "clone: $(git log -1 --format=%h)"
patch -p1 --forward < /mnt/d/kernel-build/qcacld_injection.patch > /tmp/psbx.log 2>&1
echo "rej: $(find . -name '*.rej' | wc -l)"
printf "\nCONFIG_FEATURE_MONITOR_MODE_SUPPORT := y\nCONFIG_FEATURE_FRAME_INJECTION_SUPPORT := y\n" >> drivers/staging/qcacld-3.0/configs/default_defconfig
python3 /mnt/d/kernel-build/fix_tree.py || echo FIXTREE_ISSUES
python3 - <<'PYEOF'
import re
p = "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_cfg80211.c"
s = open(p, encoding="utf-8", errors="ignore").read()
if "hdd_map_nl_chan_width(csa_params->chandef.width);\n" not in s:
    s2, n = re.subn(r"hdd_map_nl_chan_width\(csa_params->chandef\.width,\s*\n\s*0\);",
                    "hdd_map_nl_chan_width(csa_params->chandef.width);", s)
    if n:
        open(p, "w", encoding="utf-8", errors="ignore").write(s2)
    print("mapnl:", n)
else:
    print("mapnl already fixed")
i = s.find("__wlan_hdd_cfg80211_join_ibss")
j = s.find("params->chandef.width);", i)
if j > 0:
    s = s[:j] + "params->chandef.width,\n\t\t\t\t\t\t 0);" + s[j+len("params->chandef.width);"):]
    open(p, "w", encoding="utf-8", errors="ignore").write(s)
    print("join_ibss hunk applied")
PYEOF
sed -i "/wlan_hdd_frame_inject_integration.o/d" drivers/staging/qcacld-3.0/Kbuild 2>/dev/null || true
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- vendor/munch_defconfig > /tmp/cfgsbx.log 2>&1 || { echo DEFCFG_FAIL; tail -4 /tmp/cfgsbx.log; exit 1; }
./scripts/config -e SPECTRA_CAMERA -e EROFS_FS -e EROFS_FS_ZIP -e EROFS_FS_SECURITY -e EROFS_FS_USE_VM_MAP_RAM
./scripts/config -e FEATURE_FRAME_INJECTION_SUPPORT -e FEATURE_MONITOR_MODE_SUPPORT
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >> /tmp/cfgsbx.log 2>&1
grep -E "QCA_CLD_WLAN=|EROFS_FS=" .config
nohup make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image.gz-dtb > /tmp/buildsbx.log 2>&1 &
sleep 10
tail -2 /tmp/buildsbx.log
echo SBX_BUILD_STARTED
