F = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_tx_rx.c"
s = open(F, encoding="utf-8", errors="ignore").read()
old = """		skb->dev->flags |= IFF_UP;
		rxstat = netif_receive_skb(skb);"""
new = """		skb->dev->flags |= IFF_UP;
		set_bit(__LINK_STATE_START, &skb->dev->state);
		rxstat = netif_receive_skb(skb);"""
if old in s:
    s = s.replace(old, new, 1)
    open(F, "w", encoding="utf-8", errors="ignore").write(s)
    print("LINK_STATE_START added to hdd_mon_rx_packet_cbk")
else:
    print("ERROR: anchor not found in tx_rx.c")

# Also add to the rx_monitor callback (just in case)
F2 = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_rx_monitor.c"
s2 = open(F2, encoding="utf-8", errors="ignore").read()
old2 = """		skb->dev->flags |= IFF_UP;
		rxstat = netif_receive_skb(skb);"""
new2 = """		skb->dev->flags |= IFF_UP;
		set_bit(__LINK_STATE_START, &skb->dev->state);
		rxstat = netif_receive_skb(skb);"""
if old2 in s2:
    s2 = s2.replace(old2, new2, 1)
    open(F2, "w", encoding="utf-8", errors="ignore").write(s2)
    print("LINK_STATE_START added to rx_monitor callback")
else:
    print("rx_monitor anchor not found (ok if already different)")
