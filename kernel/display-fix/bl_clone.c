/*
 * bl_clone.c — Kernel module that creates a writable "brightness_clone" sysfs
 * bin_attribute on the existing panel0-backlight device.
 *
 * Problem: On the sandboXimi AOSP kernel, the backlight device's kobject
 * sysfs_ops lack a store function (EACCES on all writes). The HyperOS
 * lights HAL needs a "brightness_clone" attribute to control the backlight.
 *
 * Fix: Use bin_attribute instead of device_attribute. bin_attribute files
 * have their own read/write callbacks that bypass the kobject's sysfs_ops,
 * so writes work even when the kobject's store is broken.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/device.h>
#include <linux/sysfs.h>
#include <linux/backlight.h>
#include <linux/fb.h>
#include <linux/delay.h>
#include <linux/platform_device.h>
#include <linux/string.h>

/* SDE connector + DSI panel headers — needed to access:
 *   c_conn->allow_bl_update  (SDE connector gate)
 *   display->panel->panel_initialized  (DSI panel gate)
 * The SDE connector's update_status returns early when allow_bl_update
 * is false, and dsi_display_set_backlight returns -EINVAL when the
 * panel is not initialized. We must force both before setting brightness. */
#include "sde_connector.h"
#include "dsi_display.h"
#include "dsi_panel.h"

static struct backlight_device *bl_dev;
static struct device *bl_raw_dev;

/* Match: child is the backlight device named "panel0-backlight" */
static int match_backlight(struct device *dev, void *data)
{
	return dev->class && dev->class->name &&
	       strcmp(dev->class->name, "backlight") == 0 &&
	       strcmp(dev_name(dev), "panel0-backlight") == 0;
}

/* Apply all panel-side gates so the DSI backlight path actually runs.
 *
 * The stock sandboXimi SDE/DSI stack has several gates that silently skip
 * the backlight DCS command, leaving the panel dark:
 *   - panel_initialized: dsi_display_set_backlight() bails with -EINVAL
 *   - bl_enable:         dsi_panel_set_backlight() returns early
 *   - hbm_51_ctrl_flag:  routes into the Xiaomi HBM branch which skips DCS
 *   - esd_config.status_mode: when the ESD status read fails (which it does
 *     whenever a DCS transfer races the panel's power state) the check sets
 *     esd_recovery_pending, and the recovery loop then re-powers the panel
 *     every ~9s forever, so the display never comes up.
 * Forcing the status mode to the "always succeed" simulation breaks that
 * loop, since dsi_display_check_status() returns before touching the panel.
 */
static void bl_clone_apply_panel_fixes(struct sde_connector *c_conn)
{
	struct dsi_display *dsi_disp;
	struct dsi_panel *panel;

	if (!c_conn || !c_conn->display)
		return;

	dsi_disp = (struct dsi_display *)c_conn->display;
	panel = dsi_disp->panel;
	if (!panel)
		return;

	panel->panel_initialized = true;
	panel->mi_cfg.bl_enable = true;
	panel->mi_cfg.hbm_51_ctrl_flag = false;
	panel->esd_config.status_mode = ESD_MODE_SW_SIM_SUCCESS;
}

/* bin_attribute read callback — shows current brightness */
static ssize_t brightness_clone_read(struct file *filp, struct kobject *kobj,
	struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	if (!bl_dev)
		return -ENODEV;
	if (off > 0 || count < 8)
		return 0;
	return scnprintf(buf, count, "%d\n", bl_dev->props.brightness);
}

/* bin_attribute write callback — sets brightness via backlight API
 *
 * CRITICAL: The SDE connector's update_status callback has TWO gates:
 *   1. props.power/state check — forces brightness=0 if blanked/suspended
 *   2. allow_bl_update check — returns early WITHOUT setting hardware if false
 * We must clear both gates before calling backlight_device_set_brightness().
 */
static ssize_t brightness_clone_write(struct file *filp, struct kobject *kobj,
	struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	unsigned long val;
	int ret;
	struct sde_connector *c_conn;

	if (!bl_dev || count == 0)
		return -ENODEV;

	ret = kstrtoul(buf, 0, &val);
	if (ret)
		return ret;

	if (val > bl_dev->props.max_brightness)
		return -EINVAL;

	/* bl_get_data() returns the c_conn pointer passed to
	 * backlight_device_register() in sde_connector.c */
	c_conn = (struct sde_connector *)bl_get_data(bl_dev);
	if (c_conn) {
		c_conn->allow_bl_update = true;
		bl_clone_apply_panel_fixes(c_conn);
	}

	/* Force unblank + clear FBBLANK/SUSPENDED so the SDE update_status
	 * callback does not override brightness to 0 */
	bl_dev->props.power = FB_BLANK_UNBLANK;
	bl_dev->props.state &= ~(BL_CORE_FBBLANK | BL_CORE_SUSPENDED);

	ret = backlight_device_set_brightness(bl_dev, val);
	if (ret)
		pr_warn("bl_clone: set brightness %lu failed rc=%d\n", val, ret);

	return count;
}

