#!/system/bin/sh
# zygisk_nudge.sh — if the ZN injector lost the race with zygote at boot,
# restart zygote once so injection lands. Runs from /data/adb/service.d/.
sleep 45
PID=$(pidof zygote64)
[ -z "$PID" ] && exit 0
if grep -qi zygisk /proc/$PID/maps 2>/dev/null; then
	exit 0
fi
# injector missed — restart zygote to re-inject
kill -9 "$PID"
sleep 20
PID=$(pidof zygote64)
grep -qi zygisk /proc/$PID/maps 2>/dev/null && echo "zygisk_nudge: injected on retry" || echo "zygisk_nudge: still missing"