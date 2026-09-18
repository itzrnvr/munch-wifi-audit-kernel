import sys

BASE = "/root/sbx/"

def patch(path, old, new):
    p = BASE + path
    src = open(p, newline="", encoding="utf-8", errors="surrogateescape").read()
    if new.split("\n")[1].strip() in src or new.split("\n")[2].strip() in src:
        print(f"ALREADY: {path}")
        return
    if old not in src:
        print(f"MISS: {path}: {old[:60]!r}")
        sys.exit(1)
    src = src.replace(old, new, 1)
    open(p, "w", newline="", encoding="utf-8", errors="surrogateescape").write(src)
    print(f"PATCHED: {path}")

# ---- fs/exec.c ----
patch("fs/exec.c",
      "static int do_execveat_common(int fd, struct filename *filename,",
      """#ifdef CONFIG_KSU
extern bool ksu_execveat_hook __read_mostly;
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv,
			void *envp, int *flags);
extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,
				 void *argv, void *envp, int *flags);
#endif

static int do_execveat_common(int fd, struct filename *filename,""")

patch("fs/exec.c",
      "	return __do_execve_file(fd, filename, argv, envp, flags, NULL);",
      """#ifdef CONFIG_KSU
	if (unlikely(ksu_execveat_hook))
		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
	else
		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
#endif
	return __do_execve_file(fd, filename, argv, envp, flags, NULL);""")

# ---- fs/open.c ----
patch("fs/open.c",
      "long do_faccessat(int dfd, const char __user *filename, int mode)\n{",
      """#ifdef CONFIG_KSU
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,
			int *mode, int *flags);
#endif

long do_faccessat(int dfd, const char __user *filename, int mode)
{
#ifdef CONFIG_KSU
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif""")

# ---- fs/read_write.c ----
patch("fs/read_write.c",
      "ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)\n{",
      """#ifdef CONFIG_KSU
extern bool ksu_vfs_read_hook __read_mostly;
extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,
			size_t *count_ptr, loff_t **pos);
#endif

ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
{
#ifdef CONFIG_KSU
	if (unlikely(ksu_vfs_read_hook))
		ksu_handle_vfs_read(&file, &buf, &count, &pos);
#endif""")

# ---- fs/stat.c ----
patch("fs/stat.c",
      "SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,\n\t\tstruct stat __user *, statbuf, int, flag)\n{",
      """#ifdef CONFIG_KSU
extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
#endif

SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,
		struct stat __user *, statbuf, int, flag)
{
#ifdef CONFIG_KSU
	ksu_handle_stat(&dfd, &filename, &flag);
#endif""")

print("HOOKS_DONE")
