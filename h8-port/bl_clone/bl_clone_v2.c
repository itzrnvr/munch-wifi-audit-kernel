/*
 * bl_clone.c — creates a writable "brightness_clone" sysfs bin_attribute on
 * the panel0-backlight device so the HyperOS lights HAL can control the
 * backlight (the stock kobject sysfs_ops have no store function on this
 * kernel; bin_attributes carry their own callbacks and bypass that).
 *
 * Built-in variant: at boot the DSI panel device does not exist yet, so a
 * delayed work retries the lookup for up to ~90 seconds before giving up.
 * Without this node the HAL cannot re-apply brightness after screen blank
 * and the panel stays dark on wake.
 *
 * Also loadable as a module (insmod) — same code path via module_init.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/device.h>
#include <linux/sysfs.h>
#include <linux/backlight.h>
#include <linux/fb.h>
#include <linux/platform_device.h>
#include <linux/string.h>
#include <linux/workqueue.h>

#include "sde_connector.h"
#include "dsi_display.h"
#include "dsi_panel.h"

static struct backlight_device *bl_dev;
static struct device *bl_raw_dev;
static struct delayed_work bl_clone_work;
static int retries;

#define BL_RETRY_MS 300
#define BL_MAX_RETRIES 300 /* ~90 s */

static int match_backlight(struct device *dev, void *data)
{
	return dev->class && dev->class->name &&
	       strcmp(dev->class->name, "backlight") == 0 &&
	       strcmp(dev_name(dev), "panel0-backlight") == 0;
}

static ssize_t brightness_clone_read(struct file *filp, struct kobject *kobj,
	struct bin_attribute *attr, char *buf, loff_t off, size_t count)
{
	if (!bl_dev)
		return -ENODEV;
	if (off > 0 || count < 8)
		return 0;
	return scnprintf(buf, count, "%d\n", bl_dev->props.brightness);
}

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

	/* Gate 1+2: force SDE connector + panel-init gates so the DSI
	 * backlight update actually runs after a blank. */
	c_conn = (struct sde_connector *)bl_get_data(bl_dev);
	if (c_conn) {
		c_conn->allow_bl_update = true;
		if (c_conn->display) {
			struct dsi_display *dsi_disp =
				(struct dsi_display *)c_conn->display;
			if (dsi_disp->panel) {
				struct dsi_panel *panel = dsi_disp->panel;
				panel->panel_initialized = true;
				panel->mi_cfg.bl_enable = true;
				panel->mi_cfg.hbm_51_ctrl_flag = false;
			}
		}
	}

	/* Gate 3: force unblank + clear FBBLANK/SUSPENDED */
	bl_dev->props.power = FB_BLANK_UNBLANK;
	bl_dev->props.state &= ~(BL_CORE_FBBLANK | BL_CORE_SUSPENDED);

	ret = backlight_device_set_brightness(bl_dev, val);
	return count;
}

static struct bin_attribute brightness_clone_attr = {
	.attr = {
		.name = "brightness_clone",
		.mode = 0666,
	},
	.read = brightness_clone_read,
	.write = brightness_clone_write,
};

static bool bl_clone_created;

static int bl_clone_try_create(void)
{
	struct device *mdp_dev;
	int ret;

	if (bl_clone_created)
		return 0;

	mdp_dev = bus_find_device_by_name(&platform_bus_type, NULL,
					  "ae00000.qcom,mdss_mdp");
	if (!mdp_dev)
		return -ENODEV;

	bl_raw_dev = device_find_child(mdp_dev, NULL, match_backlight);
	put_device(mdp_dev);
	if (!bl_raw_dev)
		return -ENODEV;

	bl_dev = to_backlight_device(bl_raw_dev);
	if (!bl_dev) {
		put_device(bl_raw_dev);
		bl_raw_dev = NULL;
		return -EINVAL;
	}

	ret = sysfs_create_bin_file(&bl_raw_dev->kobj, &brightness_clone_attr);
	if (ret) {
		put_device(bl_raw_dev);
		bl_raw_dev = NULL;
		bl_dev = NULL;
		return ret;
	}

	/* Force backlight visible immediately (boot path: panel may come up
	 * dark until the HAL's first write). */
	{
		struct sde_connector *c_conn =
			(struct sde_connector *)bl_get_data(bl_dev);
		if (c_conn) {
			c_conn->allow_bl_update = true;
			if (c_conn->display) {
				struct dsi_display *dsi_disp =
					(struct dsi_display *)c_conn->display;
				if (dsi_disp->panel) {
					dsi_disp->panel->panel_initialized = true;
					dsi_disp->panel->mi_cfg.bl_enable = true;
					dsi_disp->panel->mi_cfg.hbm_51_ctrl_flag = false;
				}
			}
		}
	}
	bl_dev->props.power = FB_BLANK_UNBLANK;
	bl_dev->props.state &= ~(BL_CORE_FBBLANK | BL_CORE_SUSPENDED);
	backlight_device_set_brightness(bl_dev, 1024);

	bl_clone_created = true;
	pr_info("bl_clone: brightness_clone ready (retries=%d)\n", retries);
	return 0;
}

static void bl_clone_poll(struct work_struct *work)
{
	int ret = bl_clone_try_create();

	if (ret == 0)
		return;
	if (++retries >= BL_MAX_RETRIES) {
		pr_err("bl_clone: gave up after %d tries (%d)\n", retries, ret);
		return;
	}
	schedule_delayed_work(&bl_clone_work, msecs_to_jiffies(BL_RETRY_MS));
}

static int __init bl_clone_init(void)
{
	INIT_DELAYED_WORK(&bl_clone_work, bl_clone_poll);
	/* first shot may succeed when insmod'd after boot */
	if (bl_clone_try_create() == 0)
		return 0;
	schedule_delayed_work(&bl_clone_work, msecs_to_jiffies(BL_RETRY_MS));
	return 0;
}

static void __exit bl_clone_exit(void)
{
	cancel_delayed_work_sync(&bl_clone_work);
	if (bl_raw_dev) {
		sysfs_remove_bin_file(&bl_raw_dev->kobj,
				      &brightness_clone_attr);
		put_device(bl_raw_dev);
		bl_raw_dev = NULL;
		bl_dev = NULL;
		bl_clone_created = false;
	}
	pr_info("bl_clone: removed\n");
}

late_initcall(bl_clone_init);
module_exit(bl_clone_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("h8");
MODULE_DESCRIPTION("Backlight brightness_clone bridge (built-in) for HyperOS HAL");