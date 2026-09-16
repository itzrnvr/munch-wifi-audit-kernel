#!/system/bin/sh
echo 0 > /sys/module/wlan/parameters/con_mode
sleep 5
svc wifi enable
echo "back to station mode"
