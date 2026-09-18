# KernelSU v0.9.5 on munch (sm8250, kernel 4.19, HyperOS)

Proven-working root for POCO F4 (munch) on the sandboXimi-derived 4.19 tree
with the MIUI display port. KernelSU-Next v3.3+ does NOT work on this kernel:
it patches the syscall table via fixmap/stop_machine at boot and panics
before userspace (no adb, falls to fastboot). v0.9.5 uses kprobe/manual hooks
and boots clean.

## Integration (what was done)

1. `drivers/kernelsu` -> KernelSU-0.9.5/kernel (symlink or copy)
2. `drivers/Makefile`: `obj-$(CONFIG_KSU) += kernelsu/`
   `drivers/Kconfig`: `source "drivers/kernelsu/Kconfig"`
3. Config: `CONFIG_KSU=y`, `CONFIG_KPROBES=y`, `CONFIG_KPROBE_EVENTS=y`,
   `CONFIG_OVERLAY_FS=y`
4. Manual hook call sites (kprobes alone unreliable here), see
   `patch_manual_hooks.py`:
   - fs/exec.c do_execveat_common: ksu_handle_execveat + sucompat
   - fs/open.c do_faccessat: ksu_handle_faccessat
   - fs/read_write.c vfs_read: ksu_handle_vfs_read
   - fs/stat.c newfstatat: ksu_handle_stat
5. Version define: tarball builds lack .git, Makefile falls back to
   `-DKSU_VERSION=16`; manager (11872) rejects it. Set
   `-DKSU_VERSION=11872` (or build from a git checkout).

## Allowlist binary format (/data/adb/ksu/.allowlist)

u32 magic 0x7f4b5355 ("USK\x7f"), u32 FILE_FORMAT_VERSION=3, then raw
`struct app_profile` records (776 bytes, see kernel/ksu.h):
  u32 version (=2), char key[256] (pkg name), i32 current_uid, bool allow_su,
  union rp/nrp config (selinux_domain "u:r:su:s0" at record offset 700).
No count field; records read until EOF. Loaded once at boot — edits need a
reboot. UID changes on app reinstall; stale uid = silent EACCES on su exec
(sucompat only redirects allowed uids; others hit the /system/bin/su decoy).

## MIUI/HyperOS host quirks (cost hours; do not rediscover)

- Sideloaded APKs get DELETED minutes after install by MIUI security
  (com.miui.securitycore / guardprovider / cleaner). Disable them:
  `pm disable-user --user 0 <pkg>`.
- `am start` of third-party activities from shell uid = Error type 3;
  from root (su -c) it works.
- Input injection from shell denied; from root OK.
- /system/bin/su and /product/bin/su are Magisk-era decoys on this device;
  KSU sucompat intercepts /system/bin/su execve for allowed uids and
  redirects to /data/adb/ksud. Always call the absolute path.
