import sys

# 1. Kconfig option
p = "/root/kernelsu-next/kernel/Kconfig"
src = open(p, newline="").read()
if "KSU_BISECT_STAGE" not in src:
    src = src.rstrip("\n") + """

config KSU_BISECT_STAGE
	int "Boot bisect stage: 0=full 1=skip syscall hooks 2=KSU disabled"
	default 0
	depends on KSU
	help
	  Debug ladder for bring-up on old kernels.
"""
    open(p, "w", newline="").write(src)
    print("PATCHED Kconfig")
else:
    print("ALREADY Kconfig")

# 2. init.c bisect gates
p = "/root/kernelsu-next/kernel/core/init.c"
src = open(p, newline="").read()
if "KSU_BISECT_STAGE" not in src:
    # top of init fn: full disable
    src = src.replace(
        "\tksu_init_symbol_resolver();\n\tksu_syscall_hook_init();",
        """#if defined(CONFIG_KSU_BISECT_STAGE) && (CONFIG_KSU_BISECT_STAGE == 2)
	pr_info("KSU bisect stage 2: KSU fully disabled at boot\\n");
	return 0;
#endif
	ksu_init_symbol_resolver();
#if defined(CONFIG_KSU_BISECT_STAGE) && (CONFIG_KSU_BISECT_STAGE >= 1)
	pr_info("KSU bisect stage 1: skipping syscall hook install\\n");
#else
	ksu_syscall_hook_init();
#endif""", 1)
    # the two manager_init call sites
    count = src.count("\t\tksu_syscall_hook_manager_init();") + src.count("\t\tksu_syscall_hook_manager_init();")
    src = src.replace(
        "	ksu_syscall_hook_manager_init();",
        """#if !(defined(CONFIG_KSU_BISECT_STAGE) && (CONFIG_KSU_BISECT_STAGE >= 1))
	ksu_syscall_hook_manager_init();
#endif""", 2)
    open(p, "w", newline="").write(src)
    print("PATCHED init.c")
else:
    print("ALREADY init.c")