/* bin_attribute: mode 0666 so HAL (system) and root can both write */
static struct bin_attribute brightness_clone_attr = {
	.attr = {
		.name = "brightness_clone",
		.mode = 0666,
	},
	.read = brightness_clone_read,
	.write = brightness_clone_write,
};

/* reinit_panel — re-sends DCS sleep-out (0x11) + display-on (0x29) to the
 * panel. On this kernel the panel sometimes ends up in display-off/sleep
 * while everything else (backlight, commits, rendering) reports healthy,
 * leaving the screen black. Writing anything to this file pokes the two
 * standard DCS commands that bring the scan-out back up. */
static ssize_t reinit_panel_write(struct file *filp, struct kobject *kobj,
	struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	struct sde_connector *c_conn;
	struct dsi_display *dsi_disp;
	struct dsi_panel *panel;
	struct mipi_dsi_device *dsi;
	int ret;

	if (!bl_dev)
		return -ENODEV;

	c_conn = (struct sde_connector *)bl_get_data(bl_dev);
	if (!c_conn || !c_conn->display)
		return -ENODEV;

	dsi_disp = (struct dsi_display *)c_conn->display;
	panel = dsi_disp->panel;
	if (!panel)
		return -ENODEV;

	dsi = &panel->mipi_device;

	/* Keep the DSI path unlocked for the transfers below */
	c_conn->allow_bl_update = true;
	bl_clone_apply_panel_fixes(c_conn);

	pr_info("bl_clone: panel reinit: sleep_out + display_on\n");

	ret = mipi_dsi_dcs_exit_sleep_mode(dsi);
	if (ret < 0)
		pr_warn("bl_clone: sleep_out rc=%d\n", ret);

	msleep(150);

	ret = mipi_dsi_dcs_set_display_on(dsi);
	if (ret < 0)
		pr_warn("bl_clone: display_on rc=%d\n", ret);

	pr_info("bl_clone: panel reinit done\n");
	return count;
}

static struct bin_attribute reinit_panel_attr = {
	.attr = {
		.name = "reinit_panel",
		.mode = 0222,
	},
	.write = reinit_panel_write,
};

static int __init bl_clone_init(void)
{
	struct device *mdp_dev;
	int ret;

	/* Find the MDP platform device */
	mdp_dev = bus_find_device_by_name(&platform_bus_type, NULL,
					  "ae00000.qcom,mdss_mdp");
	if (!mdp_dev) {
		pr_err("bl_clone: MDP device not found\n");
		return -ENODEV;
	}

	/* Find the backlight child device */
	bl_raw_dev = device_find_child(mdp_dev, NULL, match_backlight);
	put_device(mdp_dev);

	if (!bl_raw_dev) {
		pr_err("bl_clone: backlight device not found\n");
		return -ENODEV;
	}

	bl_dev = to_backlight_device(bl_raw_dev);
	if (!bl_dev) {
		pr_err("bl_clone: to_backlight_device failed\n");
		put_device(bl_raw_dev);
		return -EINVAL;
	}

	/* Create the brightness_clone bin_attribute */
	ret = sysfs_create_bin_file(&bl_raw_dev->kobj, &brightness_clone_attr);
	if (ret) {
		pr_err("bl_clone: sysfs_create_bin_file failed: %d\n", ret);
		put_device(bl_raw_dev);
		return ret;
	}

	/* Create the reinit_panel bin_attribute */
	ret = sysfs_create_bin_file(&bl_raw_dev->kobj, &reinit_panel_attr);
	if (ret)
		pr_warn("bl_clone: reinit_panel attr failed: %d\n", ret);

	/* Force backlight to a visible level immediately, clearing every gate
	 * (allow_bl_update, panel_initialized, bl_enable, hbm_51_ctrl_flag,
	 * ESD status mode) plus the power/state flags. */
	{
		struct sde_connector *c_conn =
			(struct sde_connector *)bl_get_data(bl_dev);
		if (c_conn) {
			c_conn->allow_bl_update = true;
			bl_clone_apply_panel_fixes(c_conn);
		}
	}
	bl_dev->props.power = FB_BLANK_UNBLANK;
	bl_dev->props.state &= ~(BL_CORE_FBBLANK | BL_CORE_SUSPENDED);
	backlight_device_set_brightness(bl_dev, 1024);

	pr_info("bl_clone: brightness_clone created, backlight set to 1024, ESD loop broken\n");
	return 0;
}

static void __exit bl_clone_exit(void)
{
	if (bl_raw_dev) {
		sysfs_remove_bin_file(&bl_raw_dev->kobj,
				      &brightness_clone_attr);
		sysfs_remove_bin_file(&bl_raw_dev->kobj,
				      &reinit_panel_attr);
		put_device(bl_raw_dev);
		bl_raw_dev = NULL;
		bl_dev = NULL;
	}
	pr_info("bl_clone: unloaded\n");
}

module_init(bl_clone_init);
module_exit(bl_clone_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("h8");
MODULE_DESCRIPTION("Backlight brightness_clone bridge (bin_attr) for HyperOS HAL");
