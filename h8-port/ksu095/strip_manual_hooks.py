#!/usr/bin/env python3
"""Remove the original-KSU manual hook call sites from fs/*.c.
KSU-Next v3.3 hooks via tracepoints; the manual sites reference symbols
that no longer exist. The sites are preserved as patches in
h8-port/ksu095/patch_manual_hooks.py for original-KSU builds."""
import sys

FILES = [
    "/root/sbx/fs/exec.c",
    "/root/sbx/fs/open.c",
    "/root/sbx/fs/read_write.c",
    "/root/sbx/fs/stat.c",
]

for path in FILES:
    lines = open(path, encoding="utf-8", errors="surrogateescape").readlines()
    out = []
    i = 0
    removed = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "#ifdef CONFIG_KSU":
            # scan to matching #endif
            j = i + 1
            depth = 1
            block = []
            while j < len(lines) and depth:
                s = lines[j].strip()
                if s.startswith("#ifdef") or s.startswith("#if "):
                    depth += 1
                elif s == "#endif":
                    depth -= 1
                if depth:
                    block.append(lines[j])
                j += 1
            blob = "".join(block)
            if "ksu_handle" in blob or "ksu_execveat_hook" in blob or "ksu_vfs_read_hook" in blob:
                removed += 1
                i = j
                continue
            out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
    open(path, "w", encoding="utf-8", errors="surrogateescape").writelines(out)
    print(f"{path}: removed {removed} ksu blocks")
print("STRIP_DONE")
