@echo off
echo ================================================
echo   DTF MANAGER PRO - GERANDO EXECUTAVEL
echo ================================================
echo.
cd /d "%~dp0"

py -3.11 -m pip install pyinstaller customtkinter pillow psd-tools numpy fpdf2 openpyxl -q

if exist "build\DTF MANAGER PRO" rmdir /s /q "build\DTF MANAGER PRO"
if exist "dist\DTF MANAGER PRO" rmdir /s /q "dist\DTF MANAGER PRO"

py -3.11 -m PyInstaller DTF_MANAGER_PRO.spec

echo.
if exist "dist\DTF MANAGER PRO\DTF MANAGER PRO.exe" (
    echo ================================================
    echo   EXE gerado com sucesso!
    echo ================================================
    echo   Revise dist\DTF MANAGER PRO\ antes de copiar para
    echo   a pasta de instalacao final.
    echo   Nao esqueca de copiar tambem: assets\psds\ e dtf_pro.db
    echo   (dados do usuario, nao fazem parte do build).
) else (
    echo ERRO: EXE nao foi gerado.
)
pause
