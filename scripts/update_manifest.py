import re
import os

manifest_path = 'apk_decoded/AndroidManifest.xml'
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()

# 1. Update application tag with necessary modern flags
if 'android:extractNativeLibs="true"' not in manifest:
    manifest = re.sub(
        r'<application\b',
        '<application android:extractNativeLibs="true" android:usesCleartextTraffic="true" android:requestLegacyExternalStorage="true" android:hardwareAccelerated="true"',
        manifest,
        count=1
    )

if 'org.apache.http.legacy' not in manifest:
    manifest = re.sub(
        r'(<application\b[^>]*>)',
        r'\1\n        <uses-library android:name="org.apache.http.legacy" android:required="false"/>',
        manifest,
        count=1
    )

# 2. Add exported to receivers with intent-filter
def add_exported(match):
    tag = match.group(0)
    if 'android:exported=' in tag:
        return tag
    if tag.endswith('/>'):
        return tag[:-2].rstrip() + ' android:exported="true"/>'
    elif tag.endswith('>'):
        return tag[:-1].rstrip() + ' android:exported="true">'
    return tag

manifest = re.sub(r'<receiver\b[^>]*>', add_exported, manifest)

# 3. Swap LAUNCHER activity from DownloaderActivity to UnityLauncherActivity
launcher_match = re.search(r'android:name="([^"]*UnityLauncherActivity)"', manifest)
launcher_class = launcher_match.group(1) if launcher_match else "com.unity3d.player.UnityPlayerActivity"

downloader_class = "com.google.android.vending.expansion.downloader_impl.DownloaderActivity"
try:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import extract_metadata
    meta = extract_metadata.load_metadata() or extract_metadata.extract_all()
    if meta.get('unity_launcher_activity'):
        launcher_class = meta['unity_launcher_activity']
    if meta.get('downloader_activity'):
        downloader_class = meta['downloader_activity']
except Exception:
    pass

old_launcher_pattern = r'<activity\s+[^>]*?DownloaderActivity[^>]*?>\s*<intent-filter>\s*<action\s+android:name="android\.intent\.action\.MAIN"\s*/>\s*<category\s+android:name="android\.intent\.category\.LAUNCHER"\s*/>\s*</intent-filter>\s*</activity>'

new_launcher = f'''<activity android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize" android:label="@string/app_name" android:name="{downloader_class}" android:screenOrientation="sensorLandscape" android:exported="true"/>
        <activity android:configChanges="keyboard|keyboardHidden|orientation|screenLayout|screenSize|smallestScreenSize" android:label="@string/app_name" android:launchMode="singleTask" android:name="{launcher_class}" android:screenOrientation="sensorLandscape" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>'''

manifest = re.sub(old_launcher_pattern, new_launcher, manifest)

# 4. Insert uses-sdk into manifest
manifest = re.sub(r'\s+android:maxSdkVersion="[^"]*"', '', manifest)
if '<uses-sdk' not in manifest:
    uses_sdk = '    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="22"/>\n'
    manifest = re.sub(r'(<manifest\b[^>]*>)', r'\1\n' + uses_sdk, manifest, count=1)
else:
    manifest = re.sub(r'android:targetSdkVersion="[^"]*"', 'android:targetSdkVersion="22"', manifest)

with open(manifest_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(manifest)

print('Updated AndroidManifest.xml successfully!')

# 5. Update apktool.yml
yml_path = 'apk_decoded/apktool.yml'
if os.path.exists(yml_path):
    with open(yml_path, 'r', encoding='utf-8') as f:
        yml = f.read()

    yml = re.sub(r'minSdkVersion:\s*\d+', 'minSdkVersion: 21', yml)
    yml = re.sub(r'targetSdkVersion:\s*\d+', 'targetSdkVersion: 22', yml)

    with open(yml_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(yml)

    print('Updated apktool.yml successfully!')
