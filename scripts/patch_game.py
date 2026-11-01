#!/usr/bin/env python3
"""
Unity 4 (TOG) - Dynamic Compatibility Patcher
=============================================
Consumes dynamically extracted APK metadata from extract_metadata.py
to patch Scoped Storage, explicit service intents, and modern manifest
rules without relying on hardcoded package or activity names.
"""

import re
import os
import sys
import shutil
import json

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def log(msg):
    print(f"[+] {msg}")

def get_or_extract_metadata():
    sys.path.insert(0, os.path.dirname(__file__))
    import extract_metadata
    meta = extract_metadata.load_metadata()
    if not meta:
        meta = extract_metadata.extract_all()
    return meta

def patch_elf_textrel_bytes(data: bytearray) -> bool:
    """
    Dynamically eliminates DT_TEXTREL from 32-bit ARM ELF shared libraries and
    nullifies relocations targeting read-only (.text) segments so modern Bionic
    linkers (API >= 23, up to Android 17 / HyperOS 3) load them without UnsatisfiedLinkError.
    Returns True if modifications were made.
    """
    import struct
    if len(data) < 52 or data[:4] != b'\x7fELF':
        return False
    if data[4] != 1:  # Only 32-bit ELF (ELFCLASS32)
        return False

    patched = False
    # 1. Parse ELF Header
    e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<IIIHHHHHH', data, 28)
    load_segments = []
    for i in range(e_phnum):
        ph_offset = e_phoff + i * e_phentsize
        if ph_offset + 32 > len(data):
            break
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack_from('<IIIIIIII', data, ph_offset)
        if p_type == 1: # PT_LOAD
            load_segments.append({'vaddr': p_vaddr, 'memsz': p_memsz, 'writable': bool(p_flags & 2)})
        elif p_type == 2: # PT_DYNAMIC
            for d in range(p_offset, min(len(data), p_offset + p_filesz), 8):
                if d + 8 > len(data):
                    break
                d_tag, d_val = struct.unpack_from('<II', data, d)
                if d_tag == 0x16: # DT_TEXTREL
                    struct.pack_into('<II', data, d, 0x0, 0x0) # DT_NULL
                    patched = True
                elif d_tag == 0x1e: # DT_FLAGS
                    if d_val & 0x4: # DF_TEXTREL
                        struct.pack_into('<I', data, d + 4, d_val & ~0x4)
                        patched = True

    # 2. Parse ELF Section Headers and nullify relocations targeting read-only segments
    if e_shoff > 0 and e_shnum > 0:
        for s in range(e_shnum):
            sh_offset = e_shoff + s * e_shentsize
            if sh_offset + 40 > len(data):
                break
            sh_name, sh_type, sh_flags, sh_addr, sh_offset_sec, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack_from('<IIIIIIIIII', data, sh_offset)
            if sh_type == 9: # SHT_REL
                for r in range(sh_offset_sec, min(len(data), sh_offset_sec + sh_size), 8):
                    if r + 8 > len(data):
                        break
                    r_offset, r_info = struct.unpack_from('<II', data, r)
                    if (r_info & 0xff) != 0: # not R_ARM_NONE
                        for seg in load_segments:
                            if seg['vaddr'] <= r_offset < seg['vaddr'] + seg['memsz'] and not seg['writable']:
                                struct.pack_into('<II', data, r, 0x0, 0x0) # R_ARM_NONE
                                patched = True
    return patched

def patch_unity_textrel(so_path):
    if not os.path.exists(so_path):
        return
    with open(so_path, 'rb') as f:
        data = bytearray(f.read())

    if patch_elf_textrel_bytes(data):
        with open(so_path, 'wb') as f:
            f.write(data)
        log(f"Patched {os.path.basename(so_path)} (eliminated DT_TEXTREL and converted text relocations to R_ARM_NONE).")

