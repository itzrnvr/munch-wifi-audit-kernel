# Add diagnostic prints to both callbacks to see which one fires
import re

# hdd_mon_rx_packet_cbk in wlan_hdd_tx_rx.c
F1 = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_tx_rx.c"
s1 = open(F1, encoding="utf-8", errors="ignore").read()
anchor1 = "cpu_index = wlan_hdd_get_cpu();"
if "H8A" not in s1:
    # Insert after the first occurrence in hdd_mon_rx_packet_cbk (around line 1591)
    idx = s1.find(anchor1, s1.find("hdd_mon_rx_packet_cbk"))
    if idx > 0:
        s1 = s1[:idx] + 'pr_err("H8A");\n\t' + s1[idx:]
        open(F1, "w", encoding="utf-8", errors="ignore").write(s1)
        print("H8A added to hdd_mon_rx_packet_cbk")

# hdd_rx_monitor_callback in wlan_hdd_rx_monitor.c
F2 = "/root/sbx/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_rx_monitor.c"
s2 = open(F2, encoding="utf-8", errors="ignore").read()
anchor2 = "cpu_index = wlan_hdd_get_cpu();"
if "H8B" not in s2:
    idx = s2.find(anchor2, s2.find("hdd_rx_monitor_callback"))
    if idx > 0:
        s2 = s2[:idx] + 'pr_err("H8B");\n\t' + s2[idx:]
        open(F2, "w", encoding="utf-8", errors="ignore").write(s2)
        print("H8B added to hdd_rx_monitor_callback")
