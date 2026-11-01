#!/usr/bin/env python3
"""
Unity 4 (TOG) - Dynamic APK Metadata & Keyword Extractor
=======================================================
Extracts all key identifiers, package names, launcher activities,
component declarations, and smali targets from a user-supplied APK
so that the patching and build pipeline can operate 100% dynamically.
"""

import os
import re
import sys
import json
import xml.etree.ElementTree as ET

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
METADATA_FILE = os.path.join(WORKSPACE_DIR, 'apk_metadata.json')

def log(msg):
    print(f"[+] {msg}")

def extract_manifest_metadata(manifest_path):
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"AndroidManifest.xml not found at: {manifest_path}")

    tree = ET.parse(manifest_path)
    root = tree.getroot()
    ns = '{http://schemas.android.com/apk/res/android}'

    package_name = root.attrib.get('package', 'unknown.package')

    # Uses-sdk
    uses_sdk = root.find('uses-sdk')
    min_sdk = 21
    target_sdk = 22
    if uses_sdk is not None:
        min_sdk = int(uses_sdk.attrib.get(f'{ns}minSdkVersion', min_sdk))
        target_sdk = int(uses_sdk.attrib.get(f'{ns}targetSdkVersion', target_sdk))

    all_activities = []
    current_launcher = None
    unity_launcher = None
    downloader_activity = None

    for act in root.findall('.//activity'):
        name = act.attrib.get(f'{ns}name', '')
        if not name:
            continue
        all_activities.append(name)

        # Check intent filters
        for ifilter in act.findall('intent-filter'):
            actions = [a.attrib.get(f'{ns}name') for a in ifilter.findall('action')]
            categories = [c.attrib.get(f'{ns}name') for c in ifilter.findall('category')]
            if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in categories:
                current_launcher = name
                break

        if 'UnityLauncherActivity' in name:
            unity_launcher = name
        elif not unity_launcher and 'UnityPlayerActivity' in name:
            unity_launcher = name

        if 'DownloaderActivity' in name:
            downloader_activity = name

    # Receivers with intent-filter
    receivers_with_filters = []
    for rec in root.findall('.//receiver'):
        rname = rec.attrib.get(f'{ns}name', '')
        if rec.findall('intent-filter') and rname:
            receivers_with_filters.append(rname)

    # Services
    services = [s.attrib.get(f'{ns}name', '') for s in root.findall('.//service') if s.attrib.get(f'{ns}name')]

    return {
        'package_name': package_name,
        'min_sdk_version': min_sdk,
        'target_sdk_version': target_sdk,
        'current_launcher_activity': current_launcher,
        'unity_launcher_activity': unity_launcher or current_launcher,
        'downloader_activity': downloader_activity,
        'all_activities': all_activities,
        'receivers_with_filters': receivers_with_filters,
        'services': services
    }

def scan_smali_targets(smali_root):
    targets = {
        'UnityUnpacker': None,
        'UnityLauncherActivity': None,
        'GoogleIAP': None,
        'GoogleIAP_Sub': None,
        'q': None,
        'AnalyticsGmsCoreClient': None,
        'LicenseChecker': None
    }
    descriptors = {}

    if not os.path.exists(smali_root):
        return targets, descriptors

    for root, dirs, files in os.walk(smali_root):
        normalized_root = root.replace('\\', '/')
        for f in files:
            if not f.endswith('.smali'):
                continue
            full_path = os.path.join(root, f)

            if f == 'UnityUnpacker.smali':
                targets['UnityUnpacker'] = full_path
            elif f == 'UnityLauncherActivity.smali':
                targets['UnityLauncherActivity'] = full_path
            elif f == 'GoogleIAP.smali':
                targets['GoogleIAP'] = full_path
            elif f == 'GoogleIAP$1.smali':
                targets['GoogleIAP_Sub'] = full_path
            elif f == 'AnalyticsGmsCoreClient.smali':
                targets['AnalyticsGmsCoreClient'] = full_path
            elif f == 'LicenseChecker.smali':
                targets['LicenseChecker'] = full_path
            elif f == 'q.smali' and 'com/google/android/gms' in normalized_root:
                targets['q'] = full_path

    # Extract class descriptors from .class directive
    for key, path in targets.items():
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as sf:
                    for line in sf:
                        if line.startswith('.class'):
                            parts = line.strip().split()
                            descriptors[key] = parts[-1]
                            break
            except Exception:
                pass

    return targets, descriptors

