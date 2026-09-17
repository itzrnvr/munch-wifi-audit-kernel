#!/system/bin/sh
echo "== uptime =="
uptime
echo "== dmesg head =="
dmesg | head -3
echo "== dmesg cnss anywhere =="
dmesg | grep -ic cnss
echo "== cnss-daemon bin =="
ls -la /vendor/bin/cnss-daemon /vendor/bin/qrtr-ns 2>/dev/null
echo "== try start =="
export LD_LIBRARY_PATH=/vendor/lib64:/vendor/dsp/cnss:/system/lib64
qrtr-ns -f &
sleep 1
cnss-daemon -n -l &
sleep 3
ps -A | grep -E "cnss-daemon|qrtr-ns" | head -3
echo "== fs_ready =="
cat /sys/kernel/cnss/fs_ready 2>/dev/null || echo 1 > /sys/kernel/cnss/fs_ready 2>/dev/null
ls /sys/kernel/cnss/ 2>/dev/null | head -8
sleep 5
echo "== dmesg new =="
dmesg | grep -iE "cnss|wlan|qrtr|qca|pil" | grep -v avc | tail -20