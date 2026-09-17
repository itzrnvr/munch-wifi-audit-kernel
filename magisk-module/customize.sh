#!/system/bin/sh
# customize.sh — manual extraction + script creation for bl_clone module
SKIPUNZIP=1

ui_print "- Installing bl_clone module files..."

# Extract all files manually
unzip -o "$ZIPFILE" bl_clone.ko -d "$MODPATH" 2>/dev/null
unzip -o "$ZIPFILE" module.prop -d "$MODPATH" 2>/dev/null
unzip -o "$ZIPFILE" post-fs-data.sh -d "$MODPATH" 2>/dev/null
unzip -o "$ZIPFILE" service.sh -d "$MODPATH" 2>/dev/null

# If unzip failed for scripts, write them manually as fallback
if [ ! -f "$MODPATH/post-fs-data.sh" ]; then
  echo '#!/system/bin/sh' > "$MODPATH/post-fs-data.sh"
  echo 'insmod /data/adb/modules/bl_clone/bl_clone.ko 2>/dev/null' >> "$MODPATH/post-fs-data.sh"
  ui_print "- post-fs-data.sh written manually"
fi

if [ ! -f "$MODPATH/service.sh" ]; then
  echo '#!/system/bin/sh' > "$MODPATH/service.sh"
  echo 'MODDIR=/data/adb/modules/bl_clone' >> "$MODPATH/service.sh"
  echo 'BL_DEV=/sys/class/backlight/panel0-backlight' >> "$MODPATH/service.sh"
  echo 'BL_CLONE=$BL_DEV/brightness_clone' >> "$MODPATH/service.sh"
  echo 'MAX_BRIGHTNESS=2047' >> "$MODPATH/service.sh"
  echo '' >> "$MODPATH/service.sh"
  echo 'for i in $(seq 1 60); do' >> "$MODPATH/service.sh"
  echo '  if [ -f "$BL_DEV/brightness" ]; then' >> "$MODPATH/service.sh"
  echo '    if ! lsmod 2>/dev/null | grep -q bl_clone; then' >> "$MODPATH/service.sh"
  echo '      insmod $MODDIR/bl_clone.ko 2>/dev/null' >> "$MODPATH/service.sh"
  echo '    fi' >> "$MODPATH/service.sh"
  echo '    break' >> "$MODPATH/service.sh"
  echo '  fi' >> "$MODPATH/service.sh"
  echo '  sleep 1' >> "$MODPATH/service.sh"
  echo 'done' >> "$MODPATH/service.sh"
  echo '' >> "$MODPATH/service.sh"
  echo 'if [ ! -f "$BL_CLONE" ]; then exit 1; fi' >> "$MODPATH/service.sh"
  echo '' >> "$MODPATH/service.sh"
  echo 'bl_bridge() {' >> "$MODPATH/service.sh"
  echo '  local last=""' >> "$MODPATH/service.sh"
  echo '  while true; do' >> "$MODPATH/service.sh"
  echo '    b=$(settings get system screen_brightness 2>/dev/null)' >> "$MODPATH/service.sh"
  echo '    if [ -z "$b" ] || [ "$b" = "null" ]; then sleep 2; continue; fi' >> "$MODPATH/service.sh"
  echo '    if [ "$b" != "$last" ]; then' >> "$MODPATH/service.sh"
  echo '      scaled=$(( b * MAX_BRIGHTNESS / 255 ))' >> "$MODPATH/service.sh"
  echo '      [ "$scaled" -gt "$MAX_BRIGHTNESS" ] && scaled=$MAX_BRIGHTNESS' >> "$MODPATH/service.sh"
  echo '      [ "$scaled" -lt 1 ] && scaled=1' >> "$MODPATH/service.sh"
  echo '      echo "$scaled" > "$BL_CLONE" 2>/dev/null && last="$b"' >> "$MODPATH/service.sh"
  echo '    fi' >> "$MODPATH/service.sh"
  echo '    sleep 2' >> "$MODPATH/service.sh"
  echo '  done' >> "$MODPATH/service.sh"
  echo '}' >> "$MODPATH/service.sh"
  echo '' >> "$MODPATH/service.sh"
  echo 'bl_bridge &' >> "$MODPATH/service.sh"
  ui_print "- service.sh written manually"
fi

chmod 755 "$MODPATH/post-fs-data.sh" "$MODPATH/service.sh"
chmod 644 "$MODPATH/bl_clone.ko" "$MODPATH/module.prop"

ui_print "- Module files installed successfully"
