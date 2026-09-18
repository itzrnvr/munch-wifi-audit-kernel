#!/bin/bash
# integrate_blclone.sh — add bl_clone as built-in to /root/sbx
set -e
cd /root/sbx
cp /mnt/d/kernel-build/bl_clone_builtin.c drivers/misc/bl_clone.c

# Kconfig entry
if ! grep -q "BL_CLONE" drivers/misc/Kconfig; then
  sed -i '/^endmenu/i \
config BL_CLONE\n\
\tbool "Backlight brightness_clone bridge (HyperOS HAL)"\n\
\tdefault y\n\
\thelp\n\
\t  Writable brightness_clone bin_attribute on panel0-backlight.\n' drivers/misc/Kconfig
fi

# Makefile: add object + include paths for techpack headers
if ! grep -q "bl_clone" drivers/misc/Makefile; then
  cat >> drivers/misc/Makefile <<'EOF'

ccflags-$(CONFIG_BL_CLONE) += -I$(srctree)/techpack/display/msm/dsi
ccflags-$(CONFIG_BL_CLONE) += -I$(srctree)/techpack/display/msm/sde
ccflags-$(CONFIG_BL_CLONE) += -I$(srctree)/techpack/display/msm
ccflags-$(CONFIG_BL_CLONE) += -I$(srctree)/techpack/display
ccflags-$(CONFIG_BL_CLONE) += -I$(srctree)/include/drm
obj-$(CONFIG_BL_CLONE) += bl_clone.o
EOF
fi

./scripts/config --enable CONFIG_BL_CLONE
yes '' | make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null 2>&1
grep -E "^CONFIG_BL_CLONE=" .config
echo INTEGRATED