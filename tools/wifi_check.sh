#!/system/bin/sh
echo "== lsmod =="
lsmod | grep -iE "wlan|qca"
echo "== /sys/module/wlan =="
ls /sys/module/wlan 2>/dev/null || echo "no wlan module dir"
echo "== kallsyms hdd count =="
grep -c " hdd" /proc/kallsyms
echo "== kallsyms wlan =="
grep -c "wlan_" /proc/kallsyms
echo "== qcacld in kernel =="
grep -cw "wlan_hdd_open" /proc/kallsyms
echo "== dmesg wlan =="
dmesg | grep -iE "wlan|qca_cld|cnss|qrtr|wcnss" | grep -v avc | tail -20
echo "== wifi module dir =="
ls /data/adb/modules/wifi_pktcap/ 2>/dev/null | head -5
echo "== firmware ini =="
ls -la /vendor/firmware/wlan/qca_cld/ 2>/dev/null | head -5