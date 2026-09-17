/* su_watchdog.c — auto-umount /system/bin unless cancelled.
 * Runs detached from root ctx; calls umount(2) directly so it works
 * even when /system/bin is broken. */
#include <unistd.h>
#include <sys/mount.h>
#include <stdio.h>

int main(void) {
	int i;
	/* wait up to 90s, checking every 5s for the cancel file */
	for (i = 0; i < 18; i++) {
		sleep(5);
		if (access("/data/local/tmp/su_ok", F_OK) == 0)
			return 0; /* cancelled — overlay is good */
	}
	umount2("/system/bin", MNT_DETACH);
	return 0;
}