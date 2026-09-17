#!/system/bin/sh
# bl_clone boot script — loads the backlight bridge kernel module and starts
# the brightness daemon.
#
# Lives in /data/adb/service.d/ (standalone script) instead of a Magisk
# module, because Magisk's bootloop protection keeps auto-disabling the
# bl_clone module directory on this device.
#
# Why the module exists at all:
#   The sandboXimi kernel's panel0-backlight kobject has no sysfs store, so
#   neither the HAL nor root can write /sys/class/backlight/.../brightness.
#   bl_clone.ko adds a *bin_attribute* "brightness_clone" (bin_attributes
#   carry their own write handler, so they bypass the broken kobject) and
#   clears the panel gates (panel_initialized, bl_enable, hbm_51_ctrl_flag,
#   ESD status mode) before pushing the value through
#   backlight_device_set_brightness().
#
# Why the screen is pinned on:
#   A panel disable (screen off) leaves the DSI cmd engine refcount
#   inconsistent - dsi_display_cmd_engine_enable() then fails with -EINVAL
#   and every DCS transfer times out, which drives the Qualcomm HWC into a
#   DisplayPowerReset loop that never recovers. Until that kernel race is
#   patched, the panel must not be disabled, so we pin the screen on.

BL_DEV=/sys/class/backlight/panel0-backlight
BL_CLONE="$BL_DEV/brightness_clone"
KO=/data/adb/bl_clone.ko

# --- wait for the panel driver, then load the module ---
for i in $(seq 1 90); do
	[ -f "$BL_DEV/brightness" ] && break
	sleep 1
done

lsmod 2>/dev/null | grep -q bl_clone || insmod "$KO" 2>/dev/null
[ ! -f "$BL_CLONE" ] && exit 1

# --- pin the screen on (see header) ---
svc power stayon true 2>/dev/null
settings put system screen_off_timeout 2147483647 2>/dev/null
settings put system screen_brightness_mode 0 2>/dev/null

# --- brightness bridge: Android setting -> brightness_clone ---
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