# -*- mode: python ; coding: utf-8 -*-
import os, sys, platform

block_cipher = None

def get_browser_path():
    """获取 Playwright Chromium 路径（跨平台）"""
    try:
        from playwright.paths import browser_executable_path
        p = browser_executable_path("chromium")
        if p and os.path.exists(p):
            return os.path.dirname(os.path.dirname(p))
    except:
        pass
    return None

chromium_base = get_browser_path()
system = platform.system()
print(f"Platform: {system}, Chromium: {chromium_base}")

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('index.html', '.'),
        ('import_template.csv', '.'),
        ('config.yaml', '.'),
        ('logo.png', '.'),
        ('notifier.py', '.'),
    ],
    hiddenimports=[
        'scraper', 'yaml', 'urllib3', 'idna',
        'charset_normalizer', 'certifi', 'cryptography',
        'OpenSSL', 'numpy', 'PIL', 'playwright',
        'playwright.sync_api', 'playwright._impl._driver',
        'webdriver_manager', 'webbrowser', 'notifier', 'urllib.request',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 打包 Chromium（仅 macOS/Linux，Windows 由 GitHub Actions workflow 单独处理）
if chromium_base and os.path.exists(chromium_base):
    a.datas += [
        ('playwright_browsers', chromium_base, 'ALWAYS_COPY'),
    ]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TL_monitor',
    debug=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TL_monitor',
)
