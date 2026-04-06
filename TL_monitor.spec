# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
        ('logo.ico', '.'),
        ('index.html', '.'),
        ('config.yaml', '.'),
        ('notifier.py', '.'),
        ('scraper.py', '.'),
    ],
    hiddenimports=[

        'playwright',
        'playwright.sync_api',
        'playwright.async_api',
        'playwright._impl',
        'playwright._impl._driver',
        'webdriver_manager',
        'webbrowser',
        'notifier',
        'yaml',
        'numpy',
        'PIL',
        'urllib3',
        'idna',
        'charset_normalizer',
        'certifi',
        'cryptography',
        'cffi',
        'greenlet',
        'pyee',
        'wsclient',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    forge=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TL_monitor',
    debug=False,
    console=True,
    icon='logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='TL_monitor',
)
