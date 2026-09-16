#!/usr/bin/env python3
"""GCC bring-up fixes for the sandboXimi munch tree (run inside /build/munch)."""
import os
import re

# 1. Makefile: insert -Wno flags + camera -iquote include dirs after the
#    KBUILD_CFLAGS -fno-PIE anchor line.
mk = open('Makefile', encoding='utf-8', errors='ignore').read()
if '-Wno-maybe-uninitialized' not in mk:
    m = re.search(r'^KBUILD_CFLAGS\s*\+= \$\(call cc-option,-fno-PIE\)$',
                  mk, flags=re.M)
    assert m, 'fno-PIE anchor not found'
    cam_dirs = ['cam_actuator', 'cam_cci', 'cam_csiphy', 'cam_eeprom',
                'cam_flash', 'cam_ois', 'cam_res_mgr', 'cam_sensor',
                'cam_sensor_io', 'cam_sensor_utils']
    base = 'techpack/camera-xiaomi/drivers/'
    iq = ' '.join('-iquote $(srctree)/' + base + d for d in cam_dirs)
    iq += ' -iquote $(srctree)/techpack/camera-xiaomi/drivers/cam_utils'
    ins = (m.group(0) + '\n'
           'KBUILD_CFLAGS += -Wno-maybe-uninitialized -Wno-format'
           ' -Wno-misleading-indentation -Wno-unused-but-set-variable\n'
           'KBUILD_CFLAGS += ' + iq + '\n')
    mk = mk[:m.start()] + ins + mk[m.end():]
    open('Makefile', 'w', encoding='utf-8', errors='ignore').write(mk)
    print('Makefile: flags + iquotes inserted')
else:
    print('Makefile: already patched')

# 1b. techpack Makefiles: subdir-scoped include flags + platform conf headers
#     (LINUXINCLUDE += in these files never reaches the compiler in this tree).
tp_add = {
    'techpack/audio/Makefile':
        'subdir-ccflags-y += -I$(srctree)/techpack/audio/include/uapi '
        '-I$(srctree)/techpack/audio/include/elliptic '
        '-I$(srctree)/techpack/audio/include '
        '-include $(srctree)/techpack/audio/config/konaautoconf.h\n',
    'techpack/camera-xiaomi/Makefile':
        'subdir-ccflags-y += -I$(srctree)/techpack/camera-xiaomi/include/uapi '
        '-I$(srctree)/techpack/camera-xiaomi/include '
        '-include $(srctree)/techpack/camera-xiaomi/config/konacameraconf.h\n',
}
for p, line in tp_add.items():
    s = open(p, encoding='utf-8', errors='ignore').read()
    if 'subdir-ccflags-y += -I$(srctree)/techpack' not in s:
        open(p, 'a', encoding='utf-8', errors='ignore').write('\n' + line)
        print(p + ': subdir-ccflags added')
    else:
        print(p + ': already patched')

