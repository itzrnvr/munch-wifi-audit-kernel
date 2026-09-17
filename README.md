# munch-wifi-audit-kernel

Custom kernel for **POCO F4 (munch)** with QCACLD frame injection, monitor mode RX, and EAPOL capture — running on HyperOS (Android 14).

## What This Is

A custom 4.19.300 kernel (based on sandboXimi/android_kernel_xiaomi_munch, branch oni-1.0-staging) with:

- **Frame injection** — mdk4 beacon flood / deauth at 500+ pkt/s
- **Monitor mode RX** — 802.11 frames captured to pcap via AF_PACKET (beacons, probes, data, EAPOL)
- **Erofs support** — boots HyperOS V816 (erofs system partition, requirement bit 0 = LZ4_0PADDING)
- **Permanent flash** — boot_a + boot_b flashed, every reboot loads the custom kernel
- **Root** — Magisk v30.7 debug build preserved in ramdisk

## Quick Start

### On the phone (root shell):

```sh
# Switch to monitor mode on channel 6
su -c sh /data/local/tmp/mon-on 6

# Capture 60s to pcap
su -c sh /data/local/tmp/eapol 6 /data/local/tmp/cap.pcap 60

# Back to normal Wi-Fi
su -c sh /data/local/tmp/mon-off
```

### Deauth (force EAPOL handshake):

```sh
su -c /data/local/kali/kali-arm64/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 \
  --library-path /data/local/kali/kali-arm64/usr/lib/aarch64-linux-gnu/ \
  /data/local/kali/kali-arm64/usr/sbin/mdk4 wlan0 d -t a
```

### On the PC:

```sh
adb pull /data/local/tmp/cap.pcap
hashcat -m 22000 cap.pcap wordlist.txt
```

## Build

### Prerequisites

- WSL (Ubuntu 24.04 or similar) on a Windows PC
- Phone connected via USB ADB (rooted, unlocked bootloader)
- ~5GB disk space

### Toolchain Setup

```sh
# In WSL (UbuntuH8):
apt-get install gcc-aarch64-linux-gnu make bc flex bison libssl-dev openssl cpio python3 python-is-python3 git patch xz-utils

# Install GCC-11 cross compiler (from jammy debs):
mkdir -p /opt/gcc11 && cd /opt/gcc11
for f in cpp-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb \
         gcc-11-aarch64-linux-gnu_11.4.0-1ubuntu1~22.04.3cross1_amd64.deb \
         libgcc-11-dev-arm64-cross_11.4.0-1ubuntu1~22.04.3cross1_all.deb; do
  wget -q "http://archive.ubuntu.com/ubuntu/pool/main/g/gcc-11-cross/$f"
  dpkg -x "$f" root
done

# Install binutils-2.38 (from jammy, to avoid 2.42 "dangerous relocation" bug):
mkdir -p /opt/bu238 && cd /opt/bu238
for f in binutils-aarch64-linux-gnu_2.38-4ubuntu2.12_amd64.deb \
         binutils-common_2.38-4ubuntu2.12_amd64.deb \
         libbinutils_2.38-4ubuntu2.12_amd64.deb; do
  wget -q "http://archive.ubuntu.com/ubuntu/pool/main/b/binutils/$f"
  dpkg -x "$f" root
done

# Install libc6-dev (arm64, for headers):
mkdir -p /root/dev && cd /root/dev
wget -q http://deb.debian.org/debian/pool/main/g/glibc/libc6-dev_2.36-9+deb12u14_arm64.deb
dpkg -x libc6-dev_2.36-9+deb12u14_arm64.deb .
```

### Kernel Build

```sh
# Clone the source
git clone --depth 1 -b oni-1.0-staging --single-branch \
  https://github.com/sandboXimi/android_kernel_xiaomi_munch.git /root/sbx

# Apply the injection patch
cd /root/sbx
patch -p1 --forward < qcacld_injection.patch

# Apply all tree fixes
python3 fix_tree.py

# Add the specific monitor RX fixes (see patches/ directory)
python3 fix_iup.py          # IFF_UP force in callbacks
python3 fix_link_state.py   # __LINK_STATE_START force
python3 fix_mon_cbk.py      # netif_receive_skb in hdd_mon_rx_packet_cbk

# Configure
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- vendor/munch_defconfig
./scripts/config -e SPECTRA_CAMERA -e EROFS_FS -e EROFS_FS_ZIP -e EROFS_FS_SECURITY \
  -e EROFS_FS_USE_VM_MAP_RAM -e FEATURE_FRAME_INJECTION_SUPPORT -e FEATURE_MONITOR_MODE_SUPPORT
./scripts/config -d DEBUG_FS  # MUST stay off (52MB kernels crash)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig

# Ensure LITHIUM and PKT_CAPTURE are set in the qcacld Kbuild
# (see fix_tree.py for the CONFIG_LITHIUM := y + CONFIG_WLAN_FEATURE_PKT_CAPTURE := y prepend)

# Build
export PATH="/opt/bu238/root/usr/bin:/opt/gcc11/root/usr/bin:$PATH"
export LD_LIBRARY_PATH="/opt/bu238/root/usr/lib/x86_64-linux-gnu"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j16 Image.gz-dtb
```

