import subprocess
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

def patch_arm_cp15_barriers_bytes(data: bytearray) -> int:
    """
    Replaces legacy ARMv6 CP15 Data Memory Barriers (mcr p15, 0, r3, c7, c10, 5 -> ba 3f 07 ee)
    with standard ARMv7 DMB ISH (5b f0 7f f5) in 32-bit ARM binaries.
    Modern kernels (Android 14/15/16, Linux 5.15+) do not trap/emulate CP15 memory barriers
    for 32-bit user-space processes, leading to fatal SIGILL (Illegal Instruction) crashes.
    """
    target = bytes.fromhex('ba 3f 07 ee')
    replacement = bytes.fromhex('5b f0 7f f5')
    count = data.count(target)
    if count > 0:
        data[:] = data.replace(target, replacement)
    return count

def patch_native_device_id_bytes(data: bytearray) -> int:
    """
    Replaces standalone '\x00getDeviceId\x00' with '\x00toString\x00\x00\x00\x00' in native shared libraries.
    Prevents JNI calls to TelephonyManager.getDeviceId() from throwing SecurityException and aborting
    via ART's AssertNoPendingException check.
    """
    target = b'\x00getDeviceId\x00'
    replacement = b'\x00toString\x00\x00\x00\x00'
    count = data.count(target)
    if count > 0:
        data[:] = data.replace(target, replacement)
    return count

def patch_native_telephony_calls(meta=None):
    """
    Patches decoded and extracted native libraries to neutralize getDeviceId calls in native libraries.
    """
    dirs = [
        os.path.join(WORKSPACE_DIR, 'extracted_code', 'native'),
        os.path.join(WORKSPACE_DIR, 'apk_decoded', 'lib'),
    ]
    for d in dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith('.so'):
                        p = os.path.join(root, f)
                        with open(p, 'rb') as fp:
                            b = bytearray(fp.read())
                        c = patch_native_device_id_bytes(b)
                        if c > 0:
                            with open(p, 'wb') as fp:
                                fp.write(b)
                            log(f"Patched {c} native getDeviceId JNI string(s) in {f} -> toString")

