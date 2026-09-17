#!/system/bin/sh
# Simple backlight bridge daemon — polls screen_brightness, writes to brightness_clone
BL=/sys/class/backlight/panel0-backlight/brightness_clone
LOG=/data/local/tmp/bl_poll.log
rm -f "$LOG"
while true; do
	b=$(settings get system screen_brightness 2>/dev/null)
	echo "poll b=$b" >> "$LOG"
	if [ -n "$b" ] && [ "$b" != "null" ]; then
		scaled=$(( b * 2047 / 255 ))
		[ "$scaled" -gt 2047 ] && scaled=2047
		[ "$scaled" -lt 1 ] && scaled=1
		echo "$scaled" > "$BL" 2>/dev/null
	fi
	sleep 2
done