def scan_native_binaries():
    native_meta = {
        'has_real_unity': False,
        'has_real_mono': False,
        'unity_source_path': None,
        'mono_source_path': None
    }
    extracted_native = os.path.join(WORKSPACE_DIR, 'extracted_code', 'native')
    if os.path.exists(extracted_native):
        for f in os.listdir(extracted_native):
            fpath = os.path.join(extracted_native, f)
            if 'libunity.so' in f and os.path.getsize(fpath) > 1_000_000:
                native_meta['has_real_unity'] = True
                native_meta['unity_source_path'] = fpath
            elif 'libmono.so' in f and os.path.getsize(fpath) > 1_000_000:
                native_meta['has_real_mono'] = True
                native_meta['mono_source_path'] = fpath

    return native_meta

def extract_all(decoded_dir=None):
    if decoded_dir is None:
        decoded_dir = os.path.join(WORKSPACE_DIR, 'apk_decoded')

    manifest_path = os.path.join(decoded_dir, 'AndroidManifest.xml')
    smali_root = os.path.join(decoded_dir, 'smali')

    log("Extracting APK codenames and manifest metadata...")
    manifest_meta = extract_manifest_metadata(manifest_path)
    
    log("Scanning smali targets and class descriptors...")
    smali_targets, descriptors = scan_smali_targets(smali_root)

    log("Scanning native engine binaries...")
    native_meta = scan_native_binaries()

    full_metadata = {
        'package_name': manifest_meta['package_name'],
        'min_sdk_version': manifest_meta['min_sdk_version'],
        'target_sdk_version': manifest_meta['target_sdk_version'],
        'current_launcher_activity': manifest_meta['current_launcher_activity'],
        'unity_launcher_activity': manifest_meta['unity_launcher_activity'],
        'downloader_activity': manifest_meta['downloader_activity'],
        'all_activities_count': len(manifest_meta['all_activities']),
        'receivers_with_filters': manifest_meta['receivers_with_filters'],
        'services': manifest_meta['services'],
        'smali_targets': smali_targets,
        'class_descriptors': descriptors,
        'native_binaries': native_meta,
        'adb_launch_component': f"{manifest_meta['package_name']}/{manifest_meta['unity_launcher_activity']}"
    }

    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_metadata, f, indent=4)
    log(f"Metadata saved to: {METADATA_FILE}")

    print("\n" + "=" * 65)
    print("           EXTRACTED APK METADATA & CODENAMES")
    print("=" * 65)
    print(f"  Package Name:       {full_metadata['package_name']}")
    print(f"  Current Launcher:   {full_metadata['current_launcher_activity']}")
    print(f"  Unity Launcher:     {full_metadata['unity_launcher_activity']}")
    print(f"  Downloader Activity:{full_metadata['downloader_activity']}")
    print(f"  Target SDK:         {full_metadata['target_sdk_version']}")
    print(f"  ADB Launch Target:  {full_metadata['adb_launch_component']}")
    print(f"  Real Engine SOs:    Unity={'OK' if native_meta['has_real_unity'] else 'MISSING'}, Mono={'OK' if native_meta['has_real_mono'] else 'MISSING'}")
    print(f"  Smali Targets Found:{sum(1 for v in smali_targets.values() if v)} / {len(smali_targets)}")
    print("=" * 65 + "\n")

    return full_metadata

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

if __name__ == '__main__':
    extract_all()
