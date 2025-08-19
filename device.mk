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

# ------------------------------------------------------------------------------
# CRITICAL FIXES FOR DECRYPTION
# ------------------------------------------------------------------------------

# Use TWRP's system_vold for decryption instead of manual library linking
PRODUCT_PROPERTY_OVERRIDES += \
    ro.crypto.volume.metadata.method=dm-default-key

# Mediatek specific crypto modules (if available)
PRODUCT_PACKAGES += \
    libkeymaster4 \
    libkeymaster4_1 \
    libkeystore-engine-wifi-hidl \
    libpuresoftkeymasterdevice

# Recovery decryption libraries (optional - let system_vold handle it primarily)
TARGET_RECOVERY_DEVICE_MODULES += \
    libkeymaster4 \
    libkeymaster4_1 \
    libkeystore-engine-wifi-hidl \
    libpuresoftkeymasterdevice

TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4_1.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeystore-engine-wifi-hidl.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so

# Enable system vold for better decryption support
TW_CRYPTO_USE_SYSTEM_VOLD := true
TW_CRYPTO_SYSTEM_VOLD_DEBUG := true

# ------------------------------------------------------------------------------
# TWRP UI CONFIGURATION
# ------------------------------------------------------------------------------

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

# ------------------------------------------------------------------------------
# TWRP FEATURES
# ------------------------------------------------------------------------------

TW_INCLUDE_NTFS_3G := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
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

# FBE and encryption flags (sync with BoardConfig)
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_FBE := true
TW_USE_FSCRYPT_POLICY := v2
TW_PREPARE_DATA_MEDIA_EARLY := true
TW_INCLUDE_LOGICAL := true
TW_INCLUDE_F2FS := true

# ------------------------------------------------------------------------------
# SYSTEM PROP OVERRIDES
# ------------------------------------------------------------------------------

TW_OVERRIDE_SYSTEM_PROPS := \
    "ro.build.product;ro.build.fingerprint=ro.system.build.fingerprint;ro.build.version.incremental;ro.product.device=ro.product.system.device;ro.product.model=ro.product.system.model;ro.product.name=ro.product.system.name"

# ------------------------------------------------------------------------------
# STATUS BAR LAYOUT
# ------------------------------------------------------------------------------

TW_STATUS_ICONS_ALIGN := center
TW_CUSTOM_CPU_POS := "300"
TW_CUSTOM_CLOCK_POS := "70"
TW_CUSTOM_BATTERY_POS := "790"
TW_BATTERY_SYSFS_WAIT_SECONDS := 6

# ------------------------------------------------------------------------------
# MAINTAINER INFO
# ------------------------------------------------------------------------------

BOARD_MAINTAINER_NAME := ツ๛abrohim๛
TW_DEVICE_VERSION := $(BOARD_MAINTAINER_NAME)
OF_MAINTAINER := $(TW_DEVICE_VERSION)
PB_MAIN_VERSION := $(TW_DEVICE_VERSION)

# ------------------------------------------------------------------------------
# FSTAB AND FINAL CONFIGS
# ------------------------------------------------------------------------------

# Fstab path
TARGET_RECOVERY_FSTAB := $(LOCAL_PATH)/recovery.fstab

# Additional product packages for Mediatek support
PRODUCT_PACKAGES += \
    libion \
    libhardware \
    libhwbinder \
    libhidltransport \
    libutils \
    libcutils \
    libdl \
    libbase \
    libz \
    libc++ \
    libcrypto \
    libssl \
    libxml2

# Ensure these libraries are included in recovery
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libion.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhardware.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhwbinder.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhidltransport.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libutils.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libcutils.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libdl.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libbase.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libz.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libc++.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libcrypto.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libssl.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libxml2.so

# Add support for Mediatek specific modules
PRODUCT_PACKAGES += \
    libmtk_drvb \
    libmtk_symbols \
    libmtk_properties \
    libmtk_platform \
    libmtk_net \
    libmtk_netd \
    libmtk_netutils \
    libmtk_netd_client

# Include necessary binaries for recovery
PRODUCT_PACKAGES += \
    toybox \
    strace \
    lsof \
    sgdisk \
    grep \
    sed \
    awk \
    gzip \
    gunzip \
    cpio \
    tar \
    e2fsck \
    resize2fs \
    make_ext4fs \
    mkfs.f2fs \
    fsck.f2fs \
    fibmap.f2fs

# Set recovery properties
PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    persist.sys.usb.config=mtp,adb \
    ro.adb.secure=0 \
    ro.debuggable=1 \
    ro.secure=0 \
    ro.allow.mock.location=1 \
    ro.dalvik.vm.native.bridge=0 \
    persist.service.adb.enable=1 \
    persist.service.debuggable=1 \
    persist.sys.root_access=1
