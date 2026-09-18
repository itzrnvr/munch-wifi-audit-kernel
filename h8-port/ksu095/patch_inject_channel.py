#!/usr/bin/env python3
"""One-time qcacld patch: honor a radiotap channel field for monitor injection.

Fixes "Injection monitor vdev N has zero channel frequency; dropping frame"
(wma_frame_inject.c) for runtime-switched monitor vdevs whose WMA mhz field
is never populated. After this patch the USERSPACE injector controls the
transmit channel by embedding a radiotap channel field — no further kernel
changes needed for channel control.

1. struct inject_frame_req gains tx_chanfreq.
2. hdd_monitor_mode_tx_inject parses radiotap channel (present bit 3) into it.
3. wma_frame_inject falls back to req->tx_chanfreq when vdev mhz == 0.
"""
import sys

BASE = "/root/sbx/drivers/staging/qcacld-3.0/"

def patch(path, old, new):
    p = BASE + path
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if new.split("\n")[0].strip() in s and old.split("\n")[0].strip() not in s:
        print(f"ALREADY: {path}")
        return
    if old not in s:
        print(f"MISS: {path}: {old[:60]!r}")
        sys.exit(1)
    s = s.replace(old, new, 1)
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print(f"PATCHED: {path}")

# 1. struct field
patch("core/hdd/inc/wlan_hdd_frame_inject.h",
      """	uint32_t tx_rate;
	uint64_t timestamp;""",
      """	uint32_t tx_rate;
	uint32_t tx_chanfreq;	/* h8: radiotap channel for monitor injection */
	uint64_t timestamp;""")

# 2. HDD: parse radiotap channel into req
patch("core/hdd/src/wlan_hdd_tx_rx.c",
      """	if (has_radiotap) {
		frame_data = skb->data + rtap_len;
		frame_len = skb->len - rtap_len;""",
      """	if (has_radiotap) {
		/* h8: extract channel field (present bit 3) so userspace can
		 * steer the injection channel without kernel state.
		 * Walk present bits 0..2 to locate bit 3's payload. */
		uint32_t present = skb->data[4] | (skb->data[5] << 8) |
				   (skb->data[6] << 16) | (skb->data[7] << 24);
		static const uint8_t sz[4] = {8, 1, 1, 4};
		uint32_t off = 8;
		int b;

		for (b = 0; b < 3; b++)
			if (present & (1u << b))
				off += sz[b];
		if ((present & (1u << 3)) && off + 4 <= rtap_len)
			req_chan = skb->data[off + 2] | (skb->data[off + 3] << 8);
		frame_data = skb->data + rtap_len;
		frame_len = skb->len - rtap_len;""")

# declare req_chan + store into req (req is allocated after; store after alloc)
patch("core/hdd/src/wlan_hdd_tx_rx.c",
      """	struct ieee80211_radiotap_header *rthdr;
	struct inject_frame_req *req;""",
      """	struct ieee80211_radiotap_header *rthdr;
	struct inject_frame_req *req;
	uint16_t req_chan = 0;""")

patch("core/hdd/src/wlan_hdd_tx_rx.c",
      """	req->frame_len = frame_len;
	req->tx_flags = 0;""",
      """	req->frame_len = frame_len;
	req->tx_flags = 0;
	req->tx_chanfreq = req_chan;""")

# 3. WMA fallback
patch("core/wma/src/wma_frame_inject.c",
      """		tx_chanfreq = wma_handle->interfaces[vdev_id].mhz;""",
      """		tx_chanfreq = wma_handle->interfaces[vdev_id].mhz;
		/* h8: userspace-supplied radiotap channel fallback */
		if (!tx_chanfreq && req->tx_chanfreq)
			tx_chanfreq = req->tx_chanfreq;""")

print("INJECT_CHANNEL_PATCH_DONE")