def patch_arm_cp15_barriers(meta=None):
    """
    Scans and patches extracted and decoded native libraries to eliminate legacy ARMv6 CP15 barriers.
    """
    dirs_to_check = [
        os.path.join(WORKSPACE_DIR, 'extracted_code', 'native'),
        os.path.join(WORKSPACE_DIR, 'apk_decoded', 'lib'),
    ]
    for d in dirs_to_check:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith('.so'):
                        p = os.path.join(root, f)
                        with open(p, 'rb') as fp:
                            b = bytearray(fp.read())
                        c = patch_arm_cp15_barriers_bytes(b)
                        if c > 0:
                            with open(p, 'wb') as fp:
                                fp.write(b)
                            log(f"Patched {c} CP15 DMB barrier instruction(s) in {f} -> ARMv7 dmb ish")

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

    lib_base = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'lib')
    native_dir = os.path.join(lib_base, 'armeabi-v7a')
    os.makedirs(native_dir, exist_ok=True)
    
    unity_src = meta.get('native_binaries', {}).get('unity_source_path')
    mono_src = meta.get('native_binaries', {}).get('mono_source_path')

    target_unity = os.path.join(native_dir, 'libunity.so')
    target_mono = os.path.join(native_dir, 'libmono.so')

    if unity_src and os.path.exists(unity_src):
        shutil.copy(unity_src, target_unity)
    if mono_src and os.path.exists(mono_src):
        shutil.copy(mono_src, target_mono)

    # Patch ALL .so files across all ABIs in apk_decoded/lib to eliminate DT_TEXTREL
    if os.path.exists(lib_base):
        for root, _, files in os.walk(lib_base):
            for f in files:
                if f.lower().endswith('.so'):
                    patch_unity_textrel(os.path.join(root, f))

    patch_arm_cp15_barriers(meta)
    patch_native_telephony_calls(meta)
    log("Replaced stub loaders, eliminated DT_TEXTREL, and patched native libraries.")

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

    pattern = r'(invoke-direct \{(v\d+), p1\}, Landroid/content/Intent;-><init>\(Ljava/lang/String;\)V)'
    def repl(m):
        full = m.group(1)
        reg = m.group(2)
        temp_reg = 'v4' if reg == 'v3' else 'v3'
        return f'{full}\n\n    const-string {temp_reg}, "com.google.android.gms"\n\n    invoke-virtual {{{reg}, {temp_reg}}}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;'

    if 'com.google.android.gms' not in content:
        content, count = re.subn(pattern, repl, content)
        if count > 0:
            with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(content)
            log(f"Patched {os.path.basename(smali_path)} ({count} Explicit GMS Service Intents).")

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

    pattern = r'(invoke-direct \{(v\d+), [^}]+?\}, Landroid/content/Intent;-><init>\(Ljava/lang/String;\)V\s+)(const-string)'
    def repl(m):
        full_intent = m.group(1)
        reg = m.group(2)
        rest = m.group(3)
        return f'{full_intent}const-string v1, "com.google.android.gms"\n\n    invoke-virtual {{{reg}, v1}}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;\n\n    {rest}'

    if 'setPackage' not in content and 'com.google.android.gms.analytics.service.START' in content:
        content, count = re.subn(pattern, repl, content, count=1)
        if count > 0:
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

    pattern = r'(invoke-direct \{(v\d+), (v\d+)\}, Landroid/content/Intent;-><init>\(Ljava/lang/String;\)V)(\s+const/4 \w+, 0x1\s+invoke-virtual \{[^}]+?\}, Landroid/content/Context;->bindService)'
    def repl(m):
        full_init = m.group(1)
        intent_reg = m.group(2)
        bind_part = m.group(4)
        return f'{full_init}\n\n    const-string v4, "com.android.vending"\n\n    invoke-virtual {{{intent_reg}, v4}}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;{bind_part}'

    if 'com.android.vending' not in content and 'bindService' in content:
        content, count = re.subn(pattern, repl, content, count=1)
        if count > 0:
            with open(smali_path, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(content)
            log("Patched LicenseChecker.smali (Explicit Licensing Service Intent).")

def patch_telephony_device_id(meta=None):
    """
    On Android 10+ (API >= 29) and modern OS builds, TelephonyManager.getDeviceId()
    throws SecurityException for non-privileged apps.
    Creates a compatibility helper and redirects all getDeviceId() invocations across
    smali to invoke-static Lcompat/TelephonyCompat;->getDeviceId(...) returning an empty string.
    This preserves try-catch boundaries, register allocations, and move-result instructions.
    """
    smali_dir = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'smali')
    if not os.path.exists(smali_dir):
        return

    # 1. Create compat helper class in smali/compat/TelephonyCompat.smali
    compat_dir = os.path.join(smali_dir, 'compat')
    os.makedirs(compat_dir, exist_ok=True)
    compat_smali = os.path.join(compat_dir, 'TelephonyCompat.smali')
    compat_code = """.class public Lcompat/TelephonyCompat;
.super Ljava/lang/Object;
.source "TelephonyCompat.java"

.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static getDeviceId(Landroid/telephony/TelephonyManager;)Ljava/lang/String;
    .locals 1

    const-string v0, ""

    return-object v0
.end method
"""
    with open(compat_smali, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(compat_code)

    # 2. Redirect all getDeviceId invocations
    pattern_normal = re.compile(r'invoke-virtual\s*(\{[^}]*\}),\s*Landroid/telephony/TelephonyManager;->getDeviceId\(\)Ljava/lang/String;')
    pattern_range = re.compile(r'invoke-virtual/range\s*(\{[^}]*\}),\s*Landroid/telephony/TelephonyManager;->getDeviceId\(\)Ljava/lang/String;')

    count = 0
    for root, _, files in os.walk(smali_dir):
        for f in files:
            if f.endswith('.smali') and f != 'TelephonyCompat.smali':
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                new_content, n1 = pattern_normal.subn(r'invoke-static \g<1>, Lcompat/TelephonyCompat;->getDeviceId(Landroid/telephony/TelephonyManager;)Ljava/lang/String;', content)
                new_content, n2 = pattern_range.subn(r'invoke-static/range \g<1>, Lcompat/TelephonyCompat;->getDeviceId(Landroid/telephony/TelephonyManager;)Ljava/lang/String;', new_content)
                if (n1 + n2) > 0:
                    count += (n1 + n2)
                    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
                        fp.write(new_content)
    if count > 0:
        log(f"Patched {count} getDeviceId() calls to route through TelephonyCompat (neutralized SecurityException).")

def patch_manifest(target_sdk=22, meta=None):
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

    # Legacy Apache HTTP library (required on targetSdk >= 28)
    if 'org.apache.http.legacy' not in m:
        m = re.sub(r'(<application\b[^>]*>)', r'\1\n        <uses-library android:name="org.apache.http.legacy" android:required="false"/>', m, count=1)

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

def set_target_sdk(target_sdk):
    manifest_path = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'AndroidManifest.xml')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            m = f.read()
        m = re.sub(r'android:targetSdkVersion="[^"]*"', f'android:targetSdkVersion="{target_sdk}"', m)
        m = re.sub(r'\s+android:maxSdkVersion="[^"]*"', '', m)
        if target_sdk >= 28 and 'org.apache.http.legacy' not in m:
            m = re.sub(r'(<application\b[^>]*>)', r'\1\n        <uses-library android:name="org.apache.http.legacy" android:required="false"/>', m, count=1)
        with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(m)
        log(f"Updated AndroidManifest.xml targetSdkVersion to {target_sdk}")

    yml_path = os.path.join(WORKSPACE_DIR, 'apk_decoded', 'apktool.yml')
    if os.path.exists(yml_path):
        with open(yml_path, 'r', encoding='utf-8') as f:
            yml = f.read()
        yml = re.sub(r'targetSdkVersion:\s*\d+', f'targetSdkVersion: {target_sdk}', yml)
        with open(yml_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(yml)
        log(f"Updated apktool.yml targetSdkVersion to {target_sdk}")

def patch_assembly_csharp_accelerometer_aim(meta=None):
    dll_path = os.path.join(WORKSPACE_DIR, 'extracted_code', 'managed', 'Assembly-CSharp.dll')
    if not os.path.exists(dll_path):
        return
    with open(dll_path, 'rb') as f:
        dll = bytearray(f.read())

    # Target in camera controller Awake (route to accelerometer tilt aiming)
    target_pattern = bytes.fromhex('02 72 29 ab 00 70 16 28 8f 08 00 0a 7d e1 03 00 04 02 7b e1 03 00 04 3a 41 00 00 00 28 2a 07 00 0a 39 16 00 00 00 02 18 7d e1 03 00 04 72 3b ab 00 70 28 2c 00 00 0a 38 11 00 00 00')
    replacement = bytes([0x38, 0x37, 0x00, 0x00, 0x00]) + bytes([0x00] * (len(target_pattern) - 5))

    if target_pattern in dll:
        dll = dll.replace(target_pattern, replacement, 1)
        with open(dll_path, 'wb') as f:
            f.write(dll)
        log("Patched Assembly-CSharp.dll (Activated Accelerometer Tilt Aiming Mode for tablet/gyro fallback).")


def patch_assembly_csharp_gyro_camera(meta=None):
    dll_path = os.path.join(WORKSPACE_DIR, 'extracted_code', 'managed', 'Assembly-CSharp.dll')
    if not os.path.exists(dll_path):
        return
    ps_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patch_camera.ps1')
    if not os.path.exists(ps_script):
        ps_script = os.path.join(WORKSPACE_DIR, 'scripts', 'patch_camera.ps1')
    if os.path.exists(ps_script):
        cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps_script, '-DllPath', dll_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            log("Patched Assembly-CSharp.dll (Live Gyroscope sensitivity and jitter damping controls).")
        else:
            log(f"Warning: patch_camera.ps1 returned code {res.returncode}: {res.stderr or res.stdout}")

def apply_all_patches(target_sdk=22, meta=None):
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
    patch_telephony_device_id(meta)
    patch_assembly_csharp_accelerometer_aim(meta)
    patch_assembly_csharp_gyro_camera(meta)
    patch_arm_cp15_barriers(meta)
    patch_native_telephony_calls(meta)
    patch_manifest(target_sdk=target_sdk, meta=meta)
    log(f"All patches successfully applied for package '{meta['package_name']}'.")

if __name__ == '__main__':
    apply_all_patches(target_sdk=22)
