/* drmprops.c — List DRM connector properties (static, no libdrm) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <errno.h>

int main(void)
{
	int fd, i, j;
	struct drm_mode_card_res res = {0};
	struct drm_mode_get_connector conn = {0};
	struct drm_mode_get_property prop = {0};

	fd = open("/dev/dri/card0", O_RDWR);
	if (fd < 0) { perror("open /dev/dri/card0"); return 1; }

	if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) {
		perror("GETRESOURCES"); close(fd); return 1;
	}

	res.connector_id_ptr = (uint64_t)calloc(res.count_connectors, sizeof(uint32_t));
	res.encoder_id_ptr = (uint64_t)calloc(res.count_encoders, sizeof(uint32_t));
	res.crtc_id_ptr = (uint64_t)calloc(res.count_crtcs, sizeof(uint32_t));
	res.fb_id_ptr = (uint64_t)calloc(res.count_fbs, sizeof(uint32_t));

	if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) {
		perror("GETRESOURCES 2"); close(fd); return 1;
	}

	uint32_t *cids = (uint32_t *)res.connector_id_ptr;
	for (i = 0; i < res.count_connectors; i++) {
		memset(&conn, 0, sizeof(conn));
		conn.connector_id = cids[i];
		ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn);

		conn.modes_ptr = (uint64_t)calloc(conn.count_modes, sizeof(struct drm_mode_modeinfo));
		conn.props_ptr = (uint64_t)calloc(conn.count_props, sizeof(uint32_t));
		conn.prop_values_ptr = (uint64_t)calloc(conn.count_props, sizeof(uint64_t));

		ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn);

		printf("Connector %d: type=%d id=%d status=%d\n",
			i, conn.connector_type, conn.connector_id, conn.connection);

		uint32_t *pids = (uint32_t *)conn.props_ptr;
		uint64_t *pvals = (uint64_t *)conn.prop_values_ptr;
		for (j = 0; j < conn.count_props; j++) {
			memset(&prop, 0, sizeof(prop));
			prop.prop_id = pids[j];
			ioctl(fd, DRM_IOCTL_MODE_GETPROPERTY, &prop);
			printf("  [%2d] %-30s = %llu\n", j, prop.name, pvals[j]);
		}

		free((void *)conn.modes_ptr);
		free((void *)conn.props_ptr);
		free((void *)conn.prop_values_ptr);
	}

	close(fd);
	return 0;
}
