#!/system/bin/sh
# Test: kill bridge daemon, wait, count DSI failures
echo "=== Before: failure count ==="
dmesg | grep -c "Command transfer failed"

# Find and kill the daemon (the sh running bl_bridge_simple.sh)
for pid in $(ps -A | grep "bl_bridge_simple" | grep -v grep | tr -s ' ' | cut -d' ' -f2); do
	echo "killing $pid"
	kill -9 $pid 2>/dev/null
done

sleep 20

echo "=== After 20s: failure count ==="
dmesg | grep -c "Command transfer failed"
echo "=== Last 5 backlight updates ==="
dmesg | grep "set backlight" | tail -5