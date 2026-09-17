#!/system/bin/sh
echo "== scan test =="
cmd -w wifi status 2>/dev/null | head -5 || dumpsys wifi | grep -m2 "SSID\|mWifiInfo"
echo "== monitor switch test =="
svc wifi disable
sleep 3
ip link set wlan0 down
echo 4 > /sys/module/wlan/parameters/con_mode
sleep 10
ip link set wlan0 up
echo "con_mode=$(cat /sys/module/wlan/parameters/con_mode)"
echo "== inject test (mdk4 3s) =="
/data/local/kali/kali-arm64/root/mdk4 wlan0 d -t 66:66:66:66:66:66 -s 250 -c 2>&1 &
MDK=$!
sleep 3
kill $MDK 2>/dev/null
echo "== back to STA =="
echo 0 > /sys/module/wlan/parameters/con_mode
sleep 5
svc wifi enable
sleep 6
ip link show wlan0 | head -1
echo "con_mode=$(cat /sys/module/wlan/parameters/con_mode) (0=STA ok)"