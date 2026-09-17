#!/system/bin/sh
# post-fs-data.sh — load bl_clone module early (before HALs start)
# If the backlight device isn't ready yet, insmod fails silently;
# service.sh will retry. This is just a best-effort early load.

MODDIR=/data/adb/modules/bl_clone
insmod "$MODDIR/bl_clone.ko" 2>/dev/null
