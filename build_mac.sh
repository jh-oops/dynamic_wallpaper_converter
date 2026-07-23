#!/bin/bash
# 构建 macOS 独立程序（.app）
# 用法：bash build_mac.sh   （需先有 python3 + 本目录依赖）
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "== 安装依赖 =="
"$PY" -m pip install -q -r requirements.txt

echo "== 定位 ffmpeg 二进制 =="
FFDIR=$("$PY" -c "import imageio_ffmpeg,os;print(os.path.join(os.path.dirname(imageio_ffmpeg.__file__),'binaries'))")

echo "== PyInstaller 打包 =="
"$PY" -m PyInstaller --noconfirm --windowed --name "动态壁纸生成器" \
  --add-data "web_ui.html:." \
  --add-data "tags_library.json:." \
  --add-data "$FFDIR:imageio_ffmpeg/binaries" \
  --hidden-import app --hidden-import transcode_for_zip --hidden-import tag_matcher --hidden-import image_analyzer \
  main_app.py

echo "== 完成 =="
echo "产物：dist/动态壁纸生成器.app"

echo "== 复制到 /Applications（方便通过聚焦搜索/启动台打开）=="
rm -rf "/Applications/动态壁纸生成器.app"
cp -R "dist/动态壁纸生成器.app" "/Applications/动态壁纸生成器.app"
echo "已安装到：/Applications/动态壁纸生成器.app"

echo ""
echo "若双击被 Gatekeeper 拦截，可运行："
echo "  xattr -cr \"/Applications/动态壁纸生成器.app\""
echo "  codesign --force --deep --sign - \"/Applications/动态壁纸生成器.app\""
