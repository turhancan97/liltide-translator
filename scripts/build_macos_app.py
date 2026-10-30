"""Build a local macOS app; no installation, credentials or cloud calls."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != 'darwin':
        raise SystemExit('Build Liltide.app on macOS with a macOS Python interpreter.')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'packaging/macos'))
    from notices import collect
    collect(root / 'build/macos-notices')
    # Keep generated caches inside the ignored build directory.
    import os
    env = os.environ.copy()
    env['PYINSTALLER_CONFIG_DIR'] = str(root / 'build/pyinstaller-cache')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        str(root / 'packaging/macos/Liltide.spec')], cwd=root, env=env, check=True)
    print(f'Built {root / "dist/Liltide.app"}')


if __name__ == '__main__':
    main()
