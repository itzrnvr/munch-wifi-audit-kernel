#!/system/bin/sh
# su_overlay_final.sh — watchdog-protected su overlay install
OV=/data/adb/.su_ovl
MP=/data/adb/magisk/magiskpolicy
OKF=/data/local/tmp/su_ok

rm -f $OKF
umount /system/bin 2>/dev/null

# 1. arm the watchdog (90s, syscall umount, no shell deps)
/data/local/tmp/su_watchdog &
WD=$!

# 2. live sepolicy: allow the associate that got denied
$MP --live "allow system_file system_file filesystem associate" >/dev/null 2>&1
$MP --live "allow shell system_file filesystem associate" >/dev/null 2>&1
$MP --live "allow magisk system_file filesystem associate" >/dev/null 2>&1
$MP --live "allow untrusted_app system_file filesystem associate" >/dev/null 2>&1

# 3. prepare overlay
rm -rf $OV && mkdir -p $OV/upper $OV/work
cp /debug_ramdisk/su $OV/upper/su
chmod 6755 $OV/upper/su
chown root:shell $OV/upper/su

# 4. mount with unified system_file label
mount -t overlay overlay -o lowerdir=/system/bin,upperdir=$OV/upper,workdir=$OV/work,context=u:object_r:system_file:s0 /system/bin
RC=$?
echo "mount rc=$RC"
[ $RC -ne 0 ] && { kill $WD 2>/dev/null; echo MOUNT_FAILED_SAFE; exit 1; }

# 5. verify from magisk context first
if /system/bin/su -c "id" 2>&1 | head -1; then
	echo "MAGISK_CTX_OK — now test fresh shell within 90s"
else
	echo "MAGISK_CTX_BROKEN — watchdog will clean up"
	exit 1
fi
# watchdog stays armed; PC-side fresh-shell test decides via su_ok file