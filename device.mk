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
    # Additional binaries & libraries needed for recovery decryption

# Keymaster + Keystore2 + Gatekeeper + KeyMint
TARGET_RECOVERY_DEVICE_MODULES += \
    libkeymaster4 \
    libpuresoftkeymasterdevice \
    libsoftkeymasterdevice \
    libkeymint \
    libkeystore2_crypto \
    libkeystore2 \
    libbinder_ndk \
    libhidlbase \
    libhidltransport \
    libutils \
    libbase \
    libcrypto \
    libssl

# Services (executables) that must be copied into recovery
TARGET_RECOVERY_DEVICE_MODULES += \
    keystore2 \
    hwservicemanager \
    servicemanager \
    vold

# Vendor HAL service binaries (adjust path if vendor tree provides different names)
TARGET_RECOVERY_DEVICE_MODULES += \
    android.hardware.security.keymint-service \
    android.hardware.gatekeeper@1.0-service

# Relink libraries into recovery ramdisk
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libsoftkeymasterdevice.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymint.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeystore2_crypto.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeystore2.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libbinder_ndk.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhidlbase.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhidltransport.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libutils.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libbase.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libcrypto.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libssl.so

# Relink binaries too (if make complains, add explicitly)
TW_RECOVERY_ADDITIONAL_RELINK_BINARY_FILES += \
    $(TARGET_OUT_EXECUTABLES)/keystore2 \
    $(TARGET_OUT_EXECUTABLES)/hwservicemanager \
    $(TARGET_OUT_EXECUTABLES)/servicemanager \
    $(TARGET_OUT_EXECUTABLES)/vold \
    $(TARGET_OUT_EXECUTABLES)/android.hardware.security.keymint-service \
    $(TARGET_OUT_EXECUTABLES)/android.hardware.gatekeeper@1.0-service
    
# TWRP UI Configuration
TW_FRAMERATE := 120
TW_THEME := portrait_hdpi
DEVICE_RESOLUTION := 1080x2400
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
#TW_SCREEN_BLANK_ON_BOOT := true
TW_NO_SCREEN_BLANK := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TARGET_USE_CUSTOM_LUN_FILE_PATH := /config/usb_gadget/g1/functions/mass_storage.usb0/lun.%d/file
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

# APEX
TW_EXCLUDE_APEX := true

# Display
TARGET_SCREEN_DENSITY := 440

# building of an OEM friendly TWRP. excludes SuperSu, uses Toolbox instead busybox, disables themeing. MORE INFOS TO BE ADDED
TW_OEM_BUILD := true

# Configure SELinux options.
TW_HAVE_SELINUX := true

TW_OVERRIDE_SYSTEM_PROPS := \
    "ro.build.product;ro.build.fingerprint=ro.system.build.fingerprint;ro.build.version.incremental;ro.product.device=ro.product.system.device;ro.product.model=ro.product.system.model;ro.product.name=ro.product.system.name"

# StatusBar
TW_STATUS_ICONS_ALIGN := center
TW_CUSTOM_CPU_POS := "300"
TW_CUSTOM_CLOCK_POS := "70"
TW_CUSTOM_BATTERY_POS := "790"
TW_BATTERY_SYSFS_WAIT_SECONDS := 6

# SELinux Policies
TW_INCLUDE_SELINUX := true
TW_DEFAULT_EXTERNAL_STORAGE := true

# USB
TW_EXCLUDE_DEFAULT_USB_INIT := true

# Maintainer
BOARD_MAINTAINER_NAME := ツ๛abrohim๛
TW_DEVICE_VERSION := $(BOARD_MAINTAINER_NAME)
OF_MAINTAINER := $(BOARD_MAINTAINER_NAME)
PB_MAIN_VERSION := $(BOARD_MAINTAINER_NAME)

# Only use our custom recovery.fstab
TW_USE_LEGACY_FSTAB := true
TW_IGNORE_DEFAULT_FSTAB := true
TW_INCLUDE_F2FS := true
