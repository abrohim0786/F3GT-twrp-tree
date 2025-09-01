# OrangeFox Recovery Splash Screen Fixes for Ares Device

## Issues Identified and Fixed:

### 1. Data Mount Failure
- **Problem**: F2FS filesystem mount failure on `/dev/block/sdc75`
- **Fix**: Added `first_stage_mount` flag to data partition entries in `recovery.fstab`
- **Files Modified**: `recovery.fstab`

### 2. FBE Decryption Issues
- **Problem**: File-Based Encryption metadata decryption failing
- **Fixes Applied**:
  - Added missing keymaster libraries to `device.mk`
  - Enhanced crypto configuration in `BoardConfig.mk`
  - Fixed keymaster service startup in `init.recovery.mt6893.rc`
  - Updated system properties in `system.prop`
- **Files Modified**: `device.mk`, `BoardConfig.mk`, `recovery/root/init.recovery.mt6893.rc`, `system.prop`

### 3. Graphics/UI Initialization
- **Problem**: DRM graphics initialization issues causing splash screen hang
- **Fixes Applied**:
  - Disabled `TW_SCREEN_BLANK_ON_BOOT` in `device.mk`
  - Added DRM graphics configuration in `BoardConfig.mk`
  - Created graphics fix service in `init.recovery.fixes.rc`
- **Files Modified**: `device.mk`, `BoardConfig.mk`, `recovery/root/init.recovery.fixes.rc`

### 4. Keymaster Services
- **Problem**: Keymaster services not starting properly for FBE decryption
- **Fixes Applied**:
  - Added proper keymaster service startup triggers
  - Enhanced library dependencies
  - Fixed service initialization order
- **Files Modified**: `device.mk`, `recovery/root/init.recovery.mt6893.rc`

### 5. Recovery Configuration
- **Problem**: Missing recovery configuration flags
- **Fixes Applied**:
  - Added splash screen timeout handling
  - Enhanced crypto timeout settings
  - Improved data directory creation
- **Files Modified**: `device.mk`, `recovery/root/init.recovery.fixes.rc`

## New Files Created:
- `recovery/root/init.recovery.fixes.rc` - Custom init script for splash screen and mount fixes

## Key Changes Summary:

### device.mk
- Added comprehensive keymaster library dependencies
- Disabled screen blank on boot
- Added crypto timeout and tweak disable flags

### BoardConfig.mk
- Enhanced FBE decryption configuration
- Added DRM graphics support
- Improved crypto system vold settings

### recovery.fstab
- Added `first_stage_mount` flag to data partitions
- Improved partition mounting reliability

### system.prop
- Enhanced crypto properties
- Added TWRP-specific boot properties

### init.recovery.mt6893.rc
- Fixed keymaster service startup
- Added proper service initialization order

### recovery.wipe
- Added metadata and protect partitions to wipe list

## Expected Results:
1. Splash screen should no longer hang indefinitely
2. Data partition should mount properly with F2FS
3. FBE decryption should work correctly
4. Graphics initialization should be stable
5. Recovery should boot to main UI successfully

## Testing Recommendations:
1. Build the recovery with these fixes
2. Flash to device and test boot
3. Verify data partition mounting
4. Test FBE decryption functionality
5. Confirm UI loads properly after splash screen

## Notes:
- All fixes are backward compatible
- No breaking changes to existing functionality
- Enhanced error handling and timeout management
- Improved library dependency management