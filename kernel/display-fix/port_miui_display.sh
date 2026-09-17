#!/bin/bash
# port_miui_display.sh — Port the MIUI display driver stack from
# UtsavBalar1231/kernel_xiaomi_sm8250 (android14-stable) into the
# sandboXimi munch tree, so the kernel works with HyperOS's display HAL.
#
# Background: the sandboXimi tree (oni-1.0-staging) ships AOSP display
# drivers. HyperOS's display HAL expects the MIUI variant; with the AOSP
# variant the panel never scans out (backlight-only black screen, then a
# DSI cmd-engine corruption loop on first screen-off). This is a known
# sm8250 community issue — see the README of liyafe1997/kernel_xiaomi_sm8250_mod.
#
# Usage (inside WSL, with the UtsavBalar1231 tarball already extracted
# to /root/utsav and the sandboXimi tree at /root/sbx):
#   bash port_miui_display.sh
set -e

SBX=/root/sbx
UTSAV=/root/utsav/kernel_xiaomi_sm8250-android14-stable

[ -d "$UTSAV" ] || { echo "utsav tree missing: $UTSAV"; exit 1; }
cd "$SBX"

# 1. Replace the display techpack (keep an AOSP backup OUTSIDE techpack/
#    so kbuild doesn't compile it)
[ -d techpack/display ] && [ ! -d /root/display_aosp_bak ] && \
	mv techpack/display /root/display_aosp_bak
cp -r /root/utsav/techpack/display techpack/display

# 2. Fix TRACE_INCLUDE_PATH in the swapped pll_trace.h (the sandboXimi
#    tree resolves trace includes relative to include/trace/)
sed -i 's|#define TRACE_INCLUDE_PATH \.$|#define TRACE_INCLUDE_PATH ../../techpack/display/pll|' \
	techpack/display/pll/pll_trace.h

# 3. sde_fence.c uses get_unused_fd_start_flags() which was removed in
#    4.19.3xx; use get_unused_fd_flags() (same fd allocation semantics)
sed -i 's|fd = get_unused_fd_start_flags(1, 0);|fd = get_unused_fd_flags(0);|' \
	techpack/display/msm/sde/sde_fence.c

# 4. Board/DTS files (panel timings incl. 90Hz mode, SDE config)
for f in dsi-panel-l11r-38-08-0a-dsc-cmd.dtsi kona-sde-display.dtsi \
		 kona-sde.dtsi munch-sm8250.dtsi; do
	cp "$UTSAV/arch/arm64/boot/dts/vendor/qcom/$f" \
	   "arch/arm64/boot/dts/vendor/qcom/$f"
done
# all panel dtsi includes referenced by the MIUI kona-sde-display.dtsi
cp -n /root/utsav/arch/arm64/boot/dts/vendor/qcom/dsi-panel-*.dtsi \
	   arch/arm64/boot/dts/vendor/qcom/ 2>/dev/null || true

# 5. Core DRM changes (connector_kdev, MIUI sysfs/ioctl, mipi_dsi guards)
#    NOTE: drm_atomic.c is intentionally KEPT from sandboXimi — the Utsav
#    version has no MIUI additions and ours carries the devfreq boost.
U="$UTSAV/drivers/gpu/drm"
for f in drm_sysfs.c drm_ioctl.c drm_mipi_dsi.c drm_crtc.c drm_drv.c \
		 drm_file.c drm_framebuffer.c drm_mm.c drm_notifier_mi.c \
		 drm_plane.c drm_property.c; do
	cp "$U/$f" "drivers/gpu/drm/$f"
done
cp "$U/drm_internal_mi.h" drivers/gpu/drm/drm_internal_mi.h

# 6. Header: struct mipi_dsi_device::attached
cp /root/utsav/include/drm/drm_mipi_dsi.h include/drm/drm_mipi_dsi.h

# 7. Focaltech firmware stubs (stripped from OSS release; make clean
#    removes *.i files, recreate after any clean)
mkdir -p drivers/input/touchscreen/focaltech_3658u/include/firmware
for fw in fw_ft3658_l11r fw_ft3658_L11r fw_sample; do
	printf '0x00' > "drivers/input/touchscreen/focaltech_3658u/include/firmware/$fw.i"
done

echo "MIUI display port applied. Rebuild with GCC-11 (see build_miui.sh)."