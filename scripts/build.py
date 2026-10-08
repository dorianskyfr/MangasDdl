"""Build a portable native application with the current Python environment."""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onedir', '--windowed', '--name', 'MangasDdl',
        '--hidden-import', 'PIL.AvifImagePlugin',
        '--exclude-module', 'PySide6.QtWebEngineCore',
        '--exclude-module', 'PySide6.QtWebEngineWidgets',
        str(ROOT / 'main.py'),
    ], cwd=ROOT, check=True)
    folder = ROOT / 'dist' / 'MangasDdl'
    executable = folder / ('MangasDdl.exe' if sys.platform == 'win32' else 'MangasDdl')
    subprocess.run([str(executable), '--smoke-test'], cwd=folder, check=True, timeout=30)
    archive = shutil.make_archive(str(ROOT / 'dist' / f'MangasDdl-1.0.0-{platform.system().lower()}'), 'zip', root_dir=ROOT / 'dist', base_dir='MangasDdl')
    print(f'Archive prête : {archive}')


if __name__ == '__main__':
    main()
