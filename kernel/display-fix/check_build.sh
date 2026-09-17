#!/bin/bash
echo "time: $(date +%H:%M:%S)"
echo "last line: $(tail -1 /tmp/build_miui.log)"
echo "errcount: $(grep -cE 'rror:|fatal' /tmp/build_miui.log)"
echo "done: $(grep -c BUILD_DONE /tmp/build_miui.log)"
grep -E "Error [0-9]" /tmp/build_miui.log | head -4
grep -B2 "Error 1$" /tmp/build_miui.log | grep -E "undefined|error" | sort -u | head -6