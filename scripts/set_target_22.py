#!/usr/bin/env python3
import sys
import re

target = sys.argv[1] if len(sys.argv) > 1 else '37'

with open('apk_decoded/apktool.yml', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'targetSdkVersion:\s*\d+', f'targetSdkVersion: {target}', text)
with open('apk_decoded/apktool.yml', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

with open('apk_decoded/AndroidManifest.xml', 'r', encoding='utf-8') as f:
    m = f.read()

m = re.sub(r'android:targetSdkVersion="[^"]*"', f'android:targetSdkVersion="{target}"', m)
m = re.sub(r'\s+android:maxSdkVersion="[^"]*"', '', m)
with open('apk_decoded/AndroidManifest.xml', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(m)

print(f'Updated apktool.yml and AndroidManifest.xml targetSdkVersion to {target} (maxSdkVersion removed).')
