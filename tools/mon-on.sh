#!/system/bin/sh
# Switch wlan0 to monitor mode on channel (default 6)
CH=${1:-6}
svc wifi disable 2>/dev/null
sleep 3
ip link set wlan0 down
echo 4 > /sys/module/wlan/parameters/con_mode
sleep 10
ip link set wlan0 up
sleep 5
/data/local/kali/kali-arm64/root/iwpriv wlan0 setMonChan $CH 0
sleep 5
ifconfig wlan0 up
echo "monitor mode on channel $CH (con_mode=$(cat /sys/module/wlan/parameters/con_mode))"
