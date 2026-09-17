#!/system/bin/sh
echo "== raw dmesg tail (no filter) =="
dmesg | tail -8
echo "== con_mode now =="
cat /sys/module/wlan/parameters/con_mode
echo "== dmesg size =="
dmesg | wc -l