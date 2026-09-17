#!/system/bin/sh
echo "== force hdd re-init via con_mode =="
echo 0 > /sys/module/wlan/parameters/con_mode 2>/dev/null
sleep 2
echo 1 > /sys/module/wlan/parameters/con_mode
sleep 5
echo 0 > /sys/module/wlan/parameters/con_mode
sleep 8
echo "== logs =="
dmesg | grep -iE "wlan|hdd|qcacld|con_mode|qca|ol_|cds" | grep -viE "avc" | tail -30
echo "== wlan0 =="
ip link show wlan0 2>&1 | head -2