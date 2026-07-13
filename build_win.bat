@echo off
REM 构建 Windows 独立程序（.exe）
REM 用法：双击运行，或在 CMD 中 build_win.bat
cd /d "%~dp0"
set PY=%PYTHON%
if "%PY%"=="" set PY=python

echo == 安装依赖 ==
%PY% -m pip install -q -r requirements.txt

echo == 定位 ffmpeg 二进制 ==
for /f "delims=" %%i in ('%PY% -c "import imageio_ffmpeg,os;print(os.path.join(os.path.dirname(imageio_ffmpeg.__file__),'binaries'))"') do set FFDIR=%%i

echo == PyInstaller 打包 ==
%PY% -m PyInstaller --noconfirm --windowed --name "动态壁纸生成器" --add-data "web_ui.html;." --add-data "%FFDIR%;imageio_ffmpeg/binaries" --hidden-import app --hidden-import transcode_for_zip main_app.py

echo == 完成 ==
echo 产物：dist\动态壁纸生成器.exe
pause
