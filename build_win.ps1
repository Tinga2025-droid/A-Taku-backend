python -m pip install --upgrade pip wheel
pip install -r app/requirements.txt pyinstaller
pyinstaller -y pyinstaller.spec
Write-Host "EXE gerado em: dist/A-Taku-Server.exe"
