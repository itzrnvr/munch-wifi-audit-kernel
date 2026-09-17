#!/system/bin/sh
echo "== module states =="
for m in /data/adb/modules/*/; do
	n=$(basename $m)
	d="on"
	[ -f "$m/disable" ] && d="OFF"
	echo "$n: $d"
done
echo "== re-enable ONLY wifi_pktcap =="
rm -f /data/adb/modules/wifi_pktcap/disable
echo "== wlan0 =="
ip link show wlan0 2>&1 | head -1