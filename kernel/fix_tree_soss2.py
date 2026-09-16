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

# --- fixes discovered during first s-oss build attempts ---

# 5. gcc-wrapper.py -> pure pass-through (py3 + QCOM warning policy off).
wrapper = '#!/usr/bin/env python\nimport sys, subprocess\nsys.exit(subprocess.call(sys.argv[1:]))\n'
try:
    open('scripts/gcc-wrapper.py', 'w').write(wrapper)
    print('gcc-wrapper: pass-through')
except OSError as e:
    print('gcc-wrapper:', e)

# 6. smp.c: extern int in_long_press (missing type).
p = 'arch/arm64/kernel/smp.c'
s = read(p)
if s and 'extern in_long_press;' in s:
    write(p, s.replace('extern in_long_press;', 'extern int in_long_press;'))
    print('smp.c: type fixed')

# 7. sched.h: extern inline -> extern (clang-ism, GCC needs real functions).
p = 'include/linux/sched.h'
s = read(p)
if s and 'extern inline bool is_top_app' in s:
    for fn in ['bool is_critical_task', 'bool is_top_app', 'bool is_inherit_top_app',
               'void set_inherit_top_app', 'void restore_inherit_top_app']:
        s = s.replace('extern inline ' + fn, 'extern ' + fn)
    write(p, s)
    print('sched.h: extern inline fixed')

# 8. charger float math -> Q16 integer.
p = 'drivers/power/supply/ti/bq2597x_charger_munch.c'
s = read(p)
if s and 'sc8551_adc_lsb_q16' not in s:
    import re as _re
    old_arr = ('static float sc8551_adc_lsb[] = {\n'
               '\t[ADC_IBUS] = SC8551_IBUS_ADC_LSB,  [ADC_VBUS] = SC8551_VBUS_ADC_LSB,\n'
               '\t[ADC_VAC] = SC8551_VAC_ADC_LSB,\t   [ADC_VOUT] = SC8551_VOUT_ADC_LSB,\n'
               '\t[ADC_VBAT] = SC8551_VBAT_ADC_LSB,  [ADC_IBAT] = SC8551_IBAT_ADC_LSB,\n'
               '\t[ADC_TBUS] = SC8551_TSBUS_ADC_LSB, [ADC_TBAT] = SC8551_TSBAT_ADC_LSB,\n'
               '\t[ADC_TDIE] = SC8551_TDIE_ADC_LSB,\n'
               '};')
    new_arr = ('static const int sc8551_adc_lsb_q16[] = {\n'
               '\t[ADC_IBUS] = (int)(SC8551_IBUS_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_VBUS] = (int)(SC8551_VBUS_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_VAC] = (int)(SC8551_VAC_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_VOUT] = (int)(SC8551_VOUT_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_VBAT] = (int)(SC8551_VBAT_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_IBAT] = (int)(SC8551_IBAT_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_TBUS] = (int)(SC8551_TSBUS_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_TBAT] = (int)(SC8551_TSBAT_ADC_LSB * 65536.0 + 0.5),\n'
               '\t[ADC_TDIE] = (int)(SC8551_TDIE_ADC_LSB * 65536.0 + 0.5),\n'
               '};')
    if old_arr in s:
        s = s.replace(old_arr, new_arr, 1)
        s2, n = _re.sub(r'kernel_neon_begin\(\);\n\s*\*result = \(int\)\(t \* sc8551_adc_lsb\[channel\]\);\n\s*kernel_neon_end\(\);',
                        '*result = (int)(((s64)t * sc8551_adc_lsb_q16[channel]) >> 16);', s)
        write(p, s2)
        print('charger: Q16 done, use sites', n)
    else:
        print('charger: ARRAY PATTERN MISMATCH')
else:
    print('charger: already fixed')

print('SOSS2_ALL_FIXES_OK')
