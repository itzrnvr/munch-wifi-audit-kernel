#!/system/bin/sh
# service.sh — loads bl_clone module, keeps screen on, runs bridge daemon.
#
# Context: the DSI cmd-engine state on this kernel is corrupted by a panel
# disable (screen off): dsi_display_cmd_engine_enable() then fails with
# -EINVAL ("Controller state check failed") and every DCS transfer after
# that times out, which sends the Qualcomm HWC into a DisplayPowerReset
# loop (screen cycles on/off every ~9s and never recovers).
#
# Until the kernel-side race is fixed we simply never let the panel go
# through a disable, so the cmd-engine refcount stays balanced:
#   - svc power stayon true   (screen stays on while charging)
#   - screen_off_timeout max  (nothing blanks the panel)
# The screen off→on KEYCODE cycle that earlier revisions did is removed,
# because that cycle is exactly what triggers the corruption.

MODDIR=/data/adb/modules/bl_clone
BL_DEV=/sys/class/backlight/panel0-backlight
BL_CLONE="$BL_DEV/brightness_clone"

# --- Phase 1: wait for backlight device, then load module ---
for i in $(seq 1 60); do
	if [ -f "$BL_DEV/brightness" ]; then
		lsmod 2>/dev/null | grep -q bl_clone || insmod "$MODDIR/bl_clone.ko" 2>/dev/null
		break
	fi
	sleep 1
done

[ ! -f "$BL_CLONE" ] && exit 1

# --- Phase 2: keep the panel enabled (avoid the disable that corrupts DSI) ---
svc power stayon true 2>/dev/null
settings put system screen_off_timeout 2147483647 2>/dev/null
settings put system screen_brightness_mode 0 2>/dev/null

# --- Phase 3: bridge daemon (Android brightness → brightness_clone) ---
(
	while true; do
		b=$(settings get system screen_brightness 2>/dev/null)
		if [ -n "$b" ] && [ "$b" != "null" ]; then
			scaled=$(( b * 2047 / 255 ))
			[ "$scaled" -gt 2047 ] && scaled=2047
			[ "$scaled" -lt 1 ] && scaled=1
			echo "$scaled" > "$BL_CLONE" 2>/dev/null
		fi
		sleep 2
	done
) &