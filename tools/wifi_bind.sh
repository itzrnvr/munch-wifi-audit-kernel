#!/system/bin/sh
echo "== platform drivers wlan/cnss =="
ls /sys/bus/platform/drivers/ | grep -iE "wlan|qca|cnss|qcom,cnss"
echo "== cnss devices =="
ls /sys/bus/platform/devices/ | grep -iE "cnss|qca6390|wlan" | head -6
echo "== driver bind check =="
for d in $(ls /sys/bus/platform/devices/ | grep -iE "c440000|qca6390|cnss" | head -6); do
	echo "$d -> $(readlink /sys/bus/platform/devices/$d/driver 2>/dev/null || echo UNBOUND)"
done
echo "== modules =="
ls /lib/modules 2>/dev/null || ls /vendor/lib/modules 2>/dev/null | head -5