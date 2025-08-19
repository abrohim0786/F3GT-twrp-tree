#
# Copyright (C) 2025 The TWRP Open Source Project
#
# Licensed under the Apache License, Version 2.0
#

LOCAL_PATH := device/xiaomi/ares

# API level
PRODUCT_SHIPPING_API_LEVEL := 31

# Dynamic partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# Disable A/B until stable
ENABLE_VIRTUAL_AB := false
AB_OTA_UPDATER := false

# Boot control HAL
PRODUCT_PACKAGES += \
    android.hardware.boot@1.2-impl.recovery \
    android.hardware.boot@1.2-impl

# Fastbootd
PRODUCT_PACKAGES += \
    android.hardware.fastboot@1.0-impl-mock

# Health HAL
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-service \
    android.hardware.health@2.1-impl

# Recovery decryption libraries
TARGET_RECOVERY_DEVICE_MODULES += \
    libkeymaster4 \
    libpuresoftkeymasterdevice

TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so

# TWRP UI configuration
TW_FRAMERATE := 120
TW_THEME := portrait_hdpi
DEVICE_RESOLUTION := 1080x2400
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
TW_NO_SCREEN_BLANK := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TARGET_SCREEN_DENSITY := 440

# USB gadget path
TARGET_USE_CUSTOM_LUN_FILE_PATH := /config/usb_gadget/g1/functions/mass_storage.usb0/lun.%d/file

# TWRP features
TW_INCLUDE_NTFS_3G := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
TW_CRYPTO_SYSTEM_VOLD_DEBUG := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_REPACKTOOLS := true
TARGET_USES_MKE2FS := true
USE_RECOVERY_INSTALLER := true
RECOVERY_INSTALLER_PATH := $(DEVICE_PATH)/installer
TW_FORCE_KEYMASTER_VER := true
TW_EXCLUDE_APEX := true
TW_OEM_BUILD := true
TW_HAVE_SELINUX := true
TW_INCLUDE_SELINUX := true
TW_DEFAULT_EXTERNAL_STORAGE := true
TW_EXCLUDE_DEFAULT_USB_INIT := true

# System prop overrides
TW_OVERRIDE_SYSTEM_PROPS := \
    "ro.build.product;ro.build.fingerprint=ro.system.build.fingerprint;ro.build.version.incremental;ro.product.device=ro.product.system.device;ro.product.model=ro.product.system.model;ro.product.name=ro.product.system.name"

# Status bar layout
TW_STATUS_ICONS_ALIGN := center
TW_CUSTOM_CPU_POS := "300"
TW_CUSTOM_CLOCK_POS := "70"
TW_CUSTOM_BATTERY_POS := "790"
TW_BATTERY_SYSFS_WAIT_SECONDS := 6

# Maintainer info
BOARD_MAINTAINER_NAME := ツ๛abrohim๛
TW_DEVICE_VERSION := $(BOARD_MAINTAINER_NAME)
OF_MAINTAINER := $(TW_DEVICE_VERSION)
PB_MAIN_VERSION := $(TW_DEVICE_VERSION)

# Fstab path
TARGET_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab
