/* qcacld setMonChan: SIOCIWFIRSTPRIV+4, ints = {23, chan, bw} */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/wireless.h>

int main(int argc, char **argv)
{
	char buf[16];
	int *v = (int *)buf;

	if (argc < 4) {
		fprintf(stderr, "usage: %s <ifname> <channel> <bandwidth 0|1|2>\n", argv[0]);
		return 1;
	}
	int skfd = socket(AF_INET, SOCK_DGRAM, 0);
	struct iwreq wrq;
	memset(&wrq, 0, sizeof(wrq));
	memset(buf, 0, sizeof(buf));
	v[0] = 23;              /* WE_SET_MON_MODE_CHAN */
	v[1] = atoi(argv[2]);   /* channel */
	v[2] = atoi(argv[3]);   /* bandwidth */
	v[3] = 0;
	strncpy(wrq.ifr_name, argv[1], IFNAMSIZ - 1);
	wrq.u.data.pointer = (caddr_t)buf;
	wrq.u.data.length = 4 * sizeof(__s32);
	wrq.u.data.flags = 0;
	int cmd = SIOCIWFIRSTPRIV + 4;
	if (ioctl(skfd, cmd, &wrq) < 0) {
		perror("setMonChan");
		return 1;
	}
	printf("setMonChan chan=%s bw=%s OK\n", argv[2], argv[3]);
	return 0;
}
