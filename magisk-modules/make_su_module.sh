#!/system/bin/sh
# Create a Magisk module that provides /system/bin/su via magic mount
M=/data/adb/modules/su_path
mkdir -p $M/system/bin

# The magisk binary doubles as su (multi-call: invoked as "su" → su mode)
cp /data/adb/magisk/magisk $M/system/bin/su
chmod 6755 $M/system/bin/su
chown root:root $M/system/bin/su

cat > $M/module.prop << EOF
id=su_path
name=SU path provider
version=1.0
versionCode=1
author=h8
description=Provides /system/bin/su via module magic mount (kernel blocks Magisk's own overlay)
EOF

touch $M/update
rm -f $M/disable
echo "module created:"
ls -la $M/system/bin/su
cat $M/module.prop | head -3