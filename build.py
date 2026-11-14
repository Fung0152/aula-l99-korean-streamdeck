"""Build the portable app; copy only distributable assets, never local settings."""
from pathlib import Path
import shutil
import PyInstaller.__main__

ROOT=Path(__file__).resolve().parent
PyInstaller.__main__.run(['--noconfirm','--windowed','--onedir','--exclude-module','numpy',
    '--hidden-import','serial.tools.list_ports','--hidden-import','pystray._win32',
    '--name','L99StreamDeck','--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build'),
    '--specpath',str(ROOT/'build'),str(ROOT/'app/main.py')])
dest=ROOT/'dist/L99StreamDeck'
for name in ('assets','vendor'):shutil.copytree(ROOT/'app'/name,dest/name,dirs_exist_ok=True)
for name in ('LICENSE','THIRD_PARTY.md'):shutil.copy2(ROOT/name,dest/name)
shutil.copy2(ROOT/'app/USAGE.ko.md',dest/'사용안내.md')
shutil.copy2(ROOT/'app/USAGE.en.md',dest/'USAGE.en.md')
