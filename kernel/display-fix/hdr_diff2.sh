#!/bin/bash
U=/root/utsav
echo "== mipi_dsi.h diff =="
diff /root/sbx/include/drm/drm_mipi_dsi.h $U/include/drm/drm_mipi_dsi.h | head -40
echo "== all include/drm diffs =="
diff -rq /root/sbx/include/drm $U/include/drm 2>/dev/null | grep -v "Only in /root/sbx" | head -10