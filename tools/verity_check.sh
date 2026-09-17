#!/system/bin/sh
echo "== cmdline verity flags =="
cat /proc/cmdline | tr ' ' '\n' | grep -iE "verity|verifiedboot|vbmeta|slot"
echo "== dm devices (verity) =="
ls /sys/block/ | grep dm | head -5
dmsetup ls 2>/dev/null | head -6
echo "== mounts with verity =="
cat /proc/mounts | grep -iE "verity|avb|dm-" | head -5
echo "== magisk module states =="
for m in /data/adb/modules/*/; do
	n=$(basename $m)
	d="enabled"
	[ -f "$m/disable" ] && d="DISABLED"
	echo "$n: $d"
done
echo "== verity mode dmesg =="
dmesg | grep -iE "verity|avb|vbmeta" | tail -8