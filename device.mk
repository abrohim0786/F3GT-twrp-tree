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

# Disable A/B until stable
ENABLE_VIRTUAL_AB := false
AB_OTA_UPDATER := false

# Remove conflicting OTA packages
#PRODUCT_PACKAGES += \
#    otapreopt_script \
#    update_engine \
#    update_engine_sideload \
#    update_verifier

# Boot control HAL (essential for recovery)
PRODUCT_PACKAGES += \
    android.hardware.boot@1.2-impl.recovery \
    android.hardware.boot@1.2-impl \
    bootctrl.$(TARGET_BOARD_PLATFORM).recovery

# Fastbootd
PRODUCT_PACKAGES += \
    fastbootd \
    android.hardware.fastboot@1.0-impl-mock

# Health HAL
PRODUCT_PACKAGES += \
    android.hardware.health@2.1-service \
    android.hardware.health@2.1-impl.recovery
    
# Critical libraries for recovery
PRODUCT_PACKAGES += \
    libion \
    libxml2 \
    libbase \
    libz

# Keymaster libraries (required even without crypto)
PRODUCT_PACKAGES += \
    libkeymaster4 \
    libpuresoftkeymasterdevice \
    libkeymaster4support

# TWRP specific build flags
TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_USE_TOOLBOX := true
TW_EXCLUDE_TWRPAPP := true
TW_THEME := portrait_hdpi
BOARD_CHARGER_DISABLE_INIT_BLANK := true
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TARGET_USE_CUSTOM_LUN_FILE_PATH := /config/usb_gadget/g1/functions/mass_storage.usb0/lun.%d/file
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_REPACKTOOLS := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_EXTRA_LANGUAGES := true
TW_INCLUDE_NTFS_3G := true
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
TW_NO_HAPTICS := true
TW_EXCLUDE_APEX := false  # Must be false for Android 12+
USE_RECOVERY_INSTALLER := true
RECOVERY_INSTALLER_PATH := $(DEVICE_PATH)/installer

# StatusBar Customization
TW_STATUS_ICONS_ALIGN := center
DEVICE_RESOLUTION := 1080x2400
TW_CUSTOM_CPU_POS := "300"
TW_CUSTOM_CLOCK_POS := "70"
TW_CUSTOM_BATTERY_POS := "790"
TW_BATTERY_SYSFS_WAIT_SECONDS := 6
TARGET_USES_MKE2FS := true

# Crypto (DISABLED to fix boot loop)
TW_INCLUDE_CRYPTO := false
TW_INCLUDE_CRYPTO_FBE := false
TW_INCLUDE_FBE_METADATA_DECRYPT := false

# Maintainer and Branding
TW_DEVICE_VERSION := by AbRoHim
TW_OF_MAINTAINER := "AbRoHim"

# SELinux policies
BOARD_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy

# Override recovery modules
PRODUCT_HOST_PACKAGES += \
    pigz
