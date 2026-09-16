/* Minimal pcap recorder for monitor mode capture (AF_PACKET + recv, no MMAP) */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <linux/if_packet.h>
#include <linux/if_ether.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>
#include <time.h>

/* pcap global header */
struct pcap_hdr {
    unsigned int magic;
    short version_major;
    short version_minor;
    int thiszone;
    unsigned int sigfigs;
    unsigned int snaplen;
    unsigned int linktype;
};

/* pcap per-packet header */
struct pcap_pkt {
    unsigned int ts_sec;
    unsigned int ts_usec;
    unsigned int incl_len;
    unsigned int orig_len;
};

int main(int argc, char **argv)
{
    const char *ifname = argc > 1 ? argv[1] : "wlan0";
    const char *outfile = argc > 2 ? argv[2] : "/data/local/tmp/cap.pcap";
    int dur = argc > 3 ? atoi(argv[3]) : 60;
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

    FILE *f = fopen(outfile, "wb");
    if (!f) { perror("fopen"); return 1; }

    /* DLT_IEEE802_11_RADIOTAP = 127 */
    struct pcap_hdr hdr = {
        .magic = 0xa1b2c3d4,
        .version_major = 2,
        .version_minor = 4,
        .thiszone = 0,
        .sigfigs = 0,
        .snaplen = 65535,
        .linktype = 127
    };
    fwrite(&hdr, sizeof(hdr), 1, f);

    fprintf(stderr, "capturing on %s -> %s for %ds\n", ifname, outfile, dur);
    unsigned char buf[65536];

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
                struct pcap_pkt pkt;
                struct timespec ts;
                clock_gettime(CLOCK_MONOTONIC, &ts);
                pkt.ts_sec = (unsigned int)ts.tv_sec;
                pkt.ts_usec = (unsigned int)(ts.tv_nsec / 1000);
                pkt.incl_len = n;
                pkt.orig_len = n;
                fwrite(&pkt, sizeof(pkt), 1, f);
                fwrite(buf, n, 1, f);
                count++;
            }
        }
    }
    fclose(f);
    close(s);
    printf("captured %d packets in %ds -> %s\n", count, dur, outfile);
    return 0;
}
