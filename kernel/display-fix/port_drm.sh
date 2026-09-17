#!/bin/bash
U=/root/utsav/kernel_xiaomi_sm8250-android14-stable/drivers/gpu/drm
cd /root/sbx/drivers/gpu/drm || exit 1
for f in drm_sysfs.c drm_ioctl.c drm_mipi_dsi.c drm_crtc.c drm_drv.c drm_file.c drm_framebuffer.c drm_mm.c drm_notifier_mi.c drm_plane.c drm_property.c; do
	cp "$U/$f" "$f" && echo "copied $f"
done
cp "$U/drm_internal_mi.h" drm_internal_mi.h && echo "copied drm_internal_mi.h"
if ! diff -q Makefile "$U/Makefile" > /dev/null 2>&1; then
	cp "$U/Makefile" Makefile && echo "copied Makefile"
else
	echo "Makefile identical"
fi
echo "connector_kdev refs: $(grep -c connector_kdev drm_sysfs.c)"