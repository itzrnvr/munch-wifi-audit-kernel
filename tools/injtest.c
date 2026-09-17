/* injtest.c — minimal deauth frame injection test */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <net/ethernet.h>
#include <arpa/inet.h>

int main(int argc, char **argv) {
	const char *ifname = argc > 1 ? argv[1] : "wlan0";
	int sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
	if (sock < 0) { perror("socket"); return 1; }

	struct sockaddr_ll sa = {0};
	sa.sll_family = AF_PACKET;
	sa.sll_protocol = htons(ETH_P_ALL);
	sa.sll_ifindex = if_nametoindex(ifname);
	if (!sa.sll_ifindex) { perror("ifindex"); return 1; }

	/* 802.11 deauth frame: type=0xc0, broadcast */
	unsigned char deauth[] = {
		0xc0, 0x00,             /* frame control: deauth */
		0x3a, 0x01,             /* duration */
		0xff,0xff,0xff,0xff,0xff,0xff, /* addr1 (bcast) */
		0x00,0x11,0x22,0x33,0x44,0x55, /* addr2 (us) */
		0x00,0x11,0x22,0x33,0x44,0x55, /* addr3 */
		0x00, 0x00,             /* seq */
		0x07, 0x00              /* reason: class 3 frame */
	};

	int ok = 0, fail = 0;
	for (int i = 0; i < 50; i++) {
		ssize_t n = sendto(sock, deauth, sizeof(deauth), 0,
			(struct sockaddr *)&sa, sizeof(sa));
		if (n > 0) ok++; else fail++;
		usleep(20000);
	}
	printf("injection: %d ok, %d failed\n", ok, fail);
	close(sock);
	return fail ? 1 : 0;
}