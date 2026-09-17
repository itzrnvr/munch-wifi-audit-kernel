#!/system/bin/sh
mkdir -p /data/local/tmp
dmesg > /data/local/tmp/boot.log 2>/dev/null
sync
echo "== wlan lines in boot log =="
grep -icE "wlan|hdd|cnss|qrtr|qca" /data/local/tmp/boot.log
echo "== wlan0 =="
ip link show wlan0 2>&1 | head -2
echo "== ini overlay =="
head -3 /vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini 2>&1
grep -c "packet_capture_mode" /vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini 2>&1