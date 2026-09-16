#!/usr/bin/env python3
"""Minimal GCC bring-up fixes for MiCode munch-s-oss + injection patch."""
import os
import re

def read(p):
    try:
        return open(p, encoding='utf-8', errors='ignore').read()
    except OSError:
        return None

def write(p, s):
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)

# 1. Top Makefile: warning flags (GCC vs clang-built tree).
mk = read('Makefile')
if mk and '-Wno-maybe-uninitialized' not in mk:
    m = re.search(r'^KBUILD_CFLAGS\s*\+= \$\(call cc-option,-fno-PIE\)$', mk, flags=re.M)
    if m:
        ins = (m.group(0) + '\n'
               'KBUILD_CFLAGS += -Wno-maybe-uninitialized -Wno-format'
               ' -Wno-misleading-indentation -Wno-unused-but-set-variable'
               ' -Wno-array-parameter\n')
        mk = mk[:m.start()] + ins + mk[m.end():]
        write('Makefile', mk)
        print('Makefile: Wno flags inserted')
else:
    print('Makefile: skipped')

# 2. Trace headers: bare TRACE_INCLUDE_PATH . -> dir-relative (GCC needs it).
fixed = 0
for dp, dn, fn in os.walk('.'):
    if '.git' in dp:
        continue
    for f in fn:
        if not f.endswith('.h'):
            continue
        p = os.path.join(dp, f)
        s = read(p)
        if s is None:
            continue
        mfile = re.search(r'^#define TRACE_INCLUDE_FILE (\S+)', s, flags=re.M)
        mpath = re.search(r'^#define TRACE_INCLUDE_PATH (\S+)', s, flags=re.M)
        if not mfile or not mpath:
            continue
        rel = os.path.relpath(dp, 'include/trace').replace('\\', '/')
        want = rel if '/' not in mfile.group(1) else '.'
        if mpath.group(1) != want:
            s = s[:mpath.start(1)] + want + s[mpath.end(1):]
            write(p, s)
            fixed += 1
print('trace headers fixed:', fixed)

# 3. bare #elif -> #else (clang-ism).
n = 0
for dp, dn, fn in os.walk('kernel'):
    for f in fn:
        if f.endswith('.c'):
            p = os.path.join(dp, f)
            s = read(p)
            if s and re.search(r'^#elif$', s, flags=re.M):
                s = re.sub(r'^#elif$', '#else', s, flags=re.M)
                write(p, s)
                n += 1
print('bare #elif fixed in', n, 'files')

# 4. qcacld Kbuild: feature make-vars + neutralized positive Wmaybe.
p = 'drivers/staging/qcacld-3.0/Kbuild'
s = read(p)
if s is not None:
    if 'CONFIG_FEATURE_FRAME_INJECTION_SUPPORT := y' not in s:
        s = ('CONFIG_FEATURE_MONITOR_MODE_SUPPORT := y\n'
             'CONFIG_FEATURE_FRAME_INJECTION_SUPPORT := y\n\n') + s
        write(p, s)
        print('qcacld Kbuild: feature vars set')
    s = read(p)
    s2 = s.replace('ccflags-y += -Wmaybe-uninitialized',
                   'ccflags-y += -Wno-maybe-uninitialized')
    s2 = s2.replace('EXTRA_CFLAGS += -Wmaybe-uninitialized',
                    'EXTRA_CFLAGS += -Wno-maybe-uninitialized')
    if s2 != s:
        write(p, s2)
        print('qcacld Kbuild: Wmaybe neutralized')
print('SOSS_FIXES_OK')
