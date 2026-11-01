"""
Modular Feature: Cheat System & Custom Weapon Damage
Theme: Tons of Guns Authentic Comic Noir (Dark Charcoal Frame, Red Gradient Buttons, Thick Yellow Text, Square Red Close Box)
Provides:
  - Master Cheats & Mods toggle with Star symbol (★) Cheater Profile mark
  - Custom weapon damage override (Default, 250, 500, 1000, 5000, 99999 One-Hit Kill, and custom input)
  - Floating "★ CHEATS" button on homepage / map positioned immediately to the left of "⚙ SETTINGS" button
  - Auto-hides during active matches/shootouts
  - Injected directly into Unity PlayerGun.EmitProjectile via Mono.Cecil CIL hook
"""

import os
import re

FEATURE_ID = "cheat_system"
FEATURE_NAME = "Cheat System & Custom Gun Damage"
FEATURE_DESC = "Authentic themed cheats modal with master cheat switch, floating Cheats button, Cheater Mark, and custom weapon damage override."

def get_html_content():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Tons of Guns - Cheats</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }

    body {
      background-color: rgba(0, 0, 0, 0.78);
      font-family: 'Impact', 'Arial Black', 'Trebuchet MS', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 12px;
      user-select: none;
    }

    /* Authentic TOG Punchy Comic Yellow Text with 2px Hard Black Outline */
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

    .modal-frame {
      background: #181818;
      border: 4px solid #8b1818;
      box-shadow: 0 0 30px rgba(0, 0, 0, 0.95), inset 0 0 15px rgba(0, 0, 0, 0.85);
      border-radius: 8px;
      width: 100%;
      max-width: 440px;
      position: relative;
      padding: 18px 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    /* Close Button - Authentic Red Square with Black Border */
    .close-btn {
      position: absolute;
      top: -14px;
      right: -14px;
      width: 38px;
      height: 38px;
      background: #8b1818;
      border: 3px solid #000;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 10px rgba(0,0,0,0.7);
      transition: transform 0.1s ease, background 0.1s ease;
      z-index: 10;
    }
    .close-btn:active {
      transform: scale(0.92);
      background: #5a0e0e;
    }
    .close-btn span {
      color: #ffd200;
      font-family: 'Impact', 'Arial Black', sans-serif;
      font-size: 22px;
      line-height: 1;
      text-shadow: 2px 2px 0px #000;
    }

    /* Header */
    .header {
      text-align: center;
      padding-bottom: 4px;
      border-bottom: 2px dashed #444;
    }
    .header-title {
      font-size: 24px;
    }
    .header-sub {
      font-size: 11px;
      color: #ff6b6b;
      letter-spacing: 1px;
      font-weight: bold;
      margin-top: 2px;
    }

    /* Cheat Warning Badge */
    .cheat-badge {
      background: rgba(139, 24, 24, 0.45);
      border: 2px solid #8b1818;
      border-radius: 6px;
      padding: 8px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .cheat-badge-star {
      font-size: 24px;
      color: #ffd200;
      text-shadow: 2px 2px 0px #000;
    }
    .cheat-badge-text {
      font-size: 11px;
      color: #ffd200;
      line-height: 1.35;
      font-family: sans-serif;
      font-weight: bold;
    }

    /* Panels */
    .panel-box {
      background: #222;
      border: 2px solid #333;
      border-radius: 6px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .section-title {
      font-size: 13px;
      color: #ffd200;
      letter-spacing: 1px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Toggle Switch */
    .toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .toggle-label {
      color: #f3f4f6;
      font-size: 13px;
      letter-spacing: 0.8px;
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 48px;
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
      background-color: #3f3f46;
      border: 2px solid #000;
      transition: .2s;
      border-radius: 26px;
    }
    .slider-round:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 2px;
      bottom: 2px;
      background-color: #f3f4f6;
      border: 1px solid #000;
      transition: .2s;
      border-radius: 50%;
    }
    input:checked + .slider-round {
      background-color: #991b1b;
    }
    input:checked + .slider-round:before {
      transform: translateX(22px);
      background-color: #ffd200;
    }

    /* Current Status Box */
    .status-banner {
      background: #111;
      border: 2px solid #444;
      border-radius: 6px;
      padding: 8px 10px;
      text-align: center;
      font-size: 12px;
      color: #bbb;
    }
    .status-banner strong {
      color: #ffd200;
      font-size: 13px;
    }

    /* Preset Buttons Grid */
    .preset-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .preset-btn {
      background: linear-gradient(180deg, #991b1b 0%, #5a0e0e 100%);
      border: 2px solid #000;
      border-radius: 6px;
      padding: 10px 8px;
      font-size: 11px;
      text-align: center;
      cursor: pointer;
      transition: transform 0.1s ease, filter 0.1s ease, border-color 0.1s ease;
      box-shadow: 0 3px 6px rgba(0,0,0,0.6);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
    }
    .preset-btn:active {
      transform: scale(0.96);
      filter: brightness(1.2);
    }
    .preset-btn.active {
      border: 2px solid #ffd200;
      box-shadow: 0 0 10px rgba(255, 210, 0, 0.7);
      background: linear-gradient(180deg, #b91c1c 0%, #7f1d1d 100%);
    }
    .preset-dmg {
      font-size: 13px;
      letter-spacing: 0.5px;
    }
    .preset-desc {
      font-size: 9px;
      color: #ffcccc;
      font-family: sans-serif;
      font-weight: bold;
    }

    /* Custom Input Row */
    .custom-row {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }
    .custom-input {
      flex: 1;
      background: #111;
      border: 2px solid #444;
      border-radius: 6px;
      padding: 8px 10px;
      color: #ffd200;
      font-family: 'Impact', sans-serif;
      font-size: 14px;
      letter-spacing: 1px;
      outline: none;
    }
    .custom-input:focus {
      border-color: #ffd200;
    }
    .custom-apply-btn {
      background: linear-gradient(180deg, #991b1b 0%, #5a0e0e 100%);
      border: 2px solid #000;
      border-radius: 6px;
      padding: 8px 14px;
      cursor: pointer;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 3px 6px rgba(0,0,0,0.6);
    }
    .custom-apply-btn:active {
      transform: scale(0.96);
      filter: brightness(1.2);
    }

    /* Bottom Action Button */
    .action-btn {
      background: linear-gradient(180deg, #991b1b 0%, #5a0e0e 100%);
      border: 3px solid #000;
      border-radius: 6px;
      padding: 12px;
      font-size: 15px;
      cursor: pointer;
      text-align: center;
      box-shadow: 0 4px 8px rgba(0,0,0,0.7);
      transition: transform 0.1s ease;
    }
    .action-btn:active {
      transform: scale(0.97);
    }

    .toast {
      background: #111;
      border: 2px solid #4ade80;
      color: #4ade80;
      font-size: 11px;
      text-align: center;
      padding: 6px;
      border-radius: 4px;
      display: none;
    }
  </style>
</head>
<body>

  <div class="modal-frame">
    <!-- Square Red Close Button -->
    <div class="close-btn" onclick="closeCheats()">
      <span>X</span>
    </div>

    <!-- Header -->
    <div class="header">
      <div class="header-title tog-text">★ CHEAT SYSTEM ★</div>
      <div class="header-sub">CUSTOM WEAPON ATTRIBUTES & MODIFIERS</div>
    </div>

    <!-- Cheater Mark Warning Badge -->
    <div class="cheat-badge">
      <div class="cheat-badge-star">★</div>
      <div class="cheat-badge-text">
        <strong>CHEATER MARK ACTIVE:</strong> Enabling cheat modes stamps this profile permanently with the ★ star symbol.
      </div>
    </div>

    <!-- Master Switch Panel -->
    <div class="panel-box">
      <div class="toggle-row">
        <span class="toggle-label tog-text" style="font-size: 14px;">ENABLE CHEATS & MODS</span>
        <label class="switch">
          <input type="checkbox" id="cheat-toggle" onchange="toggleCheatMode(this.checked)">
          <span class="slider-round"></span>
        </label>
      </div>
    </div>

    <!-- Custom Weapon Damage Panel -->
    <div class="panel-box" id="damage-panel">
      <div class="section-title">
        <span class="tog-text">CUSTOM WEAPON DAMAGE</span>
      </div>
      <div style="font-size: 10px; color: #aaa; font-family: sans-serif;">
        Any gun equipped will deal the specified damage value to all enemies.
      </div>

      <!-- Active Status Banner -->
      <div class="status-banner">
        ACTIVE OVERRIDE: <strong id="active-val">DEFAULT (NORMAL DAMAGE)</strong>
      </div>

      <!-- Preset Buttons Grid -->
      <div class="preset-grid">
        <div class="preset-btn active" id="preset-0" onclick="applyDamage(0)">
          <span class="preset-dmg tog-text">DEFAULT</span>
          <span class="preset-desc">Normal Gun Stats</span>
        </div>
        <div class="preset-btn" id="preset-250" onclick="applyDamage(250)">
          <span class="preset-dmg tog-text">250 DMG</span>
          <span class="preset-desc">Solid Boost</span>
        </div>
        <div class="preset-btn" id="preset-500" onclick="applyDamage(500)">
          <span class="preset-dmg tog-text">500 DMG</span>
          <span class="preset-desc">Heavy Damage</span>
        </div>
        <div class="preset-btn" id="preset-1000" onclick="applyDamage(1000)">
          <span class="preset-dmg tog-text">1,000 DMG</span>
          <span class="preset-desc">Brutal Power</span>
        </div>
        <div class="preset-btn" id="preset-5000" onclick="applyDamage(5000)">
          <span class="preset-dmg tog-text">5,000 DMG</span>
          <span class="preset-desc">Super Blaster</span>
        </div>
        <div class="preset-btn" id="preset-99999" onclick="applyDamage(99999)">
          <span class="preset-dmg tog-text">99,999 DMG</span>
          <span class="preset-desc">ONE-HIT KILL</span>
        </div>
      </div>

      <!-- Custom Input Field -->
      <div class="custom-row">
        <input type="number" id="custom-input" class="custom-input" placeholder="Custom Dmg (e.g. 7500)" min="0" max="9999999">
        <div class="custom-apply-btn tog-text" onclick="applyCustomInput()">APPLY</div>
      </div>

      <div id="toast-msg" class="toast">Damage Override Applied!</div>
    </div>

    <!-- Return Action Button -->
    <div class="action-btn tog-text" onclick="closeCheats()">
      RETURN TO GAME
    </div>
  </div>

  <script>
    var currentDamage = 0;

    function closeCheats() {
      if (window.AndroidBridge && window.AndroidBridge.closeCheats) {
        window.AndroidBridge.closeCheats();
      } else {
        window.close();
      }
    }

    function toggleCheatMode(checked) {
      if (window.AndroidBridge && window.AndroidBridge.setCheatMode) {
        window.AndroidBridge.setCheatMode(checked);
      }
    }

    function showToast(msg) {
      var t = document.getElementById('toast-msg');
      if (t) {
        t.innerText = msg;
        t.style.display = 'block';
        setTimeout(function() { t.style.display = 'none'; }, 2000);
      }
    }

    function updateActiveDisplay(val) {
      currentDamage = val;
      var label = document.getElementById('active-val');
      if (val <= 0) {
        label.innerText = 'DEFAULT (NORMAL DAMAGE)';
        label.style.color = '#4ade80';
      } else if (val >= 99999) {
        label.innerText = '99,999 DMG (ONE-HIT KILL)';
        label.style.color = '#f87171';
      } else {
        label.innerText = Math.round(val).toLocaleString() + ' DAMAGE';
        label.style.color = '#ffd200';
      }

      // Highlight active preset button if match
      var presets = [0, 250, 500, 1000, 5000, 99999];
      for (var i = 0; i < presets.length; i++) {
        var pVal = presets[i];
        var btn = document.getElementById('preset-' + pVal);
        if (btn) {
          if (Math.abs(currentDamage - pVal) < 0.1) {
            btn.className = 'preset-btn active';
          } else {
            btn.className = 'preset-btn';
          }
        }
      }
    }

    function applyDamage(val) {
      updateActiveDisplay(val);
      if (window.AndroidBridge && window.AndroidBridge.setCustomDamage) {
        window.AndroidBridge.setCustomDamage(val);
      }
      showToast(val <= 0 ? 'Damage Reset to Default' : ('Weapon Damage Set to ' + val.toLocaleString()));
    }

    function applyCustomInput() {
      var inp = document.getElementById('custom-input');
      var val = parseFloat(inp.value);
      if (isNaN(val) || val < 0) {
        showToast('Please enter a valid positive number');
        return;
      }
      applyDamage(val);
      inp.value = '';
    }

    function initCheats() {
      if (window.AndroidBridge) {
        if (typeof window.AndroidBridge.getCheatMode === 'function') {
          try {
            var c = window.AndroidBridge.getCheatMode();
            document.getElementById('cheat-toggle').checked = c;
          } catch(e) {}
        }
        if (typeof window.AndroidBridge.getCustomDamage === 'function') {
          try {
            var d = window.AndroidBridge.getCustomDamage();
            updateActiveDisplay(d);
          } catch(e) {}
        }
      }
    }

    window.addEventListener('DOMContentLoaded', initCheats);
    window.addEventListener('load', initCheats);
    setTimeout(initCheats, 100);
    setTimeout(initCheats, 300);
  </script>
</body>
</html>
"""

SMALI_CLASSES = {
    "CheatsActivity.smali": """.class public Lcom/glu/tonsguns/CheatsActivity;
.super Landroid/app/Activity;
.source "CheatsActivity.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Lcom/glu/tonsguns/CheatsActivity$JsBridge;
    }
.end annotation


# instance fields
.field private webView:Landroid/webkit/WebView;


# direct methods
.method public constructor <init>()V
    .locals 0

    .line 17
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method

.method public static launch(Landroid/content/Context;)V
    .locals 2

    .line 21
    if-eqz p0, :cond_0

    .line 22
    new-instance v0, Landroid/content/Intent;

    const-class v1, Lcom/glu/tonsguns/CheatsActivity;

    invoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V

    .line 23
    const/high16 v1, 0x10000000

    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;

    .line 24
    invoke-virtual {p0, v0}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V

    .line 26
    :cond_0
    return-void
.end method


# virtual methods
.method public onBackPressed()V
    .locals 0

    .line 57
    invoke-virtual {p0}, Lcom/glu/tonsguns/CheatsActivity;->finish()V

    .line 58
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 2

    .line 30
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    .line 31
    invoke-virtual {p0}, Lcom/glu/tonsguns/CheatsActivity;->getWindow()Landroid/view/Window;

    move-result-object p1

    .line 32
    const/4 v0, 0x0

    if-eqz p1, :cond_0

    .line 33
    const/16 v1, 0x400

    invoke-virtual {p1, v1, v1}, Landroid/view/Window;->setFlags(II)V

    .line 34
    invoke-virtual {p1, v0}, Landroid/view/Window;->setBackgroundDrawable(Landroid/graphics/drawable/Drawable;)V

    .line 37
    :cond_0
    new-instance p1, Landroid/webkit/WebView;

    invoke-direct {p1, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V

    iput-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    .line 38
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    const/4 v1, 0x0

    invoke-virtual {p1, v1}, Landroid/webkit/WebView;->setBackgroundColor(I)V

    .line 39
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    const/4 v1, 0x1

    invoke-virtual {p1, v1, v0}, Landroid/webkit/WebView;->setLayerType(ILandroid/graphics/Paint;)V

    .line 41
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {p1}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;

    move-result-object p1

    .line 42
    invoke-virtual {p1, v1}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V

    .line 43
    invoke-virtual {p1, v1}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V

    .line 44
    invoke-virtual {p1, v1}, Landroid/webkit/WebSettings;->setAllowFileAccess(Z)V

    .line 45
    invoke-virtual {p1, v1}, Landroid/webkit/WebSettings;->setAllowContentAccess(Z)V

    .line 47
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    new-instance v0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;

    invoke-direct {v0, p0}, Lcom/glu/tonsguns/CheatsActivity$JsBridge;-><init>(Lcom/glu/tonsguns/CheatsActivity;)V

    const-string v1, "AndroidBridge"

    invoke-virtual {p1, v0, v1}, Landroid/webkit/WebView;->addJavascriptInterface(Ljava/lang/Object;Ljava/lang/String;)V

    .line 48
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    new-instance v0, Landroid/webkit/WebViewClient;

    invoke-direct {v0}, Landroid/webkit/WebViewClient;-><init>()V

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->setWebViewClient(Landroid/webkit/WebViewClient;)V

    .line 49
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    new-instance v0, Landroid/webkit/WebChromeClient;

    invoke-direct {v0}, Landroid/webkit/WebChromeClient;-><init>()V

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->setWebChromeClient(Landroid/webkit/WebChromeClient;)V

    .line 50
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    const-string v0, "file:///android_asset/cheats_preview.html"

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    .line 52
    iget-object p1, p0, Lcom/glu/tonsguns/CheatsActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {p0, p1}, Lcom/glu/tonsguns/CheatsActivity;->setContentView(Landroid/view/View;)V

    .line 53
    return-void
.end method
""",
    "CheatsActivity$JsBridge.smali": """.class public Lcom/glu/tonsguns/CheatsActivity$JsBridge;
.super Ljava/lang/Object;
.source "CheatsActivity.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/glu/tonsguns/CheatsActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x9
    name = "JsBridge"
.end annotation


# instance fields
.field private final activity:Lcom/glu/tonsguns/CheatsActivity;


# direct methods
.method static bridge synthetic -$$Nest$fgetactivity(Lcom/glu/tonsguns/CheatsActivity$JsBridge;)Lcom/glu/tonsguns/CheatsActivity;
    .locals 0

    iget-object p0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    return-object p0
.end method

.method public constructor <init>(Lcom/glu/tonsguns/CheatsActivity;)V
    .locals 0

    .line 63
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    .line 64
    iput-object p1, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    .line 65
    return-void
.end method


# virtual methods
.method public closeCheats()V
    .locals 2
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 69
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    if-eqz v0, :cond_0

    .line 70
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    new-instance v1, Lcom/glu/tonsguns/CheatsActivity$JsBridge$1;

    invoke-direct {v1, p0}, Lcom/glu/tonsguns/CheatsActivity$JsBridge$1;-><init>(Lcom/glu/tonsguns/CheatsActivity$JsBridge;)V

    invoke-virtual {v0, v1}, Lcom/glu/tonsguns/CheatsActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 77
    :cond_0
    return-void
.end method

.method public getCheatMode()Z
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 86
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    const/4 v1, 0x0

    if-nez v0, :cond_0

    return v1

    .line 87
    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    iget-object v2, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    invoke-virtual {v2}, Lcom/glu/tonsguns/CheatsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v0, v2, v1}, Lcom/glu/tonsguns/CheatsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 88
    const-string v2, "cheat_mode_enabled"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v0

    return v0
.end method

.method public getCustomDamage()F
    .locals 4
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 102
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    const/4 v1, 0x0

    if-nez v0, :cond_0

    return v1

    .line 103
    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    iget-object v2, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    invoke-virtual {v2}, Lcom/glu/tonsguns/CheatsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3}, Lcom/glu/tonsguns/CheatsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 104
    const-string v2, "cheat_custom_damage"

    invoke-interface {v0, v2, v1}, Landroid/content/SharedPreferences;->getFloat(Ljava/lang/String;F)F

    move-result v0

    return v0
.end method

.method public log(Ljava/lang/String;)V
    .locals 1
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 81
    const-string v0, "TOG_Cheats"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 82
    return-void
.end method

.method public setCheatMode(Z)V
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 93
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    if-nez v0, :cond_0

    return-void

    .line 94
    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    iget-object v1, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    invoke-virtual {v1}, Lcom/glu/tonsguns/CheatsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Lcom/glu/tonsguns/CheatsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 95
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v1, "cheat_mode_enabled"

    invoke-interface {v0, v1, p1}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->commit()Z

    .line 96
    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "Saved cheat_mode_enabled = "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    const-string v0, "TOG_Cheats"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 97
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->updateVisibility()V

    .line 98
    return-void
.end method

.method public setCustomDamage(F)V
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 109
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    if-nez v0, :cond_0

    return-void

    .line 110
    :cond_0
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    iget-object v1, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->activity:Lcom/glu/tonsguns/CheatsActivity;

    invoke-virtual {v1}, Lcom/glu/tonsguns/CheatsActivity;->getPackageName()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Lcom/glu/tonsguns/CheatsActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 111
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v1, "cheat_custom_damage"

    invoke-interface {v0, v1, p1}, Landroid/content/SharedPreferences$Editor;->putFloat(Ljava/lang/String;F)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->commit()Z

    .line 112
    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "Saved cheat_custom_damage = "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    const-string v0, "TOG_Cheats"

    invoke-static {v0, p1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 113
    return-void
.end method
""",
    "CheatsActivity$JsBridge$1.smali": """.class Lcom/glu/tonsguns/CheatsActivity$JsBridge$1;
.super Ljava/lang/Object;
.source "CheatsActivity.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/CheatsActivity$JsBridge;->closeCheats()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic this$0:Lcom/glu/tonsguns/CheatsActivity$JsBridge;


# direct methods
.method constructor <init>(Lcom/glu/tonsguns/CheatsActivity$JsBridge;)V
    .locals 0

    .line 70
    iput-object p1, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge$1;->this$0:Lcom/glu/tonsguns/CheatsActivity$JsBridge;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 1

    .line 73
    iget-object v0, p0, Lcom/glu/tonsguns/CheatsActivity$JsBridge$1;->this$0:Lcom/glu/tonsguns/CheatsActivity$JsBridge;

    invoke-static {v0}, Lcom/glu/tonsguns/CheatsActivity$JsBridge;->-$$Nest$fgetactivity(Lcom/glu/tonsguns/CheatsActivity$JsBridge;)Lcom/glu/tonsguns/CheatsActivity;

    move-result-object v0

    invoke-virtual {v0}, Lcom/glu/tonsguns/CheatsActivity;->finish()V

    .line 74
    return-void
.end method
""",
    "FloatingCheatsButton.smali": """.class public Lcom/glu/tonsguns/FloatingCheatsButton;
.super Ljava/lang/Object;
.source "FloatingCheatsButton.java"


# static fields
.field private static buttonView:Landroid/view/View;


# direct methods
.method static bridge synthetic -$$Nest$sfgetbuttonView()Landroid/view/View;
    .locals 1

    sget-object v0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    return-object v0
.end method

.method static bridge synthetic -$$Nest$sfputbuttonView(Landroid/view/View;)V
    .locals 0

    sput-object p0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    return-void
.end method

.method public constructor <init>()V
    .locals 0

    .line 17
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static hide()V
    .locals 2

    .line 100
    sget-object v0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    if-eqz v0, :cond_0

    .line 101
    sget-object v0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    new-instance v1, Lcom/glu/tonsguns/FloatingCheatsButton$3;

    invoke-direct {v1}, Lcom/glu/tonsguns/FloatingCheatsButton$3;-><init>()V

    invoke-virtual {v0, v1}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z

    .line 108
    :cond_0
    return-void
.end method

.method public static init(Landroid/app/Activity;)V
    .locals 1

    .line 21
    if-nez p0, :cond_0

    return-void

    .line 22
    :cond_0
    new-instance v0, Lcom/glu/tonsguns/FloatingCheatsButton$1;

    invoke-direct {v0, p0}, Lcom/glu/tonsguns/FloatingCheatsButton$1;-><init>(Landroid/app/Activity;)V

    invoke-virtual {p0, v0}, Landroid/app/Activity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 79
    return-void
.end method

.method public static show()V
    .locals 2

    .line 82
    sget-object v0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    if-eqz v0, :cond_0

    .line 83
    sget-object v0, Lcom/glu/tonsguns/FloatingCheatsButton;->buttonView:Landroid/view/View;

    new-instance v1, Lcom/glu/tonsguns/FloatingCheatsButton$2;

    invoke-direct {v1}, Lcom/glu/tonsguns/FloatingCheatsButton$2;-><init>()V

    invoke-virtual {v0, v1}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z

    .line 97
    :cond_0
    return-void
.end method

.method public static updateVisibility()V
    .locals 0

    .line 111
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->show()V

    .line 112
    return-void
.end method
""",
    "FloatingCheatsButton$1.smali": """.class Lcom/glu/tonsguns/FloatingCheatsButton$1;
.super Ljava/lang/Object;
.source "FloatingCheatsButton.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingCheatsButton;->init(Landroid/app/Activity;)V
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
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "()V"
        }
    .end annotation

    .line 22
    iput-object p1, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 6

    .line 26
    :try_start_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v0

    if-eqz v0, :cond_1

    .line 27
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v0

    invoke-virtual {v0}, Landroid/view/View;->getParent()Landroid/view/ViewParent;

    move-result-object v0

    check-cast v0, Landroid/view/ViewGroup;

    .line 28
    if-eqz v0, :cond_0

    .line 29
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/view/ViewGroup;->removeView(Landroid/view/View;)V

    .line 31
    :cond_0
    const/4 v0, 0x0

    invoke-static {v0}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfputbuttonView(Landroid/view/View;)V

    .line 34
    :cond_1
    iget-object v0, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-virtual {v0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v0

    .line 35
    iget v0, v0, Landroid/util/DisplayMetrics;->density:F

    .line 37
    new-instance v1, Landroid/widget/TextView;

    iget-object v2, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-direct {v1, v2}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    .line 38
    const-string v2, "\\u2605 CHEATS"

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    .line 39
    const-string v2, "#FFD200"

    invoke-static {v2}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I

    move-result v2

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTextColor(I)V

    .line 40
    const/high16 v2, 0x41500000    # 13.0f

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTextSize(F)V

    .line 41
    sget-object v2, Landroid/graphics/Typeface;->DEFAULT_BOLD:Landroid/graphics/Typeface;

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setTypeface(Landroid/graphics/Typeface;)V

    .line 42
    const/16 v2, 0x11

    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setGravity(I)V

    .line 43
    const/high16 v2, 0x41400000    # 12.0f

    mul-float v2, v2, v0

    float-to-int v2, v2

    const/high16 v3, 0x41000000    # 8.0f

    mul-float v3, v3, v0

    float-to-int v3, v3

    invoke-virtual {v1, v2, v3, v2, v3}, Landroid/widget/TextView;->setPadding(IIII)V

    .line 45
    new-instance v2, Landroid/graphics/drawable/GradientDrawable;

    invoke-direct {v2}, Landroid/graphics/drawable/GradientDrawable;-><init>()V

    .line 46
    const/4 v3, 0x0

    invoke-virtual {v2, v3}, Landroid/graphics/drawable/GradientDrawable;->setShape(I)V

    .line 47
    const/high16 v4, 0x40c00000    # 6.0f

    mul-float v4, v4, v0

    invoke-virtual {v2, v4}, Landroid/graphics/drawable/GradientDrawable;->setCornerRadius(F)V

    .line 48
    const-string v4, "#991B1B"

    invoke-static {v4}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I

    move-result v4

    const-string v5, "#5A0E0E"

    invoke-static {v5}, Landroid/graphics/Color;->parseColor(Ljava/lang/String;)I

    move-result v5

    filled-new-array {v4, v5}, [I

    move-result-object v4

    invoke-virtual {v2, v4}, Landroid/graphics/drawable/GradientDrawable;->setColors([I)V

    .line 49
    sget-object v4, Landroid/graphics/drawable/GradientDrawable$Orientation;->TOP_BOTTOM:Landroid/graphics/drawable/GradientDrawable$Orientation;

    invoke-virtual {v2, v4}, Landroid/graphics/drawable/GradientDrawable;->setOrientation(Landroid/graphics/drawable/GradientDrawable$Orientation;)V

    .line 50
    const/high16 v4, 0x40000000    # 2.0f

    mul-float v4, v4, v0

    float-to-int v4, v4

    const/high16 v5, -0x1000000

    invoke-virtual {v2, v4, v5}, Landroid/graphics/drawable/GradientDrawable;->setStroke(II)V

    .line 51
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setBackground(Landroid/graphics/drawable/Drawable;)V

    .line 53
    new-instance v2, Landroid/widget/FrameLayout$LayoutParams;

    const/4 v4, -0x2

    invoke-direct {v2, v4, v4}, Landroid/widget/FrameLayout$LayoutParams;-><init>(II)V

    .line 54
    const/16 v4, 0x55

    iput v4, v2, Landroid/widget/FrameLayout$LayoutParams;->gravity:I

    .line 55
    const/high16 v4, 0x42dc0000    # 110.0f

    mul-float v4, v4, v0

    float-to-int v4, v4

    iput v4, v2, Landroid/widget/FrameLayout$LayoutParams;->bottomMargin:I

    .line 56
    const/high16 v4, 0x430a0000    # 138.0f

    mul-float v0, v0, v4

    float-to-int v0, v0

    iput v0, v2, Landroid/widget/FrameLayout$LayoutParams;->rightMargin:I

    .line 57
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    .line 59
    new-instance v0, Lcom/glu/tonsguns/FloatingCheatsButton$1$1;

    invoke-direct {v0, p0}, Lcom/glu/tonsguns/FloatingCheatsButton$1$1;-><init>(Lcom/glu/tonsguns/FloatingCheatsButton$1;)V

    invoke-virtual {v1, v0}, Landroid/widget/TextView;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    .line 67
    iget-object v0, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    iget-object v2, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-virtual {v2}, Landroid/app/Activity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v0, v2, v3}, Landroid/app/Activity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 68
    const-string v2, "cheat_mode_enabled"

    invoke-interface {v0, v2, v3}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v0

    .line 69
    if-eqz v0, :cond_2

    goto :goto_0

    :cond_2
    const/16 v3, 0x8

    :goto_0
    invoke-virtual {v1, v3}, Landroid/widget/TextView;->setVisibility(I)V

    .line 71
    invoke-static {v1}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfputbuttonView(Landroid/view/View;)V

    .line 72
    iget-object v0, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-virtual {v0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;

    move-result-object v0

    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;

    move-result-object v0

    check-cast v0, Landroid/view/ViewGroup;

    .line 73
    invoke-virtual {v0, v1}, Landroid/view/ViewGroup;->addView(Landroid/view/View;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    .line 76
    goto :goto_1

    .line 74
    :catchall_0
    move-exception v0

    .line 75
    invoke-virtual {v0}, Ljava/lang/Throwable;->printStackTrace()V

    .line 77
    :goto_1
    return-void
.end method
""",
    "FloatingCheatsButton$1$1.smali": """.class Lcom/glu/tonsguns/FloatingCheatsButton$1$1;
.super Ljava/lang/Object;
.source "FloatingCheatsButton.java"

# interfaces
.implements Landroid/view/View$OnClickListener;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingCheatsButton$1;->run()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic this$0:Lcom/glu/tonsguns/FloatingCheatsButton$1;


# direct methods
.method constructor <init>(Lcom/glu/tonsguns/FloatingCheatsButton$1;)V
    .locals 0

    .line 59
    iput-object p1, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1$1;->this$0:Lcom/glu/tonsguns/FloatingCheatsButton$1;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public onClick(Landroid/view/View;)V
    .locals 0

    .line 62
    iget-object p1, p0, Lcom/glu/tonsguns/FloatingCheatsButton$1$1;->this$0:Lcom/glu/tonsguns/FloatingCheatsButton$1;

    iget-object p1, p1, Lcom/glu/tonsguns/FloatingCheatsButton$1;->val$activity:Landroid/app/Activity;

    invoke-static {p1}, Lcom/glu/tonsguns/CheatsActivity;->launch(Landroid/content/Context;)V

    .line 63
    return-void
.end method
""",
    "FloatingCheatsButton$2.smali": """.class Lcom/glu/tonsguns/FloatingCheatsButton$2;
.super Ljava/lang/Object;
.source "FloatingCheatsButton.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingCheatsButton;->show()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# direct methods
.method constructor <init>()V
    .locals 0

    .line 83
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 3

    .line 87
    :try_start_0
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v0

    invoke-virtual {v0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object v0

    .line 88
    invoke-virtual {v0}, Landroid/content/Context;->getPackageName()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 89
    const-string v1, "cheat_mode_enabled"

    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v0

    .line 90
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v1

    if-eqz v0, :cond_0

    goto :goto_0

    :cond_0
    const/16 v2, 0x8

    :goto_0
    invoke-virtual {v1, v2}, Landroid/view/View;->setVisibility(I)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    .line 93
    goto :goto_1

    .line 91
    :catchall_0
    move-exception v0

    .line 92
    invoke-virtual {v0}, Ljava/lang/Throwable;->printStackTrace()V

    .line 94
    :goto_1
    return-void
.end method
""",
    "FloatingCheatsButton$3.smali": """.class Lcom/glu/tonsguns/FloatingCheatsButton$3;
.super Ljava/lang/Object;
.source "FloatingCheatsButton.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/glu/tonsguns/FloatingCheatsButton;->hide()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# direct methods
.method constructor <init>()V
    .locals 0

    .line 101
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 2

    .line 104
    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->-$$Nest$sfgetbuttonView()Landroid/view/View;

    move-result-object v0

    const/16 v1, 0x8

    invoke-virtual {v0, v1}, Landroid/view/View;->setVisibility(I)V

    .line 105
    return-void
.end method
""",
}

def apply_feature(workspace_dir):
    """
    Applies the Cheat System feature onto the decoded APK workspace.
    """
    print(f"\n[*] Installing feature: {FEATURE_NAME} ({FEATURE_ID})...")
    apk_decoded = os.path.join(workspace_dir, "apk_decoded")
    if not os.path.exists(apk_decoded):
        print(f"[-] Error: decoded APK folder not found at {apk_decoded}")
        return False

    # 1. Inject HTML into assets/cheats_preview.html
    assets_dir = os.path.join(apk_decoded, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    html_path = os.path.join(assets_dir, "cheats_preview.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(get_html_content())
    print(f"  [+] Injected cheats UI asset: {html_path}")

    # 2. Inject Smali classes into com/glu/tonsguns/
    smali_dir = os.path.join(apk_decoded, "smali", "com", "glu", "tonsguns")
    os.makedirs(smali_dir, exist_ok=True)
    for fname, smali_text in SMALI_CLASSES.items():
        with open(os.path.join(smali_dir, fname), "w", encoding="utf-8") as f:
            f.write(smali_text)
    print(f"  [+] Injected CheatsActivity & FloatingCheatsButton Smali classes into {smali_dir}")

    # 3. Register activity in AndroidManifest.xml
    manifest_path = os.path.join(apk_decoded, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_content = f.read()

        activity_tag = '''        <activity android:name="com.glu.tonsguns.CheatsActivity"
                  android:theme="@android:style/Theme.Translucent.NoTitleBar.Fullscreen"
                  android:screenOrientation="portrait"
                  android:configChanges="keyboard|keyboardHidden|orientation|screenSize"
                  android:hardwareAccelerated="true"
                  android:exported="true">
            <intent-filter>
                <action android:name="com.glu.tonsguns.SHOW_CHEATS"/>
                <category android:name="android.intent.category.DEFAULT"/>
            </intent-filter>
        </activity>
    </application>'''

        if "com.glu.tonsguns.CheatsActivity" not in manifest_content:
            manifest_content = manifest_content.replace("</application>", activity_tag)
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest_content)
            print("  [+] Registered CheatsActivity in AndroidManifest.xml")

    # 4. Hook UnityLauncherActivity.smali to initialize FloatingCheatsButton
    launcher_smali = os.path.join(apk_decoded, "smali", "com", "glu", "plugins", "AUnityInstaller", "UnityLauncherActivity.smali")
    if os.path.exists(launcher_smali):
        with open(launcher_smali, "r", encoding="utf-8") as f:
            launcher_content = f.read()
        target = "invoke-super {p0, p1}, Lcom/unity3d/player/UnityPlayerActivity;->onCreate(Landroid/os/Bundle;)V"
        if target in launcher_content and "FloatingCheatsButton;->init" not in launcher_content:
            launcher_content = launcher_content.replace(
                target,
                target + "\n\n    invoke-static {p0}, Lcom/glu/tonsguns/FloatingCheatsButton;->init(Landroid/app/Activity;)V"
            )
            with open(launcher_smali, "w", encoding="utf-8") as f:
                f.write(launcher_content)
            print("  [+] Hooked UnityLauncherActivity.smali (FloatingCheatsButton.init)")

    # 5. Hook CustomGlu.smali to synchronize floating cheats button with Unity home vs match
    custom_glu_smali = os.path.join(apk_decoded, "smali", "com", "glu", "plugins", "CustomGlu.smali")
    if os.path.exists(custom_glu_smali):
        with open(custom_glu_smali, "r", encoding="utf-8") as f:
            cg_content = f.read()
        
        show_target = ".method public static Show(Ljava/lang/String;III)V\n    .locals 2"
        if show_target in cg_content and "FloatingCheatsButton;->show" not in cg_content:
            cg_content = cg_content.replace(
                show_target,
                show_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->show()V"
            )

        hide_target = ".method public static Hide(Ljava/lang/String;)V\n    .locals 2"
        if hide_target in cg_content and "FloatingCheatsButton;->hide" not in cg_content:
            cg_content = cg_content.replace(
                hide_target,
                hide_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->hide()V"
            )

        hide_all_target = ".method public static HideAll()V\n    .locals 2"
        if hide_all_target in cg_content and "FloatingCheatsButton;->hide" not in cg_content:
            cg_content = cg_content.replace(
                hide_all_target,
                hide_all_target + "\n\n    invoke-static {}, Lcom/glu/tonsguns/FloatingCheatsButton;->hide()V"
            )

        with open(custom_glu_smali, "w", encoding="utf-8") as f:
            f.write(cg_content)
        print("  [+] Hooked CustomGlu.smali (FloatingCheatsButton show/hide on map vs match)")

    print(f"[+] Feature '{FEATURE_NAME}' applied successfully!\n")
    return True

if __name__ == '__main__':
    ws = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    apply_feature(ws)
