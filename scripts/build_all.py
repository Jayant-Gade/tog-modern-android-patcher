#!/usr/bin/env python3
"""
Unity 4 (TOG) - Modern Android Porting & Historical Preservation Pipeline
=========================================================================
This script automates the complete process from a legacy Unity 4 Android APK
to a fully ported, 16KB-page-aligned, Scoped-Storage-patched, and signed APK
compatible with modern Android (including Android 14, 15, and Android 16).

Usage:
    python scripts/build_all.py                         # Ports, patches, aligns, and signs
    python scripts/build_all.py --input my_game.apk     # Specify custom input APK
    python scripts/build_all.py --output out.apk        # Specify custom output APK
    python scripts/build_all.py --decompile             # Also decompiles C# and Java sources
"""

import sys
import os
import re
import shutil
import zipfile
import subprocess
import argparse

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_INPUT_APK = 'tog_orig.apk'
DEFAULT_OUTPUT_APK = 'tog_ported.apk'

def log(msg):
    print(f"[+] {msg}")

def resolve_input_apk(user_specified=None):
    if user_specified:
        path = os.path.abspath(user_specified) if os.path.isabs(user_specified) else os.path.join(WORKSPACE_DIR, user_specified)
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Specified input APK not found at: {path}")

    # Check default generic name
    default_path = os.path.join(WORKSPACE_DIR, DEFAULT_INPUT_APK)
    if os.path.exists(default_path):
        return default_path

    # Fallback auto-detection for any user-supplied APK in workspace
    excluded = ('_ported.apk', '_aligned.apk', '_unaligned.apk', 'base_rebuilt.apk', 'temp_aligned.apk', 'temp_unaligned.apk')
    candidates = [
        f for f in os.listdir(WORKSPACE_DIR)
        if f.lower().endswith('.apk') and not any(f.lower().endswith(ex) for ex in excluded)
    ]
    if candidates:
        selected = os.path.join(WORKSPACE_DIR, candidates[0])
        log(f"Auto-detected user input APK: {candidates[0]}")
        return selected

    raise FileNotFoundError(
        f"No input APK found! Please place '{DEFAULT_INPUT_APK}' in the project root or specify with --input <path.apk>."
    )

def find_android_sdk():
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
                        return c, latest, zipalign, apksigner
    raise RuntimeError("Android SDK build-tools not found! Please check ANDROID_HOME or D:/Software-SDK.")

def find_java():
    java_cmd = shutil.which('java')
    if java_cmd:
        return java_cmd
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        cand = os.path.join(java_home, 'bin', 'java.exe' if os.name == 'nt' else 'java')
        if os.path.exists(cand):
            return cand
    for cand in [r'D:\Softwares\jdk-17.0.18.8-hotspot\bin\java.exe', r'C:\Program Files\Java']:
        if os.path.exists(cand):
            return cand
    raise RuntimeError("Java executable not found in PATH or JAVA_HOME.")

def ensure_keystore():
    keystore_path = os.path.join(WORKSPACE_DIR, 'debug.keystore')
    if not os.path.exists(keystore_path):
        log("Generating debug keystore...")
        cmd = [
            'keytool', '-genkeypair', '-v',
            '-keystore', keystore_path,
            '-storepass', 'android',
            '-alias', 'androiddebugkey',
            '-keypass', 'android',
            '-keyalg', 'RSA',
            '-keysize', '2048',
            '-validity', '10000',
            '-dname', 'CN=Android Debug,O=Android,C=US'
        ]
        subprocess.run(cmd, check=True)
    return keystore_path

def step1_extract_binaries(orig_apk):
    log("Step 1: Extracting native and managed binaries...")
    out_dir = os.path.join(WORKSPACE_DIR, 'extracted_code')
    os.makedirs(os.path.join(out_dir, 'managed'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'native'), exist_ok=True)
    
    with zipfile.ZipFile(orig_apk, 'r') as z:
        for n in z.namelist():
            if n.startswith('assets/bin/Data/Managed/'):
                fname = os.path.basename(n)
                with open(os.path.join(out_dir, 'managed', fname), 'wb') as f:
                    f.write(z.read(n))
            elif n.startswith('lib/') or n.startswith('assets/libs/'):
                if n.endswith('.so'):
                    fname = n.replace('/', '_')
                    with open(os.path.join(out_dir, 'native', fname), 'wb') as f:
                        f.write(z.read(n))
            elif n in ['AndroidManifest.xml', 'classes.dex']:
                with open(os.path.join(out_dir, n), 'wb') as f:
                    f.write(z.read(n))
    log("Extracted core DLLs, native SOs, and classes.dex into extracted_code/")

