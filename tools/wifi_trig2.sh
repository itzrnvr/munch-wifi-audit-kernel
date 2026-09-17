#!/system/bin/sh
svc wifi enable
sleep 12
echo "== wlan logs =="
dmesg | grep -iE "hdd|qcacld|wlan|qca|request_firm|firmware" | grep -viE "avc|bootconfig" | tail -30
echo "== wlan0 =="
ip link show wlan0 2>&1 | head -2
echo "== dumpsys =="
dumpsys wifi 2>/dev/null | grep -m1 "Wi-Fi is"