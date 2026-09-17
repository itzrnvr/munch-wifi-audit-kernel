#!/bin/bash
U=/root/utsav/kernel_xiaomi_sm8250-android14-stable/drivers/gpu/drm
for f in drm_crtc.c drm_drv.c drm_file.c drm_framebuffer.c drm_mm.c drm_notifier_mi.c drm_plane.c drm_property.c; do
	OURS_ONLY=$(diff /root/sbx/drivers/gpu/drm/$f $U/$f | grep -c "^<")
	UTSAV_ONLY=$(diff /root/sbx/drivers/gpu/drm/$f $U/$f | grep -c "^>")
	echo "$f: ours_unique=$OURS_ONLY utsav_unique=$UTSAV_ONLY"
done