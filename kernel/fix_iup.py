F = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_rx_monitor.c"
s = open(F, encoding="utf-8", errors="ignore").read()
old = """		skb->next = NULL;
		skb->prev = NULL;
		rxstat = netif_receive_skb(skb);"""
new = """		skb->next = NULL;
		skb->prev = NULL;
		/* h8: driver keeps clearing IFF_UP on monitor vdev; force it
		 * so the stack accepts the frame for AF_PACKET delivery */
		skb->dev->flags |= IFF_UP;
		rxstat = netif_receive_skb(skb);"""
if old in s:
    s = s.replace(old, new, 1)
    open(F, "w", encoding="utf-8", errors="ignore").write(s)
    print("IFF_UP force applied")
else:
    print("anchor not found")
    # show current state
    for i, line in enumerate(s.split('\n')):
        if 'netif_receive' in line or 'skb->next' in line:
            print(f"{i+1}: {line}")
