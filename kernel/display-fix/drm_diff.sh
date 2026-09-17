#!/bin/bash
U=/root/utsav/kernel_xiaomi_sm8250-android14-stable/drivers/gpu/drm
for f in drm_atomic.c drm_sysfs.c drm_ioctl.c drm_mipi_dsi.c; do
	echo "===== $f ====="
	diff /root/sbx/drivers/gpu/drm/$f $U/$f | head -25
done