# 2. Trace headers, per-file correct:
#    - TRACE_INCLUDE_FILE without '/' (bare name): PATH = dir relative to
#      include/trace/  (GCC needs the full relative path)
#    - TRACE_INCLUDE_FILE already a path: PATH must stay '.'
#    Undo the blind run-4 patch (which set PATH=relpath for all).
fixed = 0
for dp, dn, fn in os.walk('.'):
    if '.git' in dp:
        continue
    for f in fn:
        if not f.endswith('.h'):
            continue
        p = os.path.join(dp, f)
        try:
            s = open(p, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        mfile = re.search(r'^#define TRACE_INCLUDE_FILE (\S+)', s, flags=re.M)
        mpath = re.search(r'^#define TRACE_INCLUDE_PATH (\S+)', s, flags=re.M)
        if not mfile or not mpath:
            continue
        rel = os.path.relpath(dp, 'include/trace').replace('\\', '/')
        want = rel if '/' not in mfile.group(1) else '.'
        if mpath.group(1) != want:
            s = s[:mpath.start(1)] + want + s[mpath.end(1):]
            open(p, 'w', encoding='utf-8', errors='ignore').write(s)
            fixed += 1
print('trace headers corrected:', fixed)
# 3. xiaomi_touch.c: duplicate DEVICE_ATTR pair (bad merge) -> keep first only.
p = 'drivers/input/touchscreen/xiaomi/xiaomi_touch.c'
s = open(p, encoding='utf-8', errors='ignore').read()
pat = re.compile(r'static DEVICE_ATTR\(set_update,[^\n]*\n[^\n]*\n\n'
                 r'static DEVICE_ATTR\(bump_sample_rate,[^\n]*\n[^\n]*\n')
ms = list(pat.finditer(s))
if len(ms) > 1:
    s = s[:ms[1].start()] + s[ms[1].end():]
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('xiaomi_touch.c: duplicate DEVICE_ATTR pair removed')
else:
    print('xiaomi_touch.c: no duplicate found (%d)' % len(ms))

# 4. wm_adsp.c: init ret in wm_adsp_create_control (GCC maybe-uninitialized).
p = 'techpack/audio/asoc/codecs/cs35l41/wm_adsp.c'
lines = open(p, encoding='utf-8', errors='ignore').readlines()
# definition body per build log: decl at line 1839 (1-based), use at 1872
if lines[1838].strip() == 'int ret;':
    lines[1838] = lines[1838].replace('int ret;', 'int ret = 0;')
    open(p, 'w', encoding='utf-8', errors='ignore').writelines(lines)
    print('wm_adsp.c: ret initialized (line 1839)')
elif 'int ret = 0;' in lines[1838]:
    print('wm_adsp.c: already fixed')
else:
    print('wm_adsp.c: UNEXPECTED content at 1839:', repr(lines[1838]))

# 5. bq2597x charger: float math banned under -mgeneral-regs-only (GCC).
#    Convert sc8551_adc_lsb float table to Q16 fixed point (compile-time
#    folded constants; runtime math becomes integer).
p = 'drivers/power/supply/ti/bq2597x_charger_munch.c'
s = open(p, encoding='utf-8', errors='ignore').read()
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
old_use = ('\t\t\tkernel_neon_begin();\n'
           '\t\t\t*result = (int)(t * sc8551_adc_lsb[channel]);\n'
           '\t\t\tkernel_neon_end();')
new_use = ('\t\t\t*result = (int)(((s64)t *'
           ' sc8551_adc_lsb_q16[channel]) >> 16);')
if old_arr in s:
    s = s.replace(old_arr, new_arr, 1)
    if old_use in s:
        s = s.replace(old_use, new_use, 1)
    else:
        print('charger: use-site pattern NOT found')
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('bq2597x: Q16 conversion applied')
else:
    print('bq2597x: array pattern not found or already fixed')

# 6. Kbuilds re-enable -Wmaybe-uninitialized AFTER our -Wno -> neutralize.
for p in ['techpack/audio/ipc/Kbuild',
          'drivers/staging/qcacld-3.0/Kbuild']:
    s = open(p, encoding='utf-8', errors='ignore').read()
    if 'EXTRA_CFLAGS += -Wmaybe-uninitialized' in s or \
       'ccflags-y += -Wmaybe-uninitialized' in s:
        s = s.replace('EXTRA_CFLAGS += -Wmaybe-uninitialized',
                      'EXTRA_CFLAGS += -Wno-maybe-uninitialized')
        s = s.replace('ccflags-y += -Wmaybe-uninitialized',
                      'ccflags-y += -Wno-maybe-uninitialized')
        open(p, 'w', encoding='utf-8', errors='ignore').write(s)
        print(p + ': Wmaybe -> Wno-maybe')
    else:
        print(p + ': no positive Wmaybe (already fixed)')

# 7. qcacld: injection guards use FEATURE_* (no CONFIG_ prefix); add -D defines.
p = 'drivers/staging/qcacld-3.0/Kbuild'
s = open(p, encoding='utf-8', errors='ignore').read()
if '-DFEATURE_FRAME_INJECTION_SUPPORT' not in s:
    s += ('\nccflags-y += -DFEATURE_FRAME_INJECTION_SUPPORT'
          ' -DFEATURE_MONITOR_MODE_SUPPORT\n')
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('qcacld Kbuild: FEATURE_* defines added')
else:
    print('qcacld Kbuild: FEATURE_* defines present')

# 8. q6adm.c: port_idx used uninitialized in crus_adm_set_params log.
p = 'techpack/audio/dsp/q6adm.c'
lines = open(p, encoding='utf-8', errors='ignore').readlines()
if lines[883].strip() == 'int port_idx;':
    lines[883] = lines[883].replace('int port_idx;', 'int port_idx = 0;')
    open(p, 'w', encoding='utf-8', errors='ignore').writelines(lines)
    print('q6adm.c: port_idx initialized')
else:
    print('q6adm.c: line 884 =', repr(lines[883]))

# 9. q6afe.c: init result decl inside send_tfa_cal_apr.
p = 'techpack/audio/dsp/q6afe.c'
s = open(p, encoding='utf-8', errors='ignore').read()
i = s.find('int send_tfa_cal_apr(')
if i > 0:
    m = re.search(r'\b(int|int32_t|uint32_t)\s+result\s*;', s[i:])
    if m:
        j = i + m.start()
        s = s[:j] + m.group(0).replace('result;', 'result = 0;') + s[j + len(m.group(0)):]
        open(p, 'w', encoding='utf-8', errors='ignore').write(s)
        print('q6afe.c: result initialized in send_tfa_cal_apr')
    else:
        print('q6afe.c: no result decl found in send_tfa_cal_apr')
else:
    print('q6afe.c: send_tfa_cal_apr not found')

# 10. hdd_map_nl_chan_width call with extra patched arg -> single-arg form.
p = 'drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_cfg80211.c'
s = open(p, encoding='utf-8', errors='ignore').read()
s2, n = re.subn(r'hdd_map_nl_chan_width\(csa_params->chandef\.width,\s*\n\s*0\);',
                'hdd_map_nl_chan_width(csa_params->chandef.width);', s)
if n:
    open(p, 'w', encoding='utf-8', errors='ignore').write(s2)
    print('hdd_map_nl_chan_width: extra arg removed')
else:
    print('hdd_map_nl_chan_width: pattern not found (already fixed?)')

# 11. Global -DFEATURE defines (qcacld Kbuild tail append never applied).
mk = open('Makefile', encoding='utf-8', errors='ignore').read()
if '-DFEATURE_FRAME_INJECTION_SUPPORT' not in mk:
    anchor = 'KBUILD_CFLAGS += -Wno-maybe-uninitialized -Wno-format'
    i = mk.find(anchor)
    line_end = mk.find('\n', i)
    mk = mk[:line_end + 1] + \
        'KBUILD_CFLAGS += -DFEATURE_FRAME_INJECTION_SUPPORT -DFEATURE_MONITOR_MODE_SUPPORT\n' + \
        mk[line_end + 1:]
    open('Makefile', 'w', encoding='utf-8', errors='ignore').write(mk)
    print('Makefile: FEATURE defines added globally')
else:
    print('Makefile: FEATURE defines present')

# 12. q6afe.c comma-group decl: int32_t result, port_id = ...
p = 'techpack/audio/dsp/q6afe.c'
s = open(p, encoding='utf-8', errors='ignore').read()
if 'int32_t result, port_id = AFE_PORT_ID_TFADSP_RX;' in s:
    s = s.replace('int32_t result, port_id = AFE_PORT_ID_TFADSP_RX;',
                  'int32_t result = 0, port_id = AFE_PORT_ID_TFADSP_RX;', 1)
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('q6afe.c: result initialized (comma group)')
else:
    print('q6afe.c: comma-group decl not found')

# 13. elliptic_sysfs.c: init all bare int length decls.
for p in ['techpack/audio/dsp/elliptic/elliptic_sysfs.c',
          'techpack/audio/dsp/mius/mius_sysfs.c']:
    s = open(p, encoding='utf-8', errors='ignore').read()
    n = s.count('\tint length;')
    s = s.replace('\tint length;', '\tint length = 0;')
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('%s: %d length decls initialized' % (p, n))

# 14. camera subdir includes: add cam_sensor_module dirs to subdir-ccflags.
p = 'techpack/camera-xiaomi/Makefile'
s = open(p, encoding='utf-8', errors='ignore').read()
if 'cam_sensor_module/cam_cci' not in s.split('subdir-ccflags-y')[1][:2000] if 'subdir-ccflags-y' in s else True:
    dirs = ['cam_actuator', 'cam_cci', 'cam_csiphy', 'cam_eeprom', 'cam_flash',
            'cam_ois', 'cam_res_mgr', 'cam_sensor', 'cam_sensor_io',
            'cam_sensor_utils']
    flags = ' '.join('-I$(srctree)/techpack/camera-xiaomi/drivers/cam_sensor_module/' + d
                     for d in dirs)
    s += '\nsubdir-ccflags-y += ' + flags + '\n'
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('camera Makefile: sensor module -I dirs added')
else:
    print('camera Makefile: sensor dirs already present')

# 15. qcacld Kbuild: enable the injection feature flags as MAKE variables
#     (the in-kernel Kbuild never includes configs/default_defconfig) and
#     register the integration object that the patch's list omits.
p = 'drivers/staging/qcacld-3.0/Kbuild'
s = open(p, encoding='utf-8', errors='ignore').read()
if 'CONFIG_FEATURE_FRAME_INJECTION_SUPPORT := y' not in s:
    s = ('CONFIG_FEATURE_MONITOR_MODE_SUPPORT := y\n'
         'CONFIG_FEATURE_FRAME_INJECTION_SUPPORT := y\n\n') + s
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('qcacld Kbuild: feature vars set at top')
else:
    print('qcacld Kbuild: feature vars already set')
if 'wlan_hdd_frame_inject_integration.o' not in s:
    s = s.replace('HDD_OBJS += $(HDD_SRC_DIR)/wlan_hdd_frame_inject.o\n',
                  'HDD_OBJS += $(HDD_SRC_DIR)/wlan_hdd_frame_inject.o\n'
                  'HDD_OBJS += $(HDD_SRC_DIR)/wlan_hdd_frame_inject_integration.o\n', 1)
    open(p, 'w', encoding='utf-8', errors='ignore').write(s)
    print('qcacld Kbuild: integration object added')
else:
    print('qcacld Kbuild: integration object present')

t = open('drivers/clk/qcom/trace.h', encoding='utf-8', errors='ignore').read()
print('clk trace.h PATH =',
      re.search(r'#define TRACE_INCLUDE_PATH (\S+)', t).group(1))
print('ALL_FIXES_OK')