def step2_decompile(java_bin):
    log("Step 2: Decompiling C# and Java sources (requested via --decompile)...")
    ilspycmd_dll = os.path.join(WORKSPACE_DIR, 'tools', 'ilspycmd', 'ilspycmd.dll')
    csharp_dll = os.path.join(WORKSPACE_DIR, 'extracted_code', 'managed', 'Assembly-CSharp.dll')
    firstpass_dll = os.path.join(WORKSPACE_DIR, 'extracted_code', 'managed', 'Assembly-CSharp-firstpass.dll')
    ref_dir = os.path.join(WORKSPACE_DIR, 'extracted_code', 'managed')

    if os.path.exists(ilspycmd_dll) and shutil.which('dotnet'):
        log("Decompiling Assembly-CSharp.dll...")
        subprocess.run([
            'dotnet', 'exec', ilspycmd_dll,
            '--nested-directories', '-p',
            '-o', os.path.join(WORKSPACE_DIR, 'source_code', 'Assembly-CSharp'),
            '-r', ref_dir, csharp_dll
        ], check=True)
        log("Decompiling Assembly-CSharp-firstpass.dll...")
        subprocess.run([
            'dotnet', 'exec', ilspycmd_dll,
            '--nested-directories', '-p',
            '-o', os.path.join(WORKSPACE_DIR, 'source_code', 'Assembly-CSharp-firstpass'),
            '-r', ref_dir, firstpass_dll
        ], check=True)

    jadx_bat = os.path.join(WORKSPACE_DIR, 'tools', 'jadx', 'bin', 'jadx.bat' if os.name == 'nt' else 'jadx')
    dex_file = os.path.join(WORKSPACE_DIR, 'extracted_code', 'classes.dex')
    if os.path.exists(jadx_bat):
        log("Decompiling classes.dex with jadx...")
        subprocess.run([
            jadx_bat, '-d', os.path.join(WORKSPACE_DIR, 'source_code', 'android_java'),
            dex_file
        ])
    log("Source decompilation complete.")

def step3_decode_apk(java_bin, orig_apk):
    log("Step 3: Decoding APK resources and manifest with apktool (--no-assets)...")
    apktool_jar = os.path.join(WORKSPACE_DIR, 'tools', 'apktool', 'apktool.jar')
    out_dir = os.path.join(WORKSPACE_DIR, 'apk_decoded')
    cmd = [
        java_bin, '-jar', apktool_jar,
        'd', '--no-assets', '-f',
        '-o', out_dir,
        orig_apk
    ]
    subprocess.run(cmd, check=True)
    log("APK decoded into apk_decoded/ (without heavy assets).")

def step4_extract_metadata():
    log("Step 4: Extracting APK codenames and manifest metadata dynamically...")
    sys.path.insert(0, os.path.dirname(__file__))
    import extract_metadata
    meta = extract_metadata.extract_all()
    log(f"Extracted Package Name: {meta['package_name']}")
    log(f"Extracted Unity Launcher: {meta['unity_launcher_activity']}")
    return meta

def step5_apply_patches(meta, target_sdk=37):
    log(f"Step 5: Applying dynamic compatibility patches (targetSdkVersion={target_sdk})...")
    sys.path.insert(0, os.path.dirname(__file__))
    import patch_game
    patch_game.apply_all_patches(target_sdk=target_sdk, meta=meta)

