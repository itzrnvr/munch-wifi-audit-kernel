obj-m := bl_clone.o

KDIR ?= /root/sbx

# Include paths for SDE connector + DSI panel headers
ccflags-y += -I$(KDIR)/techpack/display/msm/dsi
ccflags-y += -I$(KDIR)/techpack/display/msm/sde
ccflags-y += -I$(KDIR)/techpack/display/msm
ccflags-y += -I$(KDIR)/techpack/display
ccflags-y += -I$(KDIR)/include/uapi
ccflags-y += -I$(KDIR)/include/drm

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- clean
