F = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_tx_rx.c"
s = open(F, encoding="utf-8", errors="ignore").read()
old = """		skb->dev->flags |= IFF_UP;
		set_bit(__LINK_STATE_START, &skb->dev->state);
		rxstat = netif_receive_skb(skb);"""
new = """		skb->dev->flags |= IFF_UP;
		set_bit(__LINK_STATE_START, &skb->dev->state);
		/* use netif_rx (backlog path) - NAPI processes in clean context */
		rxstat = netif_rx(skb);"""
if old in s:
    s = s.replace(old, new, 1)
    open(F, "w", encoding="utf-8", errors="ignore").write(s)
    print("switched to netif_rx with LINK_STATE_START")
else:
    print("ERROR: anchor not found")
