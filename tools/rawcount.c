#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/select.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>
#include <errno.h>

int main(int argc, char **argv)
{
    const char *ifname = argc > 1 ? argv[1] : "wlan0";
    int dur = argc > 2 ? atoi(argv[2]) : 15;
    int count = 0;
    int s = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (s < 0) { perror("socket"); return 1; }
    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    if (ioctl(s, SIOCGIFINDEX, &ifr) < 0) { perror("SIOCGIFINDEX"); return 1; }
    struct sockaddr_ll addr;
    memset(&addr, 0, sizeof(addr));
    addr.sll_family = AF_PACKET;
    addr.sll_protocol = htons(ETH_P_ALL);
    addr.sll_ifindex = ifr.ifr_ifindex;
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("bind"); return 1; }
    fprintf(stderr, "listening on %s (ifindex %d) for %ds...\n", ifname, ifr.ifr_ifindex, dur);
    unsigned char buf[4096];
    int i;
    for (i = 0; i < dur; i++) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(s, &fds);
        struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
        int rv = select(s + 1, &fds, NULL, NULL, &tv);
        if (rv > 0) {
            while (1) {
                int n = recv(s, buf, sizeof(buf), MSG_DONTWAIT);
                if (n <= 0) break;
                count++;
            }
        }
    }
    printf("captured %d packets in %ds\n", count, dur);
    close(s);
    return 0;
}
