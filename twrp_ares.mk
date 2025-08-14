#
# Copyright (C) 2025 The Android Open Source Project
# Copyright (C) 2025 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

# Installs gsi keys into ramdisk, to boot a developer GSI with verified boot.
$(call inherit-product, $(SRC_TARGET_DIR)/product/gsi_keys.mk)

# Inherit from our custom product configuration
$(call inherit-product, vendor/twrp/config/common.mk)

# Inherit from ares device
$(call inherit-product, device/xiaomi/ares/device.mk)

PRODUCT_DEVICE := ares
PRODUCT_NAME := twrp_ares
PRODUCT_BRAND := POCO
PRODUCT_MODEL := Poco F3 GT,Redmi K40 Gaming
PRODUCT_MANUFACTURER := xiaomi

BUILD_FINGERPRINT := POCO/vnd_ares/ares:12/SP1A.210812.016/V816.0.2.0.TKJINXM:user/release-keys

# HACK: Set vendor patch level
PRODUCT_PROPERTY_OVERRIDES += \
    ro.vendor.build.security_patch=2099-12-31
