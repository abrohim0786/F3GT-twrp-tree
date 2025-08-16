#
# Copyright (C) 2025 The TWRP Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

LOCAL_PATH := device/xiaomi/ares

# API
PRODUCT_SHIPPING_API_LEVEL := 31

# Dynamic
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# Virtual A/B
ENABLE_VIRTUAL_AB := true
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/compression.mk)

# Installs gsi keys into ramdisk, to boot a developer GSI with verified boot.
$(call inherit-product, $(SRC_TARGET_DIR)/product/gsi_keys.mk)

# Enable project quotas and casefolding for emulated storage without sdcardfs
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# A/B
PRODUCT_PACKAGES += \
    otapreopt_script

AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_system=true \
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \
    FILESYSTEM_TYPE_system=ext4 \
    POSTINSTALL_OPTIONAL_system=true

PRODUCT_PACKAGES_DEBUG += \
    bootctrl \
    update_engine_client

# Fastbootd
PRODUCT_PACKAGES += \
    fastbootd \
    android.hardware.fastboot@1.0-impl-mock

# Health
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-impl \
    android.hardware.health@2.1-service

# Update Engine
PRODUCT_PACKAGES += \
    update_engine \
    update_engine_sideload \
    update_verifier

# Boot control HAL
PRODUCT_PACKAGES += \
    android.hardware.boot@1.2-impl.recovery \
    android.hardware.boot@1.2-impl
    
# Additional target Libraries
TARGET_RECOVERY_DEVICE_MODULES += \
    libsoftkeymasterdevice \
    libkeymaster_messages \
    libkeystore_binder \
    libhardware \
    libcutils

TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libsoftkeymasterdevice.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster_messages.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeystore_binder.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhardware.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libcutils.so

# TWRP Configurations
TW_FRAMERATE := 120
TW_THEME := portrait_hdpi
TARGET_USES_LOGD := true
TWRP_INCLUDE_LOGCAT := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_LIBRESETPROP := true
TW_INCLUDE_NTFS_3G := true
TARGET_USES_MKE2FS := true
TW_INCLUDE_FUSE_EXFAT := true
TW_EXTRA_LANGUAGES := true
TW_NO_FASTBOOT_BOOT := true

# Excludes
TW_EXCLUDE_APEX := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_TZDATA := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_LPTOOLS := true
TW_EXCLUDE_LPDUMP := true
TW_EXCLUDE_SUPERSU := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_TZDATA := true

#Brightness
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_DEFAULT_BRIGHTNESS := 1400
TW_MAX_BRIGHTNESS := 2048

# USB
TW_EXCLUDE_DEFAULT_USB_INIT := true

# Storage
RECOVERY_SDCARD_ON_DATA := true

# Maintainer
BOARD_MAINTAINER_NAME := ツ๛abrohim๛
TW_DEVICE_VERSION := $(BOARD_MAINTAINER_NAME)
OF_MAINTAINER := $(BOARD_MAINTAINER_NAME)
PB_MAIN_VERSION := $(BOARD_MAINTAINER_NAME)
