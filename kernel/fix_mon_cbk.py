F = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_tx_rx.c"
s = open(F, encoding="utf-8", errors="ignore").read()

old = """		/*
		 * If this is not a last packet on the chain
		 * Just put packet into backlog queue, not scheduling RX sirq
		 */
		if (skb->next) {
			rxstat = netif_rx(skb);
		} else {
			/*
			 * This is the last packet on the chain
			 * Scheduling rx sirq
			 */
			rxstat = netif_rx_ni(skb);
		}

		if (NET_RX_SUCCESS == rxstat)
			++adapter->
				hdd_stats.tx_rx_stats.rx_delivered[cpu_index];
		else
			++adapter->hdd_stats.tx_rx_stats.rx_refused[cpu_index];

		skb = skb_next;"""

new = """		/* h8: deliver monitor frames inline to AF_PACKET.
		 * Clear chain ptrs, force IFF_UP (driver keeps clearing it),
		 * and use netif_receive_skb for synchronous delivery. */
		skb->next = NULL;
		skb->prev = NULL;
		skb->dev->flags |= IFF_UP;
		rxstat = netif_receive_skb(skb);

		if (NET_RX_SUCCESS == rxstat)
			++adapter->
				hdd_stats.tx_rx_stats.rx_delivered[cpu_index];
		else
			++adapter->hdd_stats.tx_rx_stats.rx_refused[cpu_index];

		skb = skb_next;"""

if old in s:
    s = s.replace(old, new, 1)
    open(F, "w", encoding="utf-8", errors="ignore").write(s)
    print("hdd_mon_rx_packet_cbk patched")
else:
    print("ERROR: anchor not found")
    # find nearby lines for debugging
    for i, line in enumerate(s.split('\n')):
        if 'netif_rx_ni' in line and i > 1570 and i < 1660:
            print(f"line {i+1}: {line}")