### Package and Flash

```sh
# Swap kernel into Magisk-debug boot image
python3 swap_kernel.py debug-boot.img arch/arm64/boot/Image boot-custom.img

# Flash permanently
fastboot flash boot_a boot-custom.img
fastboot flash boot_b boot-custom.img
fastboot reboot
```

## Architecture

### Key Patches Applied

#### 1. Injection Patch (qcacld_injection.patch)
From Loukious/android_kernel_xiaomi_sm8150 (commit 18c57c6). Adds:
- `wlan_hdd_frame_inject.c` + supporting files (frame injection framework)
- `wlan_hdd_rx_monitor.c` modifications (injection hooks on monitor enable)
- Hidden STA vdev bypass (firmware drops mgmt TX from monitor vdev unless vdev type = 2/6; the patch creates a hidden STA vdev and swaps vdev_id on TX)

#### 2. LITHIUM (`CONFIG_LITHIUM := y`)
Without LITHIUM, `wlan_hdd_rx_monitor.o` compiles as **empty stubs** (the real monitor RX code is gated behind `#ifdef CONFIG_LITHIUM`). Set at the top of `drivers/staging/qcacld-3.0/Kbuild`.

#### 3. Capture Mode Force (`cds_api.c` + `wma_dev_if.c`)
The SandBoXimi tree stripped the INI wiring that sets `enable_pkt_capture_support` and `val_pkt_capture_mode`. Without these, the WMI `VDEV_PARAM_PACKET_CAPTURE_MODE` (0x93) is never sent to the firmware, and the firmware never delivers monitor frames.

Fixed by:
- `cds_api.c`: `cds_is_pktcapture_enabled()` returns `true`; `cds_get_pktcapture_mode()` returns `PKT_CAPTURE_MODE_DATA_MGMT`
- `wma_dev_if.c`: `wma_send_pkt_capture_mode()` exported wrapper, called from:
  - `hdd_enable_monitor_mode()` (in `wlan_hdd_rx_monitor.c`)
  - `wlan_hdd_set_mon_chan()` (in `wlan_hdd_main.c`)

#### 4. Monitor RX Delivery (`wlan_hdd_rx_monitor.c`)
The `hdd_rx_monitor_callback` (the function the LITHIUM DP calls for monitor frames) had three issues:

1. **`netif_rx_ni()` for last packet** — the callback runs in NAPI/softirq context; `netif_rx_ni()` calls `local_bh_enable()` inside softirq → drops. Fixed: use `netif_receive_skb()` (inline delivery).

2. **Interface not UP** — the driver's monitor vdev restart (from `setMonChan`) clears `IFF_UP` and `__LINK_STATE_START`. The kernel's `__netif_receive_skb_core()` (dev.c:4249) checks `netif_running()` and drops every frame. Fixed: force `skb->dev->flags |= IFF_UP` + `set_bit(__LINK_STATE_START, &skb->dev->state)` before delivery.

3. **Chain pointers** — `skb->next` not cleared before delivery → potential stack confusion. Fixed: `skb->next = NULL; skb->prev = NULL;`.

#### 5. Modern Erofs Transplant (LineageOS)
The sandboXimi tree's staging erofs driver supports `EROFS_ALL_REQUIREMENTS = 0` (rejects everything). HyperOS V816's system image uses erofs with requirement bit 0 (`LZ4_0PADDING`). Fixed by transplanting `fs/erofs/` from LineageOS android_kernel_xiaomi_sm8250 (lineage-21 branch, kernel 4.19.318):

- Replace `drivers/staging/erofs/` with LineageOS `fs/erofs/` (modern zdata/zmap/decompressor)
- Backport `attach_page_private`/`detach_page_private` helpers to `include/linux/pagemap.h`
- Add `EROFS_SUPER_MAGIC_V1` to `include/uapi/linux/magic.h`
- Replace `lib/lz4/` with LineageOS version (has `LZ4_decompress_safe_partial`)

#### 6. `CONFIG_WLAN_FEATURE_PKT_CAPTURE`
Enables the `components/pkt_capture/` subsystem in qcacld. The WMI capture mode param (0x93) is the firmware-side switch that tells the WiFi chip to deliver raw 802.11 frames to the monitor ring buffers. Without it, the firmware delivers nothing.

