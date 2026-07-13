# 动态壁纸 ZIP 生成器

把 mp4 一键生成符合后台规范的动态壁纸 zip（H.264 转码 / 抽首帧 / 缩略图 GIF / manifest）。

## 两种用法（分层设计）

| 工具 | 适用 | 是否需安装 |
|------|------|-----------|
| **网页版** `dynamic_wallpaper_zip_generator.html` | 视频已合规（H.264 / 1080×2400 / ≤5M） | 否，双击即用、纯浏览器、离线 |
| **桌面版** `动态壁纸生成器.app` / `.exe` | 视频需转码（非 H.264 / 分辨率不符 / 超 5M） | 下载解压双击 |

**推荐流程**：先用网页版拖入 mp4；若视频合规，浏览器直接出包；若不合规，网页会弹出提示并给出桌面程序下载入口，用桌面版转码后一步出包。

> 为让网页里的下载按钮生效，需把 `动态壁纸生成器-mac.zip`、`动态壁纸生成器-win.zip` 与
> `dynamic_wallpaper_zip_generator.html` **放在同一目录**一起分发。

---

## 桌面版说明

无需安装 Python、ffmpeg，双击即用，离线运行，素材不出本机。

## 一、普通用户：怎么用

### macOS
1. 双击 `dist/动态壁纸生成器.app`
2. 浏览器自动打开 `http://localhost:8000/`（若没开，点程序窗口里的「打开网页」）
3. 拖入 mp4，填写：
   - **名称 name**（英文，下载的 zip 以此命名，必填）
   - **作者 author**（须与设计师账号一致，区分大小写，必填）
   - **描述 description**（必填）
4. 点「生成并下载 ZIP」即可

> ⚠️ 首次打开若被 Gatekeeper 拦截（「无法打开」）：
> - 右键 `动态壁纸生成器.app` → **打开**（或 系统设置 → 隐私与安全性 → 仍要打开）；或
> - 终端执行：`xattr -cr "动态壁纸生成器.app"` 后重试。
>
> 首次运行可能弹出「允许传入连接」，**允许**即可（本地 8000 端口）。
>
> 想要正式分发给他人的 Mac，需用 Apple Developer ID 证书 `codesign` 签名（见下）。

### Windows
1. 双击 `dist/动态壁纸生成器.exe`
2. 浏览器自动打开 `http://localhost:8000/`
3. 同上填写并生成
> 若 Windows Defender / 防火墙提示，允许「专用网络」访问即可。

## 二、程序窗口说明
启动后会出现一个小控制窗口，显示「服务运行中 + 地址」，可：
- **打开网页**：跳到操作页面
- **退出程序**：停止本地服务并退出

> 同一台电脑同时只能跑一个实例（占用 8000 端口）。重复双击会直接打开已运行的页面。

## 三、开发者：如何自己构建

依赖见 `requirements.txt`：`flask`、`imageio-ffmpeg`、`Pillow`、`pyinstaller`。

### macOS 构建
```bash
bash build_mac.sh
# 产物：dist/动态壁纸生成器.app
```

### Windows 构建（需 Windows 环境）
双击 `build_win.bat`，或 CMD 中执行：
```bat
build_win.bat
# 产物：dist\动态壁纸生成器.exe
```

### 跨平台 CI（GitHub Actions）
推到 GitHub 后，Actions 会在 `macos-latest` 和 `windows-latest` 上自动构建，
在 Actions 页面的 Artifacts 中下载 `.app` / `.exe`。触发方式：
- 手动：Actions → Build Desktop App → Run workflow
- 或打 `v*` 标签推送

### 无界面模式（服务器 / CI / 沙箱）
```bash
WP_NO_GUI=1 ./动态壁纸生成器   # 不弹窗口，直接跑本地后端
```

## 四、文件清单
| 文件 | 作用 |
|------|------|
| `main_app.py` | 打包入口：后端线程 + 自动开浏览器 + Tk 控制窗口 |
| `app.py` | Flask 服务（页面 + `/api/package` 接口），可单独 `python app.py` 运行 |
| `transcode_for_zip.py` | 转码/抽帧/缩略图/manifest/打包核心逻辑 |
| `web_ui.html` | 前端页面（暗色主题） |
| `requirements.txt` | 依赖 |
| `build_mac.sh` / `build_win.bat` | 构建脚本 |
| `.github/workflows/build.yml` | 跨平台 CI |

## 五、规范要点（生成产物需满足）
- `wallpaper.jpg`：1080×2400、首帧、≤800K
- `thumbnail.gif`：400×710、10–15fps、前 2 秒、≤1.5M
- `wallpapers/wallpaper.mp4`：1080×2400、H.264、≤5M（非 H.264 源自动转码）
- `manifest.json`：{ id:UUID, type:8, author, name, description }
- 可选动态预览图 540×1200，≤2M（不进包）
