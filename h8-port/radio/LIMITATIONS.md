# Built-in radio (qcacld qca6390) capability matrix — measured 2026-09-18

Verified with rfhelper (github.com/itzrnvr/rfoverlord, native/rfhelper.c) and an
external monitor radio (WSL rig, tcpdump) as on-air witness.

| Capability | State | Evidence |
|---|---|---|
| STA scan (framework) | WORKS | cmd wifi list-scan-results, 100+ APs |
| Monitor con_mode (con_mode=4) | WORKS | wlan0 becomes radiotap netdev, UP/LOWER_UP |
| On-air packet injection | **WORKS (conditional)** | 66/100 spoofed deauths captured externally on-channel; WMA log `wma_send_injection_frame_to_fw ... tx_chanfreq=2437` |
| Monitor RX (AF_PACKET sniff) | UNVERIFIED | driver RX-delivery patches exist; not re-tested this session |
| Channel set (`iw set channel`) | FLAKY | EBUSY while background scans run; retry-loop needed |

## Proven attack-mode recipe (the 66/100 run)

1. STA wifi active first (associated or mid-scan) — the vdev needs channel
   context; a cold vdev has `mhz == 0` and WMA drops every injection frame
   with "Injection monitor vdev 0 has zero channel frequency".
2. `svc wifi disable; echo 4 > /sys/module/wlan/parameters/con_mode; svc wifi enable`
3. `ip link set wlan0 up`
4. `iw dev wlan0 set channel <ch>` — retry until not EBUSY (scans cause EBUSY)
5. Inject radiotap-framed 802.11 via AF_PACKET SOCK_RAW on wlan0
   (empty 8-byte radiotap header is enough; firmware logs tx_chanfreq).

Do NOT create a second monitor virtual iface (iw interface add) while in
attack mode: its presence makes channel changes on the primary vdev fail
(EBUSY) and poisons the injection path for the rest of the boot.

## Known driver gaps (next kernel dive)

- `wma_frame_inject.c:1443` drops injections when
  `wma_handle->interfaces[vdev_id].mhz == 0`. Patch idea: fall back to the
  cfg80211 current channel (or a global set by the set-channel path) instead
  of dropping; would make attack mode work from cold boot without STA history.
- `wma_dev_if.c:2904` (`intr[vdev_id].mhz = des_chan->ch_freq`) is the only
  mhz writer; it never runs for runtime-switched monitor vdevs.

## Measurement methodology warning (cost hours — do not repeat)

Negative on-air results are VOID unless the listening radio's channel is
proven during the exact burst window (check captured beacons' channel) AND
no other process moves that channel. The rig's own campaign engine
(aireplay/rotation on the same adapter) invalidated four separate
"impossible" conclusions before the 66/100 positive.

# bl_clone v2 (display wake fix)

HyperOS lights HAL writes `brightness_clone` on the panel0-backlight device;
the AOSP-derived kobject sysfs_ops have no store fn, so without the node the
panel wakes dark. bl_clone_v2.c = built-in delayed-work variant (first probe
at +20s, retries 90s) — no initcall-time DSI poke (v1's late_initcall poke
bricked boot: panel probe race). Load order irrelevant; survives all boots.

# Re-verification on boot-injchan.img (final kernel, 2026-09-19)

Full end-to-end pass on the restored proven kernel (original KSU v0.9.5 +
inject-channel patch + bl_clone v2):

| Check | Result |
|---|---|
| boot_completed / su | 1 / uid=0 context=su |
| brightness_clone node | present |
| STA scan | 105 APs via cmd wifi list-scan-results |
| attack mode | con_mode=4, wlan0 `type monitor`, parked ch 6 (2437 MHz) |
| deauth burst | **100/100 accepted, firmware `status=OK`**, dmesg confirms fc_subtype=0xc0 addr1=ff:ff:ff:ff:ff:ff addr2=phone MAC addr3=Fabiola BSSID tx_chanfreq=2437 |
| back to STA | con_mode=0, auto-reassoc My Haven (2457 MHz), wifi icon restored |
| sleep/wake | brightness 536 → 0 (asleep) → 336 (wake), panel unblank, screen renders |

Sequence notes from this run:
- Phone auto-associated to its saved network during `svc wifi enable` with
  con_mode=4 — that supplies the STA channel context the vdev needs
  (recipe step 1 holds even without explicit home-AP connect in the app).
- During init before `iw set channel`, the very first frame still hit the
  vdev-0 zero-channel drop and triggered the hidden-AP vdev 2 fallback;
  after the parked channel existed, every burst frame went out on the
  primary monitor vdev with the patched tx_chanfreq steering (radiotap
  channel honored — the kernel patch working as designed).
- One frame in the burst reported `DISCARDED(1)` in a completion — normal
  firmware rate-throttle under 100-frame flood, not a path failure.
