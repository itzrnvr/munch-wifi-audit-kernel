#!/system/bin/sh
# EAPOL capture: mon-on + pcapcap
# usage: eapol <channel> <outfile> <seconds>
CH=${1:-6}
OUT=${2:-/data/local/tmp/eapol.pcap}
T=${3:-60}
sh /data/local/tmp/mon-on $CH
sleep 2
/data/local/kali/kali-arm64/root/pcapcap wlan0 $OUT $T
echo "capture done: $OUT"
ls -la $OUT
