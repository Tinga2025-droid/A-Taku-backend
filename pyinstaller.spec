block_cipher = None
from PyInstaller.building.build_main import Analysis, PYZ, EXE
a = Analysis(['-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8080'],
             pathex=['.'],
             binaries=[], datas=[('app','app')],
             hiddenimports=['app','app.routers','app.models','app.database','app.auth','app.utils'],
             hookspath=[], runtime_hooks=[], excludes=[])
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, name='A-Taku-Server', console=True)
