#!/usr/bin/env python3
"""
feature_manager.py
------------------
Main Custom Feature Selector and Dispatcher (Public Toolchain):
Manages optional non-default features for the game porting pipeline.
Allows the user to interactively choose which new features to integrate,
and triggers each feature's individual module dynamically.
"""

import os
import sys
import argparse
import importlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

REGISTRY = {
    '1': {
        'id': 'settings_page',
        'name': 'Extended Visual Settings Page',
        'description': 'Audio sliders, Gyro sensitivity/damping, Cheat toggle, Save export/import',
        'module': 'features.feature_settings_page',
        'status': 'READY',
    },
    '2': {
        'id': 'cheat_mode',
        'name': 'Cheat Mode & Star (★) Marker',
        'description': 'Persistent cheat toggle with permanent save file star indicator',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
    '3': {
        'id': 'currency_changer',
        'name': 'Currency Count Changer',
        'description': 'In-game cash, gold, and credits modifier (requires cheat mode)',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
    '4': {
        'id': 'custom_attributes',
        'name': 'Custom Attribute Weapons & Armor',
        'description': 'Custom weapon damage, fire rate, ammo capacity, and armor rating',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
    '5': {
        'id': 'event_mode_offline',
        'name': 'Event Mode Offline Support',
        'description': 'Restores daily/seasonal shootout events and local calendar schedule',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
    '6': {
        'id': 'local_multiplayer',
        'name': 'Local Bluetooth/WLAN Multiplayer',
        'description': 'Peer-to-peer multiplayer restricted strictly to Bluetooth/Wi-Fi',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
    '7': {
        'id': 'save_backup',
        'name': 'Save File Backup & Restore',
        'description': 'Local device storage export and import for player progression',
        'module': None,
        'status': 'ROADMAP (Planned)',
    },
}

def display_menu():
    print("=" * 68)
    print("      CUSTOM & NON-DEFAULT FEATURES SELECTION MENU")
    print("=" * 68)
    for key, feat in REGISTRY.items():
        status_tag = f"[{feat['status']}]"
        print(f"  {key}. {feat['name']:<36} {status_tag}")
        print(f"     -> {feat['description']}")
    print("=" * 68)

def execute_feature(feat_key, workspace_dir):
    feat = REGISTRY.get(feat_key)
    if not feat:
        print(f"[-] Invalid feature key: {feat_key}")
        return False
    
    if feat['status'] != 'READY' or not feat['module']:
        print(f"[-] Feature '{feat['name']}' is currently in the {feat['status']} stage and cannot be applied yet.")
        return False

    print(f"\n[+] Executing feature: {feat['name']} ({feat['module']})...")
    sys.path.insert(0, SCRIPT_DIR)
    try:
        mod = importlib.import_module(feat['module'])
        return mod.apply_feature(workspace_dir)
    except Exception as e:
        print(f"[-] Failed to execute feature module {feat['module']}: {e}")
        return False

def interactive_prompt(workspace_dir):
    """Prompts the user interactively during the porting pipeline."""
    print("\n" + "#" * 68)
    print("  NEW FEATURES INTEGRATION STEP")
    print("#" * 68)
    
    try:
        choice = input("Do you want to integrate new/custom features into the app? [y/N]: ").strip().lower()
    except EOFError:
        choice = 'n'

    if choice not in ['y', 'yes']:
        print("[*] Skipping custom features integration. Proceeding with clean port.\n")
        return []

    display_menu()
    
    try:
        selection = input("\nEnter feature numbers to install (e.g., '1', '1,2', or 'all') [default: 1]: ").strip()
    except EOFError:
        selection = '1'

    if not selection:
        selection = '1'

    if selection.lower() == 'q':
        print("[*] Skipped feature selection.\n")
        return []

    applied = []
    if selection.lower() == 'all':
        keys_to_run = list(REGISTRY.keys())
    else:
        keys_to_run = [k.strip() for k in selection.split(',') if k.strip()]

    for k in keys_to_run:
        matched_key = None
        if k in REGISTRY:
            matched_key = k
        else:
            for rk, rfeat in REGISTRY.items():
                if rfeat['id'] == k:
                    matched_key = rk
                    break

        if matched_key:
            if execute_feature(matched_key, workspace_dir):
                applied.append(REGISTRY[matched_key]['id'])
        else:
            print(f"[-] Unknown feature: '{k}'")

    print(f"\n[+] Feature integration finished. Applied: {applied}\n")
    return applied

def main():
    parser = argparse.ArgumentParser(description="Modular Game Feature Manager")
    parser.add_argument('--list', action='store_true', help="List all available and planned features")
    parser.add_argument('--apply', type=str, help="Comma-separated feature IDs or numbers to apply (e.g. 1 or settings_page)")
    parser.add_argument('--all', action='store_true', help="Apply all ready features")
    parser.add_argument('--non-interactive', action='store_true', help="Run without user interaction")
    args = parser.parse_args()

    if args.list:
        display_menu()
        return

    if args.all:
        for k, feat in REGISTRY.items():
            if feat['status'] == 'READY':
                execute_feature(k, WORKSPACE_DIR)
        return

    if args.apply:
        for item in args.apply.split(','):
            item = item.strip()
            for k, feat in REGISTRY.items():
                if k == item or feat['id'] == item:
                    execute_feature(k, WORKSPACE_DIR)
        return

    interactive_prompt(WORKSPACE_DIR)

if __name__ == '__main__':
    main()

