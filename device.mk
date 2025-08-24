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

# Enable A/B support
ENABLE_VIRTUAL_AB := true
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS := boot system vendor product system_ext vbmeta_system vbmeta_vendor

# Remove conflicting OTA packages
#PRODUCT_PACKAGES += \
#    otapreopt_script \
#    update_engine \
#    update_engine_sideload \
#    update_verifier

# Boot control HAL
PRODUCT_PACKAGES += \
    android.hardware.boot@1.2-impl.recovery \
    android.hardware.boot@1.2-impl

# fastbootd
PRODUCT_PACKAGES += \
    android.hardware.fastboot@1.0-impl-mock

# Heath hal
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-service \
    android.hardware.health@2.1-impl
    
# Crypto and keymaster for FBE decryption
TARGET_RECOVERY_DEVICE_MODULES += \
    libkeymaster4 \
    libpuresoftkeymasterdevice \
    libkeymaster4_1 \
    libkeystore-engine-wifi-hidl

TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4_1.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeystore-engine-wifi-hidl.so

# Use system vold for decryption
TW_CRYPTO_USE_SYSTEM_VOLD := true
TW_CRYPTO_SYSTEM_VOLD_DEBUG := true

# TWRP UI Configuration
TW_THEME := portrait_hdpi
DEVICE_RESOLUTION := 1080x1920
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
TW_SCREEN_BLANK_ON_BOOT := true
TW_NO_SCREEN_BLANK := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TARGET_USE_CUSTOM_LUN_FILE_PATH := /config/usb_gadget/g1/functions/mass_storage.usb0/lun.%d/file
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_DEFAULT_EXTERNAL_STORAGE := true
TW_INCLUDE_NTFS_3G := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_REPACKTOOLS := true
TW_EXCLUDE_APEX := true
TARGET_USES_MKE2FS := true
USE_RECOVERY_INSTALLER := true
RECOVERY_INSTALLER_PATH := $(DEVICE_PATH)/installer

# Logical partitions support in recovery UI
TW_INCLUDE_LOGICAL := true

# Filesystem tools
TW_INCLUDE_F2FS := true
TARGET_USERIMAGES_USE_F2FS := true

# FastbootD
TW_INCLUDE_FASTBOOTD := true

# StatusBar
TW_STATUS_ICONS_ALIGN := center
TW_CUSTOM_CPU_POS := "300"
TW_CUSTOM_CLOCK_POS := "70"
TW_CUSTOM_BATTERY_POS := "790"
TW_BATTERY_SYSFS_WAIT_SECONDS := 6

# SELinux Policies
BOARD_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy
    
# Maintainer Info
TW_DEVICE_VERSION := by- aBr0him