- `iw dev wlan0 set channel` on the STA iface kills the qcacld scheduler
  thread (driver half-death: "Cannot post message; scheduler thread is
  stopped"); recover only via wifi toggle or reboot.

## Inject-channel patch (patch_inject_channel.py, applied 2026-09-18)

One-time qcacld patch so USERSPACE controls the injection TX channel:
- struct inject_frame_req += tx_chanfreq
- hdd_monitor_mode_tx_inject parses the radiotap channel field (present
  bit 3) into req->tx_chanfreq
- wma_frame_inject.c: if vdev mhz == 0, fall back to req->tx_chanfreq
  (kills the cold-boot "zero channel frequency" drop)

Result: injections now pass WMA and go out via the WMI mgmt-tx path on the
internal "hidden AP vdev 2" (log: "using hidden AP vdev 2 for TX").
On-air channel steering still NOT achieved: the mgmt-tx path transmits on
the hidden vdev's own channel, not the requested chanfreq (sweep found no
spoofed frames on 1/6/11/36/44 during a cold-boot app-driven burst).
The proven on-air path remains the monitor-vdev-with-mhz recipe in
radio/LIMITATIONS.md. Next dive: make the mgmt-tx path honor chanfreq, or
steer the hidden vdev's channel from userspace (observe via the app Debug
tab: /sys/kernel/frame_injection/* + dmesg presets).

## KSU-Next v3.3 on 4.19: status (2026-09-19)

- v3.3 hooks via tracepoints (syscall_hook_manager) + runtime syscall-table
  patching; NO manual-hook API (original-KSU manual hook sites must be
  STRIPPED from fs/*.c or link fails: strip_manual_hooks.py).
- BISECT gates in core/init.c: stage0=full, 1=hooks+manager off, 2=fully
  disabled (control). Stage1 and stage2 BOOT CLEAN on 4.19.
- Stage2 manager shows "Unsupported | Not integrated" BY DESIGN (init
  returns early). Stage0 full-mode "bootloop" was MISDIAGNOSED: pstore
  (console-ramoops) proves the panic is an MHI driver race, NOT KSU:
  `mhi_netdev_remove -> unregister_netdev -> rollback_registered ->
  flush_work -> check_flush_dependency BUG` in kworker mhi_w, triggered by
  WLAN MHI state transitions (wifi service toggles / SSR). This same race
  explains the session-long "random phone deaths".
- Manager (:root daemon) crashes on Android 14 with "Writable dex file
  ... not allowed" (W^X); grants via supercall still possible from UI.
- Conclusion: original KSU v0.9.5 remains the working root on this device;
  KSU-Next needs (a) deferred (process-context) text patching for stage0
  on 4.19 and (b) an MHI netdev remove-race fix for stability. Both are
  targeted patches for a future session; pstore methodology above is the
  diagnostic template.

## FINAL KSU-Next verdict (2026-09-19)

- Tarball builds report KSU_VERSION=1/v0.0.1 (Kbuild fallback) -> manager
  shows "Unsupported". patch_ksu_version.sh forces 33214/v3.3.0.
- Even with correct version, manager says "Not integrated": KSU-Next IPC
  (supercall) rides the RUNTIME syscall-table patch performed by
  syscall_hook_manager_init; on this 4.19 vendor kernel that patch path is
  unreliable (stage0 panics at init; stage3 boots but patch silently fails
  -> supercall never answers). Bisect gates: stage1/stage2/stage3 all boot.
- Zygisk/PIF therefore unavailable on original KSU v0.9.5 (no zygisk core)
  AND on KSU-Next/4.19 (IPC dead). ReZygisk standalone needs a root impl
  with zygisk core (KSU-Next/APatch) — same blocker.
- NEXT-DIVE PLAN for zygisk/PIF: make KSU-Next syscall-table patching
  4.19-safe: defer patch to process-context workqueue at boot, verify
  supercall responds (manager "Working"), then modules dir + zygisk + PIF.
  Until then: original KSU v0.9.5 = the working root (boot-injchan.img).

**RESTORED + RE-VERIFIED (2026-09-19)**: boot-injchan.img flashed back to
boot_a+boot_b. Post-boot pass: boot_completed=1, su uid=0, wifi scan 105
APs, attack mode con_mode=4, 100/100 deauth frames on-air to the Fabiola
BSSID with firmware status=OK (tx_chanfreq=2437), STA mode restored,
sleep/wake brightness 536 -> 0 -> 336 with live panel. See
../radio/LIMITATIONS.md for the full matrix. KSU-Next images remain on
D:/kernel-build (boot-ksunext-*.img) for the next dive.

## ZYGISM PATH UNBLOCKED (2026-09-19, later) — dual-root discovery

Research corrected the earlier "zygisk impossible on KSU 0.9.5" verdict:
- KSU never had built-in zygisk by design; the standard path is a standalone
  provider module (ZygiskNext / ReZygisk / NeoZygisk). PIF (osm0sis v18)
  explicitly supports "KernelSU + ReZygisk/ZygiskNext/NeoZygisk".
- ReZygisk v1.0.0 requirements: kernel >= 10940 (ours = 11872 OK after the
  KSU_VERSION fix) + ksud >= 11425 (0.9.5 = OK).

Real blocker found: the flashed boot image was DUAL-ROOT — kernel runs
KernelSU 0.9.5 but the ramdisk still has magiskinit injected
(`/debug_ramdisk/magisk` + magiskd PID live, `.backup/.magisk` in ramdisk,
all three local images: injchan / clean-rd / backup-20260915 are
Magisk-patched). KSU's module system DID work (modules.img ext4 loop40
mounted, wififix `KSU /system|/vendor overlay` live — classic ksud 0.9.5
uses modules.img by design), but the magisk conflict message + ReZygisk's
"multiple root" check trip on it.

Fix built (staged, NOT flashed): **D:/kernel-build/boot-clean-final.img**
(sha256 2a3ec836ff9a6a6855ddbce091a74c920a7c476c58c01eaf76141786f2eaeef2)
= final kernel (Image #44, 4.19.157-perf + KSU 0.9.5 + injchan + bl_clone
v2) + magiskboot-`cpio restore`-de-magisked stock ramdisk (test=0, /init
symlink, first_stage_ramdisk intact, kernel sha256 verified identical).

ReZygisk installed: `ksud module install` of the v1.0.0 zip FAILED on
sepolicy.rule `#` comment lines ("Failed to parse policy statement") —
KSU 0.9.5's policy parser doesn't skip comments. Fix: strip comment lines +
regenerate sepolicy.rule.sha256 (plain hex, no newline), rezip
(rezygisk-fixed.zip), install OK. `ksud module list` now shows rezygisk
enabled. PIF v18 + wififix also enabled.

GATED (needs user go-ahead): flash boot-clean-final.img (boot_a+b) or
fastboot-boot it first; then reboot -> ReZygisk activates (zygiskd) ->
PIF works -> Play Integrity / GPay path.

## EXECUTED (2026-09-19 ~02:45): clean flash done — ZYGISM LIVE

User go-ahead given ("Do it"). Sequence executed:
1. fastboot boot boot-clean-final.img (RAM test) -> BOOTED in 20s:
   magisk processes = 0, su uid=0, kernel 4.19.157-perf id intact,
   **zygisk-ptrace64 + zygiskd64/32 RUNNING, zygote64+zygote maps show 6
   zygisk entries each = injected** — module merged + tracer started at
   post-fs-data.
2. fastboot flash boot_a + boot_b boot-clean-final.img -> reboot -> 25s.
3. Permanent-boot verification: magisk 0, su OK, zygisk procs + 6/6 zygote
   injection, brightness_clone 536, con_mode 0.
4. Radio smoke on the clean flash: attack mode -> wlan0 monitor, ch 6 parked,
   rfhelper 100/100 frames, firmware completions on-air (fc_subtype=0xc0,
   addr3=a8:6e:84:c8:af:f8 Fabiola BSSID, chanfreq=2437); STA restored.
5. Sleep/wake on the clean flash: 536 -> 0 -> 337, panel live.
6. PIF v18: custom.pif.prop populated (Pixel 9 Pro Fold CANARY print,
   security patch 2026-08-05); GPay (com.google.android.apps.nbu.paisa.user)
   installed. Zygisk live => PIF spoofs DroidGuard at runtime.

Root stack is now KSU-ONLY (no Magisk anywhere). Rollback chain intact:
boot-injchan.img (previous proven, dual-root) + boot_backup_20260915.img
(stock) remain on D:/kernel-build.
