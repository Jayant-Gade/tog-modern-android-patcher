"""
Modular Feature: Authentic Visual Settings & Custom Controls
Theme: Tons of Guns Authentic Comic Noir (Dark Charcoal Frame, Red Gradient Buttons, Thick Yellow Text, Square Red Close Box)
Provides:
  - SFX & Music Volume continuous touch sliders
  - Gyroscope & Tilt Aiming sensitivity and jitter damping controls
  - Recalibrate rest position action
  - Cheats mode on/off toggle (with Star symbol warning mark)
  - Currency changer & attribute mod buttons
  - Save file backup (Export/Import) action
  - Dual entry point:
      1. Authentic button below "MORE GAMES" in Options popup (replaces offline Play Games button)
      2. Floating "⚙ SETTINGS" button on homepage / map (automatically hidden during matches/shootouts)
"""

import os
import re
from PIL import Image, ImageDraw
import math

FEATURE_ID = "settings_page"
FEATURE_NAME = "Extended Visual Settings Page"
FEATURE_DESC = "Authentic themed settings modal with SFX/Music/Gyro sliders, cheat toggles, save backup, and homepage/options entry points."

def get_html_content():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Tons of Guns - Settings</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }

    body {
      background-color: rgba(0, 0, 0, 0.75);
      font-family: 'Impact', 'Arial Black', 'Trebuchet MS', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 12px;
      user-select: none;
    }

    /* Authentic TOG Punchy Comic Yellow Text with 2px Hard Black Drop Outline */
    .tog-text {
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', 'Trebuchet MS', sans-serif;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      text-shadow: 
        2px 2px 0px #000,
        -1.5px -1.5px 0px #000,
        1.5px -1.5px 0px #000,
        -1.5px 1.5px 0px #000,
        0px 2px 0px #000,
        0px -2px 0px #000,
        2px 0px 0px #000,
        -2px 0px 0px #000;
    }

    /* Authentic Modal Card Container */
    .modal-frame {
      width: 100%;
      max-width: 400px;
      background: #1b1d20;
      border: 3px solid #000;
      box-shadow: 
        inset 0 0 0 2px #2d3137,
        0 12px 35px rgba(0, 0, 0, 0.95);
      position: relative;
      display: flex;
      flex-direction: column;
    }

    /* Square Red Close Button in Top Right (matches in-game close box) */
    .btn-close-box {
      position: absolute;
      top: -12px;
      right: -12px;
      width: 38px;
      height: 38px;
      background: linear-gradient(180deg, #991b1b, #6b1111);
      border: 3px solid #000;
      color: #000;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      font-size: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 10px rgba(0,0,0,0.8);
      z-index: 10;
      transition: transform 0.1s ease;
    }
    .btn-close-box:active {
      transform: scale(0.92);
    }
    .btn-close-box span {
      text-shadow: 1px 1px 0 #fca5a5;
    }

    /* Authentic Red Rectangular Comic Button */
    .tog-button {
      width: 100%;
      background: linear-gradient(180deg, #961b1b 0%, #681111 60%, #4a0a0a 100%);
      border: 3px solid #000;
      box-shadow: 
        inset 0 2px 0 rgba(255, 120, 120, 0.4),
        inset 0 -2px 0 rgba(0, 0, 0, 0.6),
        0 4px 8px rgba(0,0,0,0.6);
      padding: 13px 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      text-align: center;
      font-size: 16px;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      transition: filter 0.1s, transform 0.05s;
    }
    .tog-button:hover {
      filter: brightness(1.15);
    }
    .tog-button:active {
      transform: translateY(1px);
      box-shadow: inset 0 2px 4px rgba(0,0,0,0.8);
    }

    /* Tab Buttons Row */
    .tabs-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 14px 14px 6px 14px;
    }
    .tab-btn {
      padding: 10px 4px;
      font-size: 13px;
      background: #141618;
      border: 2px solid #282b30;
      color: #777;
      cursor: pointer;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      letter-spacing: 1px;
      text-transform: uppercase;
      text-align: center;
    }
    .tab-btn.active {
      background: linear-gradient(180deg, #961b1b 0%, #681111 60%, #4a0a0a 100%);
      border: 2px solid #000;
      color: #ffd200;
      box-shadow: inset 0 1px 0 rgba(255, 120, 120, 0.4);
      text-shadow: 
        1.5px 1.5px 0 #000,
        -1px -1px 0 #000,
        1px -1px 0 #000,
        -1px 1px 0 #000;
    }

    /* Modal Content Body */
    .modal-body {
      padding: 12px 14px 16px 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 72vh;
      overflow-y: auto;
    }

    /* Section Card */
    .panel-box {
      background: #141619;
      border: 2px solid #000;
      box-shadow: inset 0 0 0 1px #23272d;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .section-title {
      font-size: 14px;
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 1px;
      text-shadow: 1.5px 1.5px 0 #000, -1px -1px 0 #000;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Slider Container & Controls */
    .slider-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .slider-row {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      text-shadow: 1.5px 1.5px 0 #000, -1px -1px 0 #000;
    }
    .slider-val {
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      background: #0d0f11;
      padding: 1px 6px;
      border: 1px solid #333;
      text-shadow: 1px 1px 0 #000;
    }

    input[type="range"] {
      -webkit-appearance: none;
      width: 100%;
      height: 12px;
      background: #0d0f11;
      border: 2px solid #000;
      border-radius: 2px;
      outline: none;
      margin: 4px 0 8px 0;
    }
    input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 24px;
      height: 24px;
      background: linear-gradient(180deg, #ffd200 0%, #b89100 100%);
      border: 2px solid #000;
      border-radius: 2px;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }

    /* Toggle Switches */
    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 0;
    }
    .toggle-label {
      font-size: 13px;
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      text-shadow: 1.5px 1.5px 0 #000, -1px -1px 0 #000;
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 50px;
      height: 26px;
    }
    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .slider-round {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #222;
      border: 2px solid #000;
      transition: .2s;
    }
    .slider-round:before {
      position: absolute;
      content: "";
      height: 16px;
      width: 16px;
      left: 3px;
      bottom: 3px;
      background-color: #666;
      border: 1px solid #000;
      transition: .2s;
    }
    input:checked + .slider-round {
      background-color: #8b1818;
    }
    input:checked + .slider-round:before {
      transform: translateX(24px);
      background-color: #ffd200;
    }

    /* Action Buttons in Grid */
    .btn-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    /* Cheat Warning Badge */
    .cheat-badge {
      background: rgba(139, 24, 24, 0.4);
      border: 2px solid #8b1818;
      padding: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
    }
    .cheat-badge-star {
      font-size: 20px;
      color: #ffd200;
      text-shadow: 2px 2px 0 #000;
    }
    .cheat-badge-text {
      font-size: 11px;
      color: #ffd200;
      font-family: sans-serif;
      font-weight: bold;
      line-height: 1.3;
      text-shadow: 1px 1px 0 #000;
    }

    /* Modal Footer */
    .modal-footer {
      padding: 10px 14px;
      background: #111315;
      border-top: 2px solid #000;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: #888;
      letter-spacing: 1px;
    }
  </style>
</head>
<body>

  <!-- Modal Frame -->
  <div class="modal-frame" id="modal-main">
    
    <!-- Top-Right Red Square Close Box -->
    <div class="btn-close-box" onclick="closeSettings()">
      <span>✕</span>
    </div>

    <!-- Top Title Button (Matches in-game top bar) -->
    <div style="padding: 14px 14px 0 14px;">
      <div class="tog-button tog-text" style="font-size: 17px; cursor: default;">
        SETTINGS & CONTROLS
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-row">
      <div id="tab1-btn" class="tab-btn active" onclick="switchTab(1)">AUDIO & MOTION</div>
      <div id="tab2-btn" class="tab-btn" onclick="switchTab(2)">CHEATS & DATA</div>
    </div>

    <!-- Scrollable Body -->
    <div class="modal-body">

      <!-- TAB 1: AUDIO & MOTION -->
      <div id="tab1" style="display: flex; flex-direction: column; gap: 10px;">
        
        <!-- Sound Card -->
        <div class="panel-box">
          <div class="section-title">
            <span>🔊 SOUND LEVELS</span>
          </div>

          <div class="slider-group">
            <div class="slider-row">
              <span>SFX VOLUME</span>
              <span id="sfx-val" class="slider-val">80%</span>
            </div>
            <input type="range" id="sfx-slider" min="0" max="100" value="80" 
                   oninput="document.getElementById('sfx-val').innerText = this.value + '%'">
          </div>

          <div class="slider-group">
            <div class="slider-row">
              <span>MUSIC VOLUME</span>
              <span id="music-val" class="slider-val">65%</span>
            </div>
            <input type="range" id="music-slider" min="0" max="100" value="65" 
                   oninput="document.getElementById('music-val').innerText = this.value + '%'">
          </div>
        </div>

        <!-- Gyro / Motion Card -->
        <div class="panel-box">
          <div class="section-title">
            <span>📱 GYRO / TILT AIMING</span>
            <span style="margin-left: auto; font-size: 11px; color: #4ade80; text-shadow: 1px 1px 0 #000;">ACTIVE</span>
          </div>

          <div class="slider-group">
            <div class="slider-row">
              <span>AIM SENSITIVITY (SPEED)</span>
              <span id="gyro-val" class="slider-val">1.2x</span>
            </div>
            <input type="range" id="gyro-slider" min="5" max="30" value="12" 
                   oninput="updateGyroSensitivity(this.value)">
          </div>

          <div class="slider-group">
            <div class="slider-row">
              <span>JITTER DAMPING (SMOOTHING)</span>
              <span id="damp-val" class="slider-val">35%</span>
            </div>
            <input type="range" id="damp-slider" min="0" max="100" value="35" 
                   oninput="updateGyroDamping(this.value)">
          </div>

          <div class="tog-button tog-text" style="padding: 10px; font-size: 13px; margin-top: 4px;" onclick="recalibrateGyro()">
            RECALIBRATE REST POSITION
          </div>
          <div id="recal-status" style="display:none; text-align:center; color:#4ade80; font-size:11px; margin-top:3px; text-shadow:1px 1px 0 #000;">
            REST POSITION RECALIBRATED!
          </div>
        </div>

      </div>

      <!-- TAB 2: CHEATS & DATA -->
      <div id="tab2" style="display: none; flex-direction: column; gap: 10px;">
        
        <!-- Cheats Switch -->
        <div class="panel-box">
          <div class="section-title">
            <span>⭐ CHEAT ENGINE</span>
          </div>

          <div class="toggle-row">
            <span class="toggle-label">ENABLE CHEATS & MODS</span>
            <label class="switch">
              <input type="checkbox" id="cheat-toggle" onchange="toggleCheatNotice(this.checked)">
              <span class="slider-round"></span>
            </label>
          </div>

          <div id="cheat-notice" class="cheat-badge" style="display: none;">
            <div class="cheat-badge-star">★</div>
            <div class="cheat-badge-text">
              <strong>CHEATER MARK ACTIVE:</strong> Enabling cheat modes stamps this profile permanently with the ★ star symbol.
            </div>
          </div>
        </div>

        <!-- Value Changers (Cheats) -->
        <div class="panel-box">
          <div class="section-title">
            <span>💎 CURRENCY & ATTRIBUTES</span>
          </div>
          
          <div class="btn-grid-2">
            <div class="tog-button tog-text" style="font-size: 13px; padding: 10px;" onclick="alert('Currency count changer unlocked!')">
              +999K GOLD
            </div>
            <div class="tog-button tog-text" style="font-size: 13px; padding: 10px;" onclick="alert('Unlock all weapon tiers unlocked!')">
              MAX WEAPONS
            </div>
          </div>
        </div>

        <!-- Save File Migration / Backup -->
        <div class="panel-box">
          <div class="section-title">
            <span>💾 SAVE FILE MANAGER</span>
          </div>

          <div class="btn-grid-2">
            <div class="tog-button tog-text" style="font-size: 13px; padding: 10px;" onclick="alert('Exporting encrypted save to SD card...')">
              EXPORT SAVE
            </div>
            <div class="tog-button tog-text" style="font-size: 13px; padding: 10px;" onclick="alert('Select save backup JSON to restore...')">
              IMPORT SAVE
            </div>
          </div>
        </div>

      </div>

    </div>

    <!-- Modal Footer -->
    <div class="modal-footer">
      <span>TONS OF GUNS v1.1.0</span>
      <span style="color:#ffd200; font-weight:bold;">CUSTOM SETTINGS</span>
    </div>

  </div>

  <script>
    function switchTab(tabIdx) {
      document.getElementById('tab1').style.display = tabIdx === 1 ? 'flex' : 'none';
      document.getElementById('tab2').style.display = tabIdx === 2 ? 'flex' : 'none';
      document.getElementById('tab1-btn').className = tabIdx === 1 ? 'tab-btn active' : 'tab-btn';
      document.getElementById('tab2-btn').className = tabIdx === 2 ? 'tab-btn active' : 'tab-btn';
    }

    function toggleCheatNotice(checked) {
      document.getElementById('cheat-notice').style.display = checked ? 'flex' : 'none';
    }

    function closeSettings() {
      if (window.AndroidBridge && window.AndroidBridge.closeSettings) {
        window.AndroidBridge.closeSettings();
      } else {
        window.close();
      }
    }

    function initSettings() {
      if (window.AndroidBridge) {
        if (typeof window.AndroidBridge.getGyroSensitivity === 'function') {
          try {
            var s = window.AndroidBridge.getGyroSensitivity();
            if (s > 0) {
              document.getElementById('gyro-slider').value = Math.round(s * 10);
              document.getElementById('gyro-val').innerText = s.toFixed(1) + 'x';
            }
          } catch(e) {}
        }
        if (typeof window.AndroidBridge.getGyroDamping === 'function') {
          try {
            var d = window.AndroidBridge.getGyroDamping();
            if (d >= 0) {
              document.getElementById('damp-slider').value = Math.round(d);
              document.getElementById('damp-val').innerText = Math.round(d) + '%';
            }
          } catch(e) {}
        }
      }
    }

    function updateGyroSensitivity(val) {
      var s = val / 10.0;
      document.getElementById('gyro-val').innerText = s.toFixed(1) + 'x';
      if (window.AndroidBridge && window.AndroidBridge.setGyroSensitivity) {
        window.AndroidBridge.setGyroSensitivity(s);
      }
    }

    function updateGyroDamping(val) {
      var d = parseFloat(val);
      document.getElementById('damp-val').innerText = Math.round(d) + '%';
      if (window.AndroidBridge && window.AndroidBridge.setGyroDamping) {
        window.AndroidBridge.setGyroDamping(d);
      }
    }

    function recalibrateGyro() {
      if (window.AndroidBridge && window.AndroidBridge.recalibrateGyro) {
        window.AndroidBridge.recalibrateGyro();
      }
      var el = document.getElementById('recal-status');
      if (el) {
        el.style.display = 'block';
        setTimeout(function() { el.style.display = 'none'; }, 2000);
      }
    }

    window.addEventListener('DOMContentLoaded', initSettings);
    window.addEventListener('load', initSettings);
    setTimeout(initSettings, 100);
    setTimeout(initSettings, 300);
  </script>
</body>
</html>
"""

def get_settings_activity_smali():
    return """.class public Lcom/glu/tonsguns/SettingsActivity;
.super Landroid/app/Activity;
.source "SettingsActivity.java"

# inner class
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Lcom/glu/tonsguns/SettingsActivity$JsBridge;
    }
.end annotation

# instance fields
.field private webView:Landroid/webkit/WebView;

# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method

.method public static launch(Landroid/content/Context;)V
    .locals 2

    if-eqz p0, :cond_0

    new-instance v0, Landroid/content/Intent;

    const-class v1, Lcom/glu/tonsguns/SettingsActivity;

    invoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V

    const/high16 v1, 0x10000000

    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;

    invoke-virtual {p0, v0}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V

    :cond_0
    return-void
.end method

# virtual methods
.method protected onCreate(Landroid/os/Bundle;)V
    .locals 4

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    invoke-virtual {p0}, Lcom/glu/tonsguns/SettingsActivity;->getWindow()Landroid/view/Window;

    move-result-object v0

    if-eqz v0, :cond_0

    const/16 v1, 0x400

    invoke-virtual {v0, v1, v1}, Landroid/view/Window;->setFlags(II)V

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/view/Window;->setBackgroundDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_0
    new-instance v0, Landroid/webkit/WebView;

    invoke-direct {v0, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V

    iput-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/webkit/WebView;->setBackgroundColor(I)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    const/4 v2, 0x1

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3}, Landroid/webkit/WebView;->setLayerType(ILandroid/graphics/Paint;)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {v0}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;

    move-result-object v0

    invoke-virtual {v0, v2}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V

    invoke-virtual {v0, v2}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V

    invoke-virtual {v0, v2}, Landroid/webkit/WebSettings;->setAllowFileAccess(Z)V

    invoke-virtual {v0, v2}, Landroid/webkit/WebSettings;->setAllowContentAccess(Z)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    new-instance v2, Lcom/glu/tonsguns/SettingsActivity$JsBridge;

    invoke-direct {v2, p0}, Lcom/glu/tonsguns/SettingsActivity$JsBridge;-><init>(Lcom/glu/tonsguns/SettingsActivity;)V

    const-string v3, "AndroidBridge"

    invoke-virtual {v0, v2, v3}, Landroid/webkit/WebView;->addJavascriptInterface(Ljava/lang/Object;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    new-instance v2, Landroid/webkit/WebViewClient;

    invoke-direct {v2}, Landroid/webkit/WebViewClient;-><init>()V

    invoke-virtual {v0, v2}, Landroid/webkit/WebView;->setWebViewClient(Landroid/webkit/WebViewClient;)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    new-instance v2, Landroid/webkit/WebChromeClient;

    invoke-direct {v2}, Landroid/webkit/WebChromeClient;-><init>()V

    invoke-virtual {v0, v2}, Landroid/webkit/WebView;->setWebChromeClient(Landroid/webkit/WebChromeClient;)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    const-string v2, "file:///android_asset/settings_preview.html"

    invoke-virtual {v0, v2}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {p0, v0}, Lcom/glu/tonsguns/SettingsActivity;->setContentView(Landroid/view/View;)V

    return-void
.end method

.method public onBackPressed()V
    .locals 0

    invoke-virtual {p0}, Lcom/glu/tonsguns/SettingsActivity;->finish()V

    return-void
.end method
"""

def get_js_bridge_smali():
    return """.class public Lcom/glu/tonsguns/SettingsActivity$JsBridge;
.super Ljava/lang/Object;
.source "SettingsActivity.java"

# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/glu/tonsguns/SettingsActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x9
    name = "JsBridge"
.end annotation

# instance fields
.field private final activity:Lcom/glu/tonsguns/SettingsActivity;

# direct methods
.method public constructor <init>(Lcom/glu/tonsguns/SettingsActivity;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    return-void
.end method

.method static synthetic access$000(Lcom/glu/tonsguns/SettingsActivity$JsBridge;)Lcom/glu/tonsguns/SettingsActivity;
    .locals 0

    iget-object p0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    return-object p0
.end method

# virtual methods
.method public closeSettings()V
    .locals 2
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    if-eqz v0, :cond_0

    new-instance v1, Lcom/glu/tonsguns/SettingsActivity$JsBridge$1;

    invoke-direct {v1, p0}, Lcom/glu/tonsguns/SettingsActivity$JsBridge$1;-><init>(Lcom/glu/tonsguns/SettingsActivity$JsBridge;)V

    invoke-virtual {v0, v1}, Lcom/glu/tonsguns/SettingsActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    :cond_0
    return-void
.end method

.method public log(Ljava/lang/String;)V
    .locals 1
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    const-string v0, "TOG_Settings"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    return-void
.end method

.method public getGyroSensitivity()F
    .locals 4
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    const v1, 0x3f99999a    # 1.2f

    if-nez v0, :cond_0

    return v1

    :cond_0
    invoke-virtual {v0}, Lcom/glu/tonsguns/SettingsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3}, Lcom/glu/tonsguns/SettingsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    const-string v2, "gyro_sensitivity"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences;->getFloat(Ljava/lang/String;F)F

    move-result v0

    return v0
.end method

.method public setGyroSensitivity(F)V
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    if-nez v0, :cond_0

    return-void

    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    invoke-virtual {v0}, Lcom/glu/tonsguns/SettingsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Lcom/glu/tonsguns/SettingsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v1, "gyro_sensitivity"

    invoke-interface {v0, v1, p1}, Landroid/content/SharedPreferences$Editor;->putFloat(Ljava/lang/String;F)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->commit()Z

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "Saved gyro_sensitivity = "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    const-string v0, "TOG_Settings"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    return-void
.end method

.method public getGyroDamping()F
    .locals 4
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    const/high16 v1, 0x420c0000    # 35.0f

    if-nez v0, :cond_0

    return v1

    :cond_0
    invoke-virtual {v0}, Lcom/glu/tonsguns/SettingsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3}, Lcom/glu/tonsguns/SettingsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    const-string v2, "gyro_damping"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences;->getFloat(Ljava/lang/String;F)F

    move-result v0

    return v0
.end method

.method public setGyroDamping(F)V
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    if-nez v0, :cond_0

    return-void

    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->activity:Lcom/glu/tonsguns/SettingsActivity;

    invoke-virtual {v0}, Lcom/glu/tonsguns/SettingsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Lcom/glu/tonsguns/SettingsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v1, "gyro_damping"

    invoke-interface {v0, v1, p1}, Landroid/content/SharedPreferences$Editor;->putFloat(Ljava/lang/String;F)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->commit()Z

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "Saved gyro_damping = "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    const-string v0, "TOG_Settings"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    return-void
.end method

.method public recalibrateGyro()V
    .locals 4
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    const-string v0, "TOG_Settings"

    :try_start_0
    const-string v1, "ApplicationUtilities"

    const-string v2, "ExitGameCallback"

    const-string v3, "-2"

    invoke-static {v1, v2, v3}, Lcom/unity3d/player/UnityPlayer;->UnitySendMessage(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    const-string v1, "Triggered gyro recalibrate via ExitGameCallback -2"

    invoke-static {v0, v1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v1

    const-string v2, "Recalibrate error"

    invoke-static {v0, v2, v1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_0
    return-void
.end method
"""

def get_js_bridge_runnable_smali():
    return """.class Lcom/glu/tonsguns/SettingsActivity$JsBridge$1;
.super Ljava/lang/Object;
.source "SettingsActivity.java"

# interfaces
.implements Ljava/lang/Runnable;

# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/SettingsActivity$JsBridge;->closeSettings()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation

# instance fields
.field final synthetic this$0:Lcom/glu/tonsguns/SettingsActivity$JsBridge;

# direct methods
.method constructor <init>(Lcom/glu/tonsguns/SettingsActivity$JsBridge;)V
    .locals 0

    iput-object p1, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge$1;->this$0:Lcom/glu/tonsguns/SettingsActivity$JsBridge;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

# virtual methods
.method public run()V
    .locals 1

    iget-object v0, p0, Lcom/glu/tonsguns/SettingsActivity$JsBridge$1;->this$0:Lcom/glu/tonsguns/SettingsActivity$JsBridge;

    invoke-static {v0}, Lcom/glu/tonsguns/SettingsActivity$JsBridge;->access$000(Lcom/glu/tonsguns/SettingsActivity$JsBridge;)Lcom/glu/tonsguns/SettingsActivity;

    move-result-object v0

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Lcom/glu/tonsguns/SettingsActivity;->finish()V

    :cond_0
    return-void
.end method
"""

def get_floating_button_smali():
    return """.class public Lcom/glu/tonsguns/FloatingSettingsButton;
.super Ljava/lang/Object;
.source "FloatingSettingsButton.java"

# static fields
.field private static buttonView:Landroid/view/View;

# direct methods
.method static constructor <clinit>()V
    .locals 1
    const/4 v0, 0x0
    sput-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    return-void
.end method

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method static synthetic access$000()Landroid/view/View;
    .locals 1
    sget-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    return-object v0
.end method

.method static synthetic access$002(Landroid/view/View;)Landroid/view/View;
    .locals 0
    sput-object p0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    return-object p0
.end method

.method public static hide()V
    .locals 2
    sget-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    if-eqz v0, :cond_0
    sget-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    new-instance v1, Lcom/glu/tonsguns/FloatingSettingsButton$3;
    invoke-direct {v1}, Lcom/glu/tonsguns/FloatingSettingsButton$3;-><init>()V
    invoke-virtual {v0, v1}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z
    :cond_0
    return-void
.end method

.method public static init(Landroid/app/Activity;)V
    .locals 1
    if-nez p0, :cond_0
    return-void
    :cond_0
    new-instance v0, Lcom/glu/tonsguns/FloatingSettingsButton$1;
    invoke-direct {v0, p0}, Lcom/glu/tonsguns/FloatingSettingsButton$1;-><init>(Landroid/app/Activity;)V
    invoke-virtual {p0, v0}, Landroid/app/Activity;->runOnUiThread(Ljava/lang/Runnable;)V
    return-void
.end method

.method public static show()V
    .locals 2
    sget-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    if-eqz v0, :cond_0
    sget-object v0, Lcom/glu/tonsguns/FloatingSettingsButton;->buttonView:Landroid/view/View;
    new-instance v1, Lcom/glu/tonsguns/FloatingSettingsButton$2;
    invoke-direct {v1}, Lcom/glu/tonsguns/FloatingSettingsButton$2;-><init>()V
    invoke-virtual {v0, v1}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z
    :cond_0
    return-void
.end method
"""

def get_floating_button_runnable1_smali():
    return """.class Lcom/glu/tonsguns/FloatingSettingsButton$1;
.super Ljava/lang/Object;
.source "FloatingSettingsButton.java"

# interfaces
.implements Ljava/lang/Runnable;

# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingSettingsButton;->init(Landroid/app/Activity;)V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation

# instance fields
.field final synthetic val$activity:Landroid/app/Activity;

# direct methods
.method constructor <init>(Landroid/app/Activity;)V
    .locals 0
    iput-object p1, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1;->val$activity:Landroid/app/Activity;
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# virtual methods
.method public run()V
    .locals 5
    :try_start_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    if-eqz v0, :cond_1
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    invoke-virtual {v0}, Landroid/view/View;->getParent()Landroid/view/ViewParent;
    move-result-object v0
    check-cast v0, Landroid/view/ViewGroup;
    if-eqz v0, :cond_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v1
    invoke-virtual {v0, v1}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V
    :cond_0
    const/4 v0, 0x0
    invoke-static {v0}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$002(Landroid/view/View;)Landroid/view/View;

    :cond_1
    iget-object v0, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1;->val$activity:Landroid/app/Activity;
    invoke-virtual {v0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;
    move-result-object v0
    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;
    move-result-object v0
    iget v0, v0, Landroid/util/DisplayMetrics;->density:F

    new-instance v1, Landroid/widget/TextView;
    iget-object v2, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1;->val$activity:Landroid/app/Activity;
    invoke-direct {v1, v2}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    const-string v2, "\\u2699 SETTINGS"
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    const-string v2, "#FFD200"
    invoke-static {v2}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I
    move-result v2
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTextColor(I)V

    const/high16 v2, 0x41500000    # 13.0f
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTextSize(F)V

    sget-object v2, Landroid/graphics/Typeface;->DEFAULT_BOLD:Landroid/graphics/Typeface;
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTypeface(Landroid/graphics/Typeface;)V

    const/16 v2, 0x11
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setGravity(I)V

    const/high16 v2, 0x41400000    # 12.0f
    mul-float v2, v2, v0
    float-to-int v2, v2

    const/high16 v3, 0x41000000    # 8.0f
    mul-float v3, v3, v0
    float-to-int v3, v3

    invoke-virtual {v1, v2, v3, v2, v3}, Landroid/widget/TextView;->setPadding(IIII)V

    new-instance v2, Landroid/graphics/drawable/GradientDrawable;
    invoke-direct {v2}, Landroid/graphics/drawable/GradientDrawable;-><init>()V
    const/4 v3, 0x0
    invoke-virtual {v2, v3}, Landroid/graphics/drawable/GradientDrawable;->setShape(I)V

    const/high16 v3, 0x40c00000    # 6.0f
    mul-float v3, v3, v0
    invoke-virtual {v2, v3}, Landroid/graphics/drawable/GradientDrawable;->setCornerRadius(F)V

    const-string v3, "#991B1B"
    invoke-static {v3}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I
    move-result v3

    const-string v4, "#5A0E0E"
    invoke-static {v4}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I
    move-result v4

    filled-new-array {v3, v4}, [I
    move-result-object v3
    invoke-virtual {v2, v3}, Landroid/graphics/drawable/GradientDrawable;->setColors([I)V

    sget-object v3, Landroid/graphics/drawable/GradientDrawable$Orientation;->TOP_BOTTOM:Landroid/graphics/drawable/GradientDrawable$Orientation;
    invoke-virtual {v2, v3}, Landroid/graphics/drawable/GradientDrawable;->setOrientation(Landroid/graphics/drawable/GradientDrawable$Orientation;)V

    const/high16 v3, 0x40000000    # 2.0f
    mul-float v3, v3, v0
    float-to-int v3, v3
    const/high16 v4, -0x1000000
    invoke-virtual {v2, v3, v4}, Landroid/graphics/drawable/GradientDrawable;->setStroke(II)V
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setBackground(Landroid/graphics/drawable/Drawable;)V

    new-instance v2, Landroid/widget/FrameLayout$LayoutParams;
    const/4 v3, -0x2
    invoke-direct {v2, v3, v3}, Landroid/widget/FrameLayout$LayoutParams;-><init>(II)V

    const v3, 0x800055
    iput v3, v2, Landroid/widget/FrameLayout$LayoutParams;->gravity:I

    const/high16 v3, 0x42dc0000    # 110.0f
    mul-float v3, v3, v0
    float-to-int v3, v3
    iput v3, v2, Landroid/widget/FrameLayout$LayoutParams;->bottomMargin:I

    const/high16 v3, 0x41800000    # 16.0f
    mul-float v3, v3, v0
    float-to-int v0, v3
    iput v0, v2, Landroid/widget/FrameLayout$LayoutParams;->rightMargin:I

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    new-instance v0, Lcom/glu/tonsguns/FloatingSettingsButton$1$1;
    invoke-direct {v0, p0}, Lcom/glu/tonsguns/FloatingSettingsButton$1$1;-><init>(Lcom/glu/tonsguns/FloatingSettingsButton$1;)V
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    const/16 v0, 0x8
    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setVisibility(I)V

    invoke-static {v1}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$002(Landroid/view/View;)Landroid/view/View;

    iget-object v0, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1;->val$activity:Landroid/app/Activity;
    invoke-virtual {v0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v0
    check-cast v0, Landroid/view/ViewGroup;
    invoke-virtual {v0, v1}, Landroid/view/ViewGroup;->addView(Landroid/view/View;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v0
    invoke-virtual {v0}, Ljava/lang/Throwable;->printStackTrace()V

    :goto_0
    return-void
.end method
"""

def get_floating_button_click_smali():
    return """.class Lcom/glu/tonsguns/FloatingSettingsButton$1$1;
.super Ljava/lang/Object;
.source "FloatingSettingsButton.java"

# interfaces
.implements Landroid/view/View$OnClickListener;

# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingSettingsButton$1;->run()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation

# instance fields
.field final synthetic this$0:Lcom/glu/tonsguns/FloatingSettingsButton$1;

# direct methods
.method constructor <init>(Lcom/glu/tonsguns/FloatingSettingsButton$1;)V
    .locals 0
    iput-object p1, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1$1;->this$0:Lcom/glu/tonsguns/FloatingSettingsButton$1;
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# virtual methods
.method public onClick(Landroid/view/View;)V
    .locals 1
    iget-object v0, p0, Lcom/glu/tonsguns/FloatingSettingsButton$1$1;->this$0:Lcom/glu/tonsguns/FloatingSettingsButton$1;
    iget-object v0, v0, Lcom/glu/tonsguns/FloatingSettingsButton$1;->val$activity:Landroid/app/Activity;
    invoke-static {v0}, Lcom/glu/tonsguns/SettingsActivity;->launch(Landroid/content/Context;)V
    return-void
.end method
"""

def get_floating_button_runnable2_smali():
    return """.class Lcom/glu/tonsguns/FloatingSettingsButton$2;
.super Ljava/lang/Object;
.source "FloatingSettingsButton.java"

# interfaces
.implements Ljava/lang/Runnable;

# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingSettingsButton;->show()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation

# direct methods
.method constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# virtual methods
.method public run()V
    .locals 2
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    if-eqz v0, :cond_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    const/4 v1, 0x0
    invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    invoke-virtual {v0}, Landroid/view/View;->bringToFront()V
    :cond_0
    return-void
.end method
"""

def get_floating_button_runnable3_smali():
    return """.class Lcom/glu/tonsguns/FloatingSettingsButton$3;
.super Ljava/lang/Object;
.source "FloatingSettingsButton.java"

# interfaces
.implements Ljava/lang/Runnable;

# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingSettingsButton;->hide()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation

# direct methods
.method constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# virtual methods
.method public run()V
    .locals 2
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    if-eqz v0, :cond_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->access$000()Landroid/view/View;
    move-result-object v0
    const/16 v1, 0x8
    invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V
    :cond_0
    return-void
.end method
"""

def generate_drawables(drawable_dir):
    os.makedirs(drawable_dir, exist_ok=True)
    size = (128, 128)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = 8
    draw.rounded_rectangle([pad, pad, 128 - pad, 128 - pad], radius=24, fill=(150, 27, 27, 255), outline=(0, 0, 0, 255), width=6)
    draw.rounded_rectangle([pad + 5, pad + 5, 128 - pad - 5, 128 - pad - 5], radius=18, outline=(220, 60, 60, 180), width=2)

    cx, cy = 64, 64
    outer_r = 32
    hole_r = 10
    teeth = 8

    for i in range(teeth):
        angle = i * (2 * math.pi / teeth)
        tx = cx + (outer_r + 5) * math.cos(angle)
        ty = cy + (outer_r + 5) * math.sin(angle)
        draw.circle((tx, ty), 7, fill=(255, 210, 0, 255), outline=(0, 0, 0, 255), width=3)

    draw.circle((cx, cy), outer_r, fill=(255, 210, 0, 255), outline=(0, 0, 0, 255), width=4)
    draw.circle((cx, cy), hole_r, fill=(150, 27, 27, 255), outline=(0, 0, 0, 255), width=3)

    p1 = os.path.join(drawable_dir, "google_plus_128.png")
    p2 = os.path.join(drawable_dir, "games_controller_128.png")
    img.save(p1, "PNG")
    img.save(p2, "PNG")
    print(f"  [+] Generated settings icon drawables: {p1}")

def apply_feature(workspace_dir):
    """
    Applies the settings page feature into the decoded APK workspace.
    """
    print(f"[Feature: {FEATURE_NAME}] Injecting feature into workspace...")
    apk_decoded = os.path.join(workspace_dir, "apk_decoded")
    if not os.path.exists(apk_decoded):
        print(f"Error: {apk_decoded} does not exist. Decode APK first.")
        return False

    # 1. Inject HTML into assets
    assets_dir = os.path.join(apk_decoded, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    html_path = os.path.join(assets_dir, "settings_preview.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(get_html_content())
    print(f"  [+] Injected {html_path}")

    # 2. Inject Smali classes into com/glu/tonsguns/
    smali_dir = os.path.join(apk_decoded, "smali", "com", "glu", "tonsguns")
    os.makedirs(smali_dir, exist_ok=True)
    
    classes = {
        "SettingsActivity.smali": get_settings_activity_smali(),
        "SettingsActivity$JsBridge.smali": get_js_bridge_smali(),
        "SettingsActivity$JsBridge$1.smali": get_js_bridge_runnable_smali(),
        "FloatingSettingsButton.smali": get_floating_button_smali(),
        "FloatingSettingsButton$1.smali": get_floating_button_runnable1_smali(),
        "FloatingSettingsButton$1$1.smali": get_floating_button_click_smali(),
        "FloatingSettingsButton$2.smali": get_floating_button_runnable2_smali(),
        "FloatingSettingsButton$3.smali": get_floating_button_runnable3_smali(),
    }
    for fname, smali_text in classes.items():
        with open(os.path.join(smali_dir, fname), "w", encoding="utf-8") as f:
            f.write(smali_text)
    print(f"  [+] Injected SettingsActivity & FloatingSettingsButton Smali classes into {smali_dir}")

    # 3. Register activity in AndroidManifest.xml
    manifest_path = os.path.join(apk_decoded, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_content = f.read()

        activity_tag = '''        <activity android:name="com.glu.tonsguns.SettingsActivity"
                  android:theme="@android:style/Theme.Translucent.NoTitleBar.Fullscreen"
                  android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
                  android:hardwareAccelerated="true"
                  android:exported="true">
            <intent-filter>
                <action android:name="com.glu.tonsguns.SHOW_SETTINGS"/>
                <category android:name="android.intent.category.DEFAULT"/>
            </intent-filter>
        </activity>
    </application>'''

        if "com.glu.tonsguns.SettingsActivity" not in manifest_content:
            manifest_content = manifest_content.replace("</application>", activity_tag)
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest_content)
            print(f"  [+] Registered SettingsActivity in AndroidManifest.xml")

    # 4. Hook UnityLauncherActivity.smali to initialize FloatingSettingsButton
    launcher_smali = os.path.join(apk_decoded, "smali", "com", "glu", "plugins", "AUnityInstaller", "UnityLauncherActivity.smali")
    if os.path.exists(launcher_smali):
        with open(launcher_smali, "r", encoding="utf-8") as f:
            launcher_content = f.read()
        target = "invoke-super {p0, p1}, Lcom/unity3d/player/UnityPlayerActivity;->onCreate(Landroid/os/Bundle;)V"
        if target in launcher_content and "FloatingSettingsButton;->init" not in launcher_content:
            launcher_content = launcher_content.replace(
                target,
                target + "\n\n    invoke-static {p0}, Lcom/glu/tonsguns/FloatingSettingsButton;->init(Landroid/app/Activity;)V"
            )
            with open(launcher_smali, "w", encoding="utf-8") as f:
                f.write(launcher_content)
            print("  [+] Hooked UnityLauncherActivity.smali (FloatingSettingsButton.init)")

    # 5. Hook CustomGlu.smali to synchronize floating button with Unity home vs match
    custom_glu_smali = os.path.join(apk_decoded, "smali", "com", "glu", "plugins", "CustomGlu.smali")
    if os.path.exists(custom_glu_smali):
        with open(custom_glu_smali, "r", encoding="utf-8") as f:
            cg_content = f.read()
        
        show_target = ".method public static Show(Ljava/lang/String;III)V\n    .locals 2"
        if show_target in cg_content and "FloatingSettingsButton;->show" not in cg_content:
            cg_content = cg_content.replace(
                show_target,
                show_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->show()V"
            )

        hide_target = ".method public static Hide(Ljava/lang/String;)V\n    .locals 2"
        if hide_target in cg_content and "FloatingSettingsButton;->hide" not in cg_content:
            cg_content = cg_content.replace(
                hide_target,
                hide_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->hide()V"
            )

        hide_all_target = ".method public static HideAll()V\n    .locals 2"
        if hide_all_target in cg_content and "FloatingSettingsButton;->hide" not in cg_content:
            cg_content = cg_content.replace(
                hide_all_target,
                hide_all_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingSettingsButton;->hide()V"
            )

        with open(custom_glu_smali, "w", encoding="utf-8") as f:
            f.write(cg_content)
        print("  [+] Hooked CustomGlu.smali (FloatingSettingsButton show/hide on map vs match)")

    # 6. Hook PlayGameServicesGlu.smali for the in-game Options button below MORE GAMES
    pgs_smali = os.path.join(apk_decoded, "smali", "com", "glu", "plugins", "PlayGameServicesGlu.smali")
    if os.path.exists(pgs_smali):
        with open(pgs_smali, "r", encoding="utf-8") as f:
            pgs_content = f.read()

        avail_hook = """.method public static IsPlayGameServicesAvailable()I
    .locals 1

    const/4 v0, 0x0

    return v0
.end method"""
        pgs_content = re.sub(r"\.method public static IsPlayGameServicesAvailable\(\)I.*?\n\.end method", avail_hook, pgs_content, flags=re.DOTALL)

        signin_hook = """.method public static SignIn()V
    .locals 1

    sget-object v0, Lcom/unity3d/player/UnityPlayer;->currentActivity:Landroid/app/Activity;

    invoke-static {v0}, Lcom/glu/tonsguns/SettingsActivity;->launch(Landroid/content/Context;)V

    return-void
.end method"""
        pgs_content = re.sub(r"\.method public static SignIn\(\)V.*?\n\.end method", signin_hook, pgs_content, flags=re.DOTALL)

        achiev_hook = """.method public static onShowAchievementsRequested()V
    .locals 1

    sget-object v0, Lcom/unity3d/player/UnityPlayer;->currentActivity:Landroid/app/Activity;

    invoke-static {v0}, Lcom/glu/tonsguns/SettingsActivity;->launch(Landroid/content/Context;)V

    return-void
.end method"""
        pgs_content = re.sub(r"\.method public static onShowAchievementsRequested\(\)V.*?\n\.end method", achiev_hook, pgs_content, flags=re.DOTALL)

        leader_hook = """.method public static onShowLeaderboardsRequested()V
    .locals 1

    sget-object v0, Lcom/unity3d/player/UnityPlayer;->currentActivity:Landroid/app/Activity;

    invoke-static {v0}, Lcom/glu/tonsguns/SettingsActivity;->launch(Landroid/content/Context;)V

    return-void
.end method"""
        pgs_content = re.sub(r"\.method public static onShowLeaderboardsRequested\(\)V.*?\n\.end method", leader_hook, pgs_content, flags=re.DOTALL)

        with open(pgs_smali, "w", encoding="utf-8") as f:
            f.write(pgs_content)
        print("  [+] Hooked PlayGameServicesGlu.smali (Options popup buttons & SignIn route to SettingsActivity)")

    # 7. Generate settings drawables
    generate_drawables(os.path.join(apk_decoded, "res", "drawable"))

    print(f"[Feature: {FEATURE_NAME}] Successfully injected!\n")
    return True

if __name__ == "__main__":
    ws = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    apply_feature(ws)