def step6_build_and_sign(java_bin, orig_apk, zipalign_bin, apksigner_bin, keystore_path, final_apk):
    log("Step 6: Rebuilding base APK with apktool...")
    apktool_jar = os.path.join(WORKSPACE_DIR, 'tools', 'apktool', 'apktool.jar')
    base_rebuilt = os.path.join(WORKSPACE_DIR, 'base_rebuilt.apk')
    unaligned = os.path.join(WORKSPACE_DIR, 'temp_unaligned.apk')
    aligned = os.path.join(WORKSPACE_DIR, 'temp_aligned.apk')

    subprocess.run([java_bin, '-jar', apktool_jar, 'b', os.path.join(WORKSPACE_DIR, 'apk_decoded'), '-o', base_rebuilt], check=True)

    log("Step 7: Packaging assets and uncompressed native libraries...")
    with zipfile.ZipFile(base_rebuilt, 'r') as z_base, \
         zipfile.ZipFile(orig_apk, 'r') as z_orig, \
         zipfile.ZipFile(unaligned, 'w') as z_out:
        
        for item in z_base.infolist():
            data = z_base.read(item.filename)
            zinfo = zipfile.ZipInfo(item.filename)
            zinfo.date_time = item.date_time
            # Store .so and resources.arsc uncompressed for Android 11+ (API 30+) requirements
            if item.filename.endswith('.so') or item.filename == 'resources.arsc' or item.compress_type == zipfile.ZIP_STORED:
                zinfo.compress_type = zipfile.ZIP_STORED
            else:
                zinfo.compress_type = zipfile.ZIP_DEFLATED
            z_out.writestr(zinfo, data)
            
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
                if item.filename.endswith('.so') or item.compress_type == zipfile.ZIP_STORED:
                    zinfo.compress_type = zipfile.ZIP_STORED
                else:
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                z_out.writestr(zinfo, data)

    log("Step 8: Executing 16KB page alignment (zipalign -P 16 4)...")
    res = subprocess.run([zipalign_bin, '-f', '-P', '16', '4', unaligned, aligned], capture_output=True, text=True)
    if res.returncode != 0:
        log("Retrying with standard page alignment -p 4...")
        subprocess.run([zipalign_bin, '-f', '-p', '4', unaligned, aligned], check=True)

    log("Step 9: Signing APK with apksigner...")
    subprocess.run([
        apksigner_bin, 'sign',
        '--ks', keystore_path,
        '--ks-pass', 'pass:android',
        '--ks-key-alias', 'androiddebugkey',
        '--key-pass', 'pass:android',
        '--out', final_apk,
        aligned
    ], check=True)

    log("Step 10: Verifying signature...")
    res = subprocess.run([apksigner_bin, 'verify', '--verbose', final_apk], capture_output=True, text=True)
    print(res.stdout)

    # Clean intermediate files
    for temp in [base_rebuilt, unaligned, aligned]:
        if os.path.exists(temp):
            os.remove(temp)

    log(f"SUCCESS! Ported APK generated: {final_apk}")

def main():
    parser = argparse.ArgumentParser(description="Unity 4 (TOG) Modern Android Porting Pipeline")
    parser.add_argument('--input', '-i', type=str, default=None, help=f"Path to input APK (default: auto-detect or {DEFAULT_INPUT_APK})")
    parser.add_argument('--output', '-o', type=str, default=None, help=f"Path to output APK (default: {DEFAULT_OUTPUT_APK})")
    parser.add_argument('--decompile', action='store_true', help="Also decompile C# and Java source trees")
    parser.add_argument('--target-sdk', type=int, default=37, help="Target SDK version (default: 37 for Android 17 / HyperOS 3; 22-37 supported)")
    parser.add_argument('--install', type=str, nargs='?', const='127.0.0.1:58526', help="Install directly to ADB device/emulator (default: 127.0.0.1:58526)")
    args = parser.parse_args()

    orig_apk = resolve_input_apk(args.input)
    if args.output:
        final_apk = os.path.abspath(args.output) if os.path.isabs(args.output) else os.path.join(WORKSPACE_DIR, args.output)
    else:
        final_apk = os.path.join(WORKSPACE_DIR, DEFAULT_OUTPUT_APK)

    sdk_dir, bt_dir, zipalign_bin, apksigner_bin = find_android_sdk()
    java_bin = find_java()
    keystore = ensure_keystore()

    log(f"Input APK: {orig_apk}")
    log(f"Output APK: {final_apk}")
    log(f"Target SDK: {args.target_sdk} (Android 17 / Modern Android)")
    log(f"Android SDK: {sdk_dir} (build-tools {os.path.basename(bt_dir)})")
    log(f"Java Binary: {java_bin}")

    step1_extract_binaries(orig_apk)
    if args.decompile:
        step2_decompile(java_bin)
    step3_decode_apk(java_bin, orig_apk)
    meta = step4_extract_metadata()
    step5_apply_patches(meta=meta, target_sdk=args.target_sdk)
    step6_build_and_sign(java_bin, orig_apk, zipalign_bin, apksigner_bin, keystore, final_apk)

    log(f"To launch game on connected device:")
    log(f"  adb shell am start -n {meta['adb_launch_component']}")

    if args.install:
        adb_bin = os.path.join(sdk_dir, 'platform-tools', 'adb.exe' if os.name == 'nt' else 'adb')
        log(f"Installing onto {args.install}...")
        subprocess.run([adb_bin, 'connect', args.install])
        subprocess.run([adb_bin, '-s', args.install, 'install', '--bypass-low-target-sdk-block', '--no-incremental', '-r', final_apk])

if __name__ == '__main__':
    main()
