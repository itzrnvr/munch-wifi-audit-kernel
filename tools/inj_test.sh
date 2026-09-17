#!/system/bin/sh
CH=${1:-6}
svc wifi disable 2>/dev/null
sleep 3
ip link set wlan0 down
echo 4 > /sys/module/wlan/parameters/con_mode
sleep 10
ip link set wlan0 up
sleep 3
/data/local/tmp/injtest wlan0
RC=$?
echo 0 > /sys/module/wlan/parameters/con_mode
sleep 5
svc wifi enable
exit $RC