def replace_stubs(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    native_dir = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'lib', 'armeabi-v7a')
    os.makedirs(native_dir, exist_ok=True)
    
    unity_src = meta.get('native_binaries', {}).get('unity_source_path')
    mono_src = meta.get('native_binaries', {}).get('mono_source_path')

    target_unity = os.path.join(native_dir, 'libunity.so')
    target_mono = os.path.join(native_dir, 'libmono.so')

    if unity_src and os.path.exists(unity_src):
        shutil.copy(unity_src, target_unity)
        patch_unity_textrel(target_unity)
    if mono_src and os.path.exists(mono_src):
        shutil.copy(mono_src, target_mono)
        patch_unity_textrel(target_mono)

    log("Replaced stub loaders with full engine binaries (libunity.so, libmono.so).")

def patch_unity_unpacker(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('UnityUnpacker')
    if not smali_path or not os.path.exists(smali_path):
        return

    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    replacement = '''.method public static cachePath(Landroid/content/Context;)Ljava/io/File;
    .locals 3

    const/4 v0, 0x0

    invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;

    move-result-object v1

    if-nez v1, :cond_0

    invoke-virtual {p0}, Landroid/content/Context;->getFilesDir()Ljava/io/File;

    move-result-object v1

    :cond_0
    new-instance v0, Ljava/io/File;

    const-string v2, "UnityCache"

    invoke-direct {v0, v1, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    return-object v0
.end method'''

    pattern = r'\.method public static cachePath\(Landroid/content/Context;\)Ljava/io/File;[\s\S]*?\.end method'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(content)
        log(f"Patched {os.path.basename(smali_path)} (Scoped Storage Cache).")

def patch_unity_launcher(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('UnityLauncherActivity')
    if not smali_path or not os.path.exists(smali_path):
        return

    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    target = 'invoke-super {p0, p1}, Lcom/unity3d/player/UnityPlayerActivity;->onCreate(Landroid/os/Bundle;)V'
    patch = '''invoke-super {p0, p1}, Lcom/unity3d/player/UnityPlayerActivity;->onCreate(Landroid/os/Bundle;)V

    const/4 v0, 0x0

    :try_start_extdir
    invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    :try_end_extdir
    .catch Ljava/lang/Throwable; {:try_start_extdir .. :try_end_extdir} :catch_extdir

    :catch_extdir'''

    if target in content and ':try_start_extdir' not in content:
        content = content.replace(target, patch, 1)
        with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(content)
        log(f"Patched {os.path.basename(smali_path)} (Scoped Storage Pre-initialization in onCreate).")

def patch_gms_internal_q(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('q')
    if not smali_path or not os.path.exists(smali_path):
        return

    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_target = '''    new-instance v3, Landroid/content/Intent;

    const-string v4, "com.google.android.gms.games.service.START"

    invoke-direct {v3, v4}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    iget-object v4, p0, Lcom/google/android/gms/internal/q;->b:Landroid/content/Context;'''

    new_target = '''    new-instance v3, Landroid/content/Intent;

    const-string v4, "com.google.android.gms.games.service.START"

    invoke-direct {v3, v4}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v4, "com.google.android.gms"

    invoke-virtual {v3, v4}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;

    iget-object v4, p0, Lcom/google/android/gms/internal/q;->b:Landroid/content/Context;'''

    old_target_2 = '''    new-instance v4, Landroid/content/Intent;

    const-string v5, "com.google.android.gms.games.service.START"

    invoke-direct {v4, v5}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    iget-object v5, p0, Lcom/google/android/gms/internal/q;->b:Landroid/content/Context;'''

    new_target_2 = '''    new-instance v4, Landroid/content/Intent;

    const-string v5, "com.google.android.gms.games.service.START"

    invoke-direct {v4, v5}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v5, "com.google.android.gms"

    invoke-virtual {v4, v5}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;

    iget-object v5, p0, Lcom/google/android/gms/internal/q;->b:Landroid/content/Context;'''

    patched = False
    if old_target in content:
        content = content.replace(old_target, new_target, 1)
        patched = True
    if old_target_2 in content:
        content = content.replace(old_target_2, new_target_2, 1)
        patched = True

    if patched:
        with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(content)
        log("Patched GMS internal q.smali (Explicit Play Games Service Intent).")

def patch_google_iap(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('GoogleIAP')
    if smali_path and os.path.exists(smali_path):
        with open(smali_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'(new-instance v2, Landroid/content/Intent;\s+invoke-direct \{v2, v0\}, Landroid/content/Intent;-><init>\(Ljava/lang/String;\)V\s+)(iget-object v3, p0, L[^;]+/GoogleIAP;->mServiceConn:Landroid/content/ServiceConnection;)'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1const-string v3, "com.android.vending"\n\n    invoke-virtual {v2, v3}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;\n\n    \2', content, count=1)
            with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(content)
            log("Patched GoogleIAP.smali (Explicit InAppBilling Service Intent).")

    smali_path_sub = meta.get('smali_targets', {}).get('GoogleIAP_Sub')
    if smali_path_sub and os.path.exists(smali_path_sub):
        with open(smali_path_sub, 'r', encoding='utf-8') as f:
            content = f.read()

        old_sub = '''    new-instance v1, Landroid/content/Intent;

    const-string v2, "com.android.vending.billing.InAppBillingService.BIND"

    invoke-direct {v1, v2}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const/4 v2, 0x1'''

        new_sub = '''    new-instance v1, Landroid/content/Intent;

    const-string v2, "com.android.vending.billing.InAppBillingService.BIND"

    invoke-direct {v1, v2}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v2, "com.android.vending"

    invoke-virtual {v1, v2}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;

    const/4 v2, 0x1'''

        if old_sub in content:
            content = content.replace(old_sub, new_sub, 1)
            with open(smali_path_sub, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(content)
            log("Patched GoogleIAP$1.smali (Explicit InAppBilling Service Intent).")

def patch_analytics(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('AnalyticsGmsCoreClient')
    if not smali_path or not os.path.exists(smali_path):
        return

    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_target = '''    new-instance v0, Landroid/content/Intent;

    const-string v1, "com.google.android.gms.analytics.service.START"

    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V'''

    new_target = '''    new-instance v0, Landroid/content/Intent;

    const-string v1, "com.google.android.gms.analytics.service.START"

    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v1, "com.google.android.gms"

    invoke-virtual {v0, v1}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;'''

    if old_target in content:
        content = content.replace(old_target, new_target, 1)
        with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(content)
        log("Patched AnalyticsGmsCoreClient.smali (Explicit Analytics Service Intent).")

def patch_license_checker(meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    smali_path = meta.get('smali_targets', {}).get('LicenseChecker')
    if not smali_path or not os.path.exists(smali_path):
        return

    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_target = '''    new-instance v2, Landroid/content/Intent;

    new-instance v3, Ljava/lang/String;

    sget-object v4, Lcom/android/vending/licensing/LicenseChecker;->a:[B

    invoke-static {v4}, Lcom/android/vending/licensing/a/a;->a([B)[B

    move-result-object v4

    invoke-direct {v3, v4}, Ljava/lang/String;-><init>([B)V

    invoke-direct {v2, v3}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V'''

    new_target = '''    new-instance v2, Landroid/content/Intent;

    new-instance v3, Ljava/lang/String;

    sget-object v4, Lcom/android/vending/licensing/LicenseChecker;->a:[B

    invoke-static {v4}, Lcom/android/vending/licensing/a/a;->a([B)[B

    move-result-object v4

    invoke-direct {v3, v4}, Ljava/lang/String;-><init>([B)V

    invoke-direct {v2, v3}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v3, "com.android.vending"

    invoke-virtual {v2, v3}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;'''

    if old_target in content:
        content = content.replace(old_target, new_target, 1)
        with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(content)
        log("Patched LicenseChecker.smali (Explicit Licensing Service Intent).")

def patch_manifest(target_sdk=37, meta=None):
    if meta is None:
        meta = get_or_extract_metadata()

    manifest_path = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'AndroidManifest.xml')
    if not os.path.exists(manifest_path):
        return

    with open(manifest_path, 'r', encoding='utf-8') as f:
        m = f.read()

    # 1. Application tags
    if 'android:extractNativeLibs="true"' not in m:
        m = re.sub(r'<application\b', '<application android:extractNativeLibs="true" android:usesCleartextTraffic="true" android:requestLegacyExternalStorage="true" android:hardwareAccelerated="true"', m, count=1)

    # 2. Add exported="true" to components
    def add_exported(match):
        tag = match.group(0)
        if 'android:exported=' in tag:
            return tag
        if tag.endswith('/>'):
            return tag[:-2].rstrip() + ' android:exported="true"/>'
        elif tag.endswith('>'):
            return tag[:-1].rstrip() + ' android:exported="true">'
        return tag

    m = re.sub(r'<(?:activity|service|receiver)[^>]*>', add_exported, m)

    # 3. Dynamic Launcher resolution from extracted metadata
    unity_launcher = meta.get('unity_launcher_activity')
    downloader = meta.get('downloader_activity')

    if unity_launcher:
        # Remove duplicate UnityLauncherActivity declarations if any
        m = re.sub(rf'<activity[^>]*?{re.escape(unity_launcher)}[^>]*?/>\s*', '', m)

        # Reroute launcher intent from downloader to unity_launcher
        old_launcher_pattern = r'<activity\s+[^>]*?DownloaderActivity[^>]*?>\s*<intent-filter>\s*<action\s+android:name="android\.intent\.action\.MAIN"\s*/>\s*<category\s+android:name="android\.intent\.category\.LAUNCHER"\s*/>\s*</intent-filter>\s*</activity>'

        downloader_tag = f'<activity android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize" android:label="@string/app_name" android:name="{downloader}" android:screenOrientation="sensorLandscape" android:exported="true"/>' if downloader else ''
        new_launcher = f'''{downloader_tag}
        <activity android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize" android:label="@string/app_name" android:launchMode="singleTask" android:name="{unity_launcher}" android:screenOrientation="sensorLandscape" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>'''
        m = re.sub(old_launcher_pattern, new_launcher, m)

    # 4. Uses-sdk (Bump targetSdkVersion to 37 and remove any restrictive maxSdkVersion)
    m = re.sub(r'\s+android:maxSdkVersion="[^"]*"', '', m)
    if '<uses-sdk' not in m:
        uses_sdk = f'    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="{target_sdk}"/>\n'
        m = re.sub(r'(<manifest\b[^>]*>)', r'\1\n' + uses_sdk, m, count=1)
    else:
        m = re.sub(r'android:targetSdkVersion="[^"]*"', f'android:targetSdkVersion="{target_sdk}"', m)

    with open(manifest_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(m)
    log(f"Patched AndroidManifest.xml for package '{meta['package_name']}' (targetSdkVersion={target_sdk}, launcher={unity_launcher}).")

    # 5. apktool.yml
    yml_path = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'apktool.yml')
    if os.path.exists(yml_path):
        with open(yml_path, 'r', encoding='utf-8') as f:
            yml = f.read()
        yml = re.sub(r'minSdkVersion:\s*\d+', 'minSdkVersion: 21', yml)
        yml = re.sub(r'targetSdkVersion:\s*\d+', f'targetSdkVersion: {target_sdk}', yml)
        with open(yml_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(yml)
        log(f"Patched apktool.yml (targetSdkVersion={target_sdk}).")

def apply_all_patches(target_sdk=37, meta=None):
    log(f"Applying all compatibility patches with dynamic metadata (targetSdkVersion={target_sdk})...")
    if meta is None:
        meta = get_or_extract_metadata()

    replace_stubs(meta)
    patch_unity_unpacker(meta)
    patch_unity_launcher(meta)
    patch_gms_internal_q(meta)
    patch_google_iap(meta)
    patch_analytics(meta)
    patch_license_checker(meta)
    patch_manifest(target_sdk=target_sdk, meta=meta)
    log(f"All patches successfully applied for package '{meta['package_name']}'.")

if __name__ == '__main__':
    apply_all_patches(target_sdk=37)
