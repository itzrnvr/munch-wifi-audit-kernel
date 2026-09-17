#!/bin/bash
U=/root/utsav/kernel_xiaomi_sm8250-android14-stable
diff /root/sbx/include/drm/drm_mipi_dsi.h $U/include/drm/drm_mipi_dsi.h | head -30
echo === OTHER_INCLUDE_DIFFS
for d in drm; do
	diff -rq /root/sbx/include/$d $U/include/$d 2>/dev/null | grep -v "Only in /root/sbx" | head -8
done