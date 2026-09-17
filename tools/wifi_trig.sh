#!/system/bin/sh
echo "== con_mode =="
cat /sys/module/wlan/parameters/con_mode 2>/dev/null
echo "== services =="
ps -A | grep -iE "cnss|qrtr|wpa|hostapd|wifi" | head -8
echo "== svc wifi enable =="
svc wifi enable
sleep 8
echo "== dmesg after enable =="
dmesg | grep -iE "wlan|cnss|qrtr|qca|pil" | grep -v avc | tail -25
echo "== wlan0 =="
ip link show wlan0 2>&1 | head -2