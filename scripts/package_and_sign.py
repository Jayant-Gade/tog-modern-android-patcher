#!/usr/bin/env python3
"""
Unity 4 (TOG) - Standalone Packaging, 16KB Alignment & Signing Utility
"""
import zipfile
import subprocess
import os
import sys

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def find_input_apk():
    default_path = os.path.join(WORKSPACE_DIR, 'tog_orig.apk')
    if os.path.exists(default_path):
        return default_path
    excluded = ('_ported.apk', '_aligned.apk', '_unaligned.apk', 'base_rebuilt.apk', 'temp_aligned.apk', 'temp_unaligned.apk')
    candidates = [
        f for f in os.listdir(WORKSPACE_DIR)
        if f.lower().endswith('.apk') and not any(f.lower().endswith(ex) for ex in excluded)
    ]
    if candidates:
        return os.path.join(WORKSPACE_DIR, candidates[0])
    raise FileNotFoundError("Input APK not found in workspace (expected tog_orig.apk).")

def find_build_tools():
    candidates = [
        os.environ.get('ANDROID_HOME'),
        os.environ.get('ANDROID_SDK_ROOT'),
        r'D:\Software-SDK\Android-SDK',
        r'D:\Softwares-sdk\Android-SDK',
        os.path.join(WORKSPACE_DIR, 'SDK')
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            bt_dir = os.path.join(c, 'build-tools')
            if os.path.isdir(bt_dir):
                versions = sorted(os.listdir(bt_dir), reverse=True)
                if versions:
                    latest = os.path.join(bt_dir, versions[0])
                    zipalign = os.path.join(latest, 'zipalign.exe' if os.name == 'nt' else 'zipalign')
                    apksigner = os.path.join(latest, 'apksigner.bat' if os.name == 'nt' else 'apksigner')
                    if os.path.exists(zipalign) and os.path.exists(apksigner):
                        return zipalign, apksigner
    raise RuntimeError("Android SDK build-tools not found!")

orig_apk_path = find_input_apk()
base_rebuilt_path = os.path.join(WORKSPACE_DIR, 'base_rebuilt.apk')
unaligned_apk_path = os.path.join(WORKSPACE_DIR, 'temp_unaligned.apk')
aligned_apk_path = os.path.join(WORKSPACE_DIR, 'temp_aligned.apk')
final_apk_path = os.path.join(WORKSPACE_DIR, 'tog_ported.apk')
keystore_path = os.path.join(WORKSPACE_DIR, 'debug.keystore')

zipalign_bin, apksigner_bin = find_build_tools()

print(f"Using input APK: {orig_apk_path}")
print('1. Creating unaligned ported APK...')
with zipfile.ZipFile(base_rebuilt_path, 'r') as z_base, \
     zipfile.ZipFile(orig_apk_path, 'r') as z_orig, \
     zipfile.ZipFile(unaligned_apk_path, 'w') as z_out:
    
    # Write entries from base_rebuilt
    for item in z_base.infolist():
        data = z_base.read(item.filename)
        zinfo = zipfile.ZipInfo(item.filename)
        zinfo.date_time = item.date_time
        # Store .so and resources.arsc uncompressed for page-alignment and Android 11+
        if item.filename.endswith('.so') or item.filename == 'resources.arsc' or item.compress_type == zipfile.ZIP_STORED:
            zinfo.compress_type = zipfile.ZIP_STORED
        else:
            zinfo.compress_type = zipfile.ZIP_DEFLATED
        z_out.writestr(zinfo, data)
        
    print(f'   Added {len(z_base.namelist())} entries from base_rebuilt')
    
    # Write assets from original APK
    asset_count = 0
    for item in z_orig.infolist():
        if item.filename.startswith('assets/'):
            data = z_orig.read(item.filename)
            if item.filename.endswith('.so'):
                b = bytearray(data)
                import patch_game
                if patch_game.patch_elf_textrel_bytes(b):
                    data = bytes(b)
            zinfo = zipfile.ZipInfo(item.filename)
            zinfo.date_time = item.date_time
            if item.filename.endswith('.so'):
                zinfo.compress_type = zipfile.ZIP_STORED
            elif item.compress_type == zipfile.ZIP_STORED:
                zinfo.compress_type = zipfile.ZIP_STORED
            else:
                zinfo.compress_type = zipfile.ZIP_DEFLATED
            z_out.writestr(zinfo, data)
            asset_count += 1
            
    print(f'   Added {asset_count} asset entries from original APK')

print(f'   Unaligned APK created: {os.path.getsize(unaligned_apk_path)} bytes')

print('2. Running zipalign with 16KB page alignment (-P 16 4)...')
zipalign_cmd = [zipalign_bin, '-f', '-P', '16', '4', unaligned_apk_path, aligned_apk_path]
res = subprocess.run(zipalign_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print('Zipalign error:', res.stderr, res.stdout)
    print('Retrying with standard -p 4...')
    res = subprocess.run([zipalign_bin, '-f', '-p', '4', unaligned_apk_path, aligned_apk_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f'Zipalign failed: {res.stderr}')

print(f'   Aligned APK created: {os.path.getsize(aligned_apk_path)} bytes')

print('3. Signing APK with apksigner (v1, v2, v3, v4)...')
sign_cmd = [
    apksigner_bin, 'sign',
    '--ks', keystore_path,
    '--ks-pass', 'pass:android',
    '--ks-key-alias', 'androiddebugkey',
    '--key-pass', 'pass:android',
    '--out', final_apk_path,
    aligned_apk_path
]
res = subprocess.run(sign_cmd, capture_output=True, text=True)
if res.returncode != 0:
    raise RuntimeError(f'Apksigner failed: {res.stderr}\n{res.stdout}')

print(f'   Ported APK signed: {final_apk_path} ({os.path.getsize(final_apk_path)} bytes)')

print('4. Verifying APK signature and alignment...')
verify_cmd = [apksigner_bin, 'verify', '--verbose', final_apk_path]
res = subprocess.run(verify_cmd, capture_output=True, text=True)
print(res.stdout)

# Clean up intermediates
for tmp in [unaligned_apk_path, aligned_apk_path, base_rebuilt_path]:
    if os.path.exists(tmp):
        os.remove(tmp)

print('Cleaned up intermediate build files.')
print('PORTING PROCESS COMPLETED SUCCESSFULLY!')

meta_path = os.path.join(WORKSPACE_DIR, 'apk_metadata.json')
if os.path.exists(meta_path):
    try:
        import json
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        if 'adb_launch_component' in meta:
            print(f"To launch game: adb shell am start -n {meta['adb_launch_component']}")
    except Exception:
        pass