### Build Fixes (fix_tree.py)

The sandboXimi tree is clang-built; GCC-11 needs:
- `-Wno-maybe-uninitialized -Wno-format -Wno-misleading-indentation -Wno-unused-but-set-variable -Wno-array-parameter` (GCC vs clang warnings)
- `-B/opt/bu238/root/usr/bin/aarch64-linux-gnu- -fno-PIE -fno-pie` (binutils + PIE fixes)
- TRACE_INCLUDE_PATH fix (clang include-stack semantics differ from GCC)
- `extern inline` → `extern` (C99 vs clang)
- Float-to-integer Q16 conversion in bq2597x charger (GCC `-mgeneral-regs-only` bans float)
- `gcc-wrapper.py` pass-through (QCOM warning policy wrapper is Python 2 + bytes/str broken)
- Duplicate `DEVICE_ATTR` pair in xiaomi_touch.c
- Focaltech firmware stubs (`.i` files stripped from OSS release)
- IPA fortify bounds + wcd-mbhc debugfs macro defines
- `CONFIG_DYNAMIC_DEBUG=n` (binutils 2.42 "dangerous relocation" on ABS64-in-.data)

### Magisk Module (wifi_pktcap)

Overlays `/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini` with `packet_capture_mode=3` appended. Without this, the WiFi driver probe fails ("Failed to probe host driver") because the kernel's firmware loader can't find the config INI at the driver's expected path.

## Tools

### pcapcap (static arm64)
Minimal AF_PACKET pcap recorder. Opens `SOCK_RAW` on `ETH_P_ALL`, binds to the monitor interface, captures frames with `select()` + `recv()` timeout loop, writes pcap with `DLT_IEEE802_11_RADIOTAP` (linktype 127).

### iwpriv (static arm64, wireless-tools 30)
The REAL iwpriv (not a hand-rolled replacement). Discovers private ioctls via `SIOCGIWPRIV` and sends them with correct encoding. Required because the hand-rolled `setmonchan` tool had the subcmd encoding wrong (`value[0]` is the subcmd, not `u.data.flags`; `u.data.length` is in bytes, not ints).

### rawcount (static arm64)
Diagnostic tool — opens AF_PACKET socket, counts frames received in N seconds. Used to verify monitor RX delivery without pcap overhead.

### mdk4 (from Kali chroot)
WiFi injection tool. Runs via the Kali chroot's dynamic loader + libs:
```
/data/local/kali/kali-arm64/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 \
  --library-path /data/local/kali/kali-arm64/usr/lib/aarch64-linux-gnu/ \
  /data/local/kali/kali-arm64/usr/sbin/mdk4 wlan0 <mode> [options]
```

## Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `mon-on` | `/data/local/tmp/mon-on` | Switch to monitor mode on given channel |
| `mon-off` | `/data/local/tmp/mon-off` | Back to station mode + re-enable Wi-Fi |
| `eapol` | `/data/local/tmp/eapol` | Wrapper: mon-on + pcapcap |

## Key Files on Phone

| File | Path |
|------|------|
| iwpriv | `/data/local/kali/kali-arm64/root/iwpriv` |
| pcapcap | `/data/local/kali/kali-arm64/root/pcapcap` |
| rawcount | `/data/local/kali/kali-arm64/root/rawcount` |
| mdk4 | `/data/local/kali/kali-arm64/usr/sbin/mdk4` |
| Kali libs | `/data/local/kali/kali-arm64/usr/lib/aarch64-linux-gnu/` |
| Magisk module | `/data/adb/modules/wifi_pktcap/` |
| Boot backup | `D:/kernel-build/boot_backup_20260915.img` (on PC) |

## Known Limitations

- **hcx6 (hcxdumptool)** gets 0 packets because it uses `PACKET_MMAP` ring setup which fails when the interface is administratively DOWN. Use `pcapcap` instead (plain `AF_PACKET + recv()`).
- **DEBUG_FS** must stay off — kernels with `CONFIG_DEBUG_FS=y` (52.88MB) crash pre-USB on this firmware. The 50.76MB builds boot fine.
- **Channel switching** requires the real `iwpriv` tool (not a hand-rolled ioctl caller) — the private ioctl encoding is non-trivial (`value[0]` = subcmd, `u.data.length` in bytes).
- The monitor interface doesn't stay administratively UP (the driver's vdev restart clears it). The kernel patches force `IFF_UP` + `__LINK_STATE_START` per-frame in the RX callback.

## Credits

