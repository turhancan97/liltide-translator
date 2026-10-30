# Local arm64/x86_64 build uses the architecture of the build interpreter.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path(SPECPATH).parents[1]
speech_data, speech_bins, speech_imports = collect_all('azure.cognitiveservices.speech')
a = Analysis([str(root / 'packaging/macos/entry.py')],
    pathex=[str(root / 'src'), str(root / 'packaging/macos')],
    binaries=speech_bins,
    datas=speech_data + collect_data_files('liltide') +
        [(str(root / 'LICENSE'), 'notices'), (str(root / 'build/macos-notices'), 'notices/dependencies')],
    hiddenimports=speech_imports + ['keyring.backends.macOS', 'soundcard.coreaudio'],
    hookspath=[], runtime_hooks=[],
    excludes=['pytest', 'tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Liltide',
          console=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name='Liltide')
app = BUNDLE(coll, name='Liltide.app', icon=str(root / 'packaging/macos/Liltide.icns'),
    bundle_identifier='org.liltide.translator', info_plist={
        'CFBundleDisplayName': 'Liltide',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'Liltide captures only the input you select when you click Start. Translation sends that audio to Azure Speech.',
    })