- [sandboXimi](https://github.com/sandboXimi) — kernel source tree (android_kernel_xiaomi_munch, oni-1.0-staging)
- [Loukious](https://github.com/Loukious) — QCACLD injection patch (sm8150, commit 18c57c6 / 65c6a05)
- [kimocoder](https://github.com/kimocoder/qualcomm_android_monitor_mode) — Qualcomm monitor mode reference
- [LineageOS](https://github.com/LineageOS/android_kernel_xiaomi_sm8250) — modern erofs backport (4.19.318)
- [MiCode](https://github.com/MiCode/Xiaomi_Kernel_OpenSource) — munch-s-oss kernel source (reference)
- [ZerBea](https://github.com/ZerBea/hcxdumptool) — hcxdumptool (capture tool reference)

---

# The Display Fix (2026-09-17): MIUI Display Driver Port

## Symptom

After the first boot of the original kernel the panel showed **backlight
but no UI**. After the first screen-off the DSI command engine corrupted
(`dsi_display_cmd_engine_enable rc=-22`, thousands of `Command transfer
failed`) and the Qualcomm HWC entered an endless `DisplayPowerReset` loop,
cycling the screen every ~9 s forever.

## Root Cause

The sandboXimi tree (`oni-1.0-staging`) ships the **AOSP display
drivers**. HyperOS's display HAL expects the **MIUI variant** of the
techpack/display stack plus MIUI-specific core-DRM hooks. With the AOSP
variant the panel never scans out — a known sm8250 community issue
(documented in liyafe1997/kernel_xiaomi_sm8250_mod's README: "AOSP版因为
display驱动不同，在HyperOS/MIUI上屏幕无法正常显示…开机黑屏").

## The Fix

`kernel/display-fix/port_miui_display.sh` ports the MIUI display stack
from **UtsavBalar1231/kernel_xiaomi_sm8250** (android14-stable) into the
sandboXimi tree:

| Component | Change |
|---|---|
| `techpack/display/` | replaced wholesale (51 files: DSI ctrl/display/panel + MI variants, SDE connector/encoder/kms, PHY) |
| `drivers/gpu/drm/` | 12 files + `drm_internal_mi.h` — `connector_kdev`, MIUI sysfs (`disp_param`), ioctl master filter, mipi_dsi attach guards. `drm_atomic.c` kept from sandboXimi (carries the devfreq boost, no MIUI content in Utsav's copy) |
| `include/drm/drm_mipi_dsi.h` | `struct mipi_dsi_device::attached` member |
| DTS | `dsi-panel-l11r-38-08-0a-dsc-cmd.dtsi` (adds the 90 Hz timing), `kona-sde-display.dtsi`, `kona-sde.dtsi`, `munch-sm8250.dtsi` + 100 panel dtsi includes |
| build fixes | `pll_trace.h` TRACE_INCLUDE_PATH, `sde_fence.c` `get_unused_fd_flags()` (removed API), focaltech `*.i` firmware stubs |

Rebuild with the same GCC-11/binutils-2.38 toolchain (`build_miui.sh`),
swap the raw `Image` into a stock-format boot image (`swap_kernel.py`),
flash to `boot_a` + `boot_b`.

### Result

- Panel binds, HyperOS HAL drives natively (`dsi_panel_set_backlight` in
  dmesg at boot), `brightness_clone` created by the driver itself
- **0** DSI command failures, **0** commit timeouts, no HWC recovery loop

## The bl_clone backlight module (`kernel/display-fix/bl_clone.c`)

On the AOSP-driver kernel the backlight kobject's `sysfs_ops` had no
`store` (every write → EACCES) so nothing — not even root — could set
brightness. `bl_clone.ko` adds a **bin_attribute** `brightness_clone`
(bin_attributes carry their own write handler, bypassing the broken
kobject) and clears the panel gates (`panel_initialized`, `bl_enable`,
`hbm_51_ctrl_flag`, ESD status mode) before calling
`backlight_device_set_brightness()`.

The kernel has `CONFIG_MODULE_SIG_FORCE=y` (hidden from `/proc/config.gz`
but present in the build `.config`), so the module must be signed with
the build tree's own key:

```sh
/root/sbx/scripts/sign-file sha512 \
    /root/sbx/certs/signing_key.pem /root/sbx/certs/signing_key.x509 bl_clone.ko
```

With the MIUI display port the native path works, so the module is
mostly a fallback — but `magisk-module/` and `tools/bl_clone_service.sh`
(installed at `/data/adb/service.d/`, immune to Magisk's module
bootloop-protection `disable` files) keep a phone bootable even if the
AOSP tree is accidentally rebuilt.

## Boot script persistence

Magisk's bootloop protection kept auto-disabling the bl_clone *module
directory* after several crash-reboots. Standalone scripts under
`/data/adb/service.d/` are unaffected — `tools/bl_clone_service.sh`
loads the module, pins the screen on (the AOSP driver's panel-disable
path is what corrupts the DSI cmd engine), and runs a small bridge daemon
polling Android's `screen_brightness` into `brightness_clone`.
