# 动态壁纸 ZIP 生成器（Dynamic Wallpaper Converter）

把 mp4 一键生成符合后台规范的动态壁纸 zip（H.264 自动转码 / 抽首帧 / 缩略图 GIF / manifest）。

- 仓库：https://github.com/jh-oops/dynamic_wallpaper_converter
- 下载（Release v1.0）：https://github.com/jh-oops/dynamic_wallpaper_converter/releases/tag/v1.0
- **在线网页版（无需下载，点开即用）**：https://jh-oops.github.io/dynamic_wallpaper_converter/

---

## 一、两种用法（分层设计）

| 工具 | 适用场景 | 是否需安装 |
|------|----------|-----------|
| **网页版** `dynamic_wallpaper_zip_generator.html` | 视频已合规（H.264 + 1080×2400 + ≤5M） | 否，浏览器双击即用、离线 |
| **桌面版** `动态壁纸生成器.app` / `.exe` | 视频需转码（非 H.264 / 分辨率不符 / 超 5M） | 下载解压双击，离线、素材不出本机 |

> **推荐流程**：先用网页版拖入 mp4。视频合规 → 浏览器直接出包；不合规 → 网页弹提示并给出桌面程序下载入口，用桌面版转码后一步出包。

---

## 二、普通用户：网页版怎么用（零安装）

1. 下载 `dynamic_wallpaper_zip_generator.html`（从 Release 页，或从仓库根目录）
2. **双击用浏览器打开**（Chrome / Edge / Safari 均可）
3. 填写：
   - **名称 name**：必填，下载的 zip 以此命名
   - **作者 author**：必填，须与设计师账号一致，**区分大小写**
   - **描述 description**：必填
4. 拖入 mp4 → 点「生成并下载 ZIP」

> ⚠️ 网页版**只能处理合规视频**。若视频非 H.264、分辨率不是 1080×2400、或体积 > 5M，网页会弹黄色引导卡片说明原因，并给出桌面程序下载按钮（见「四、分发给同事」）。

---

## 三、普通用户：桌面版怎么用（含转码）

无需安装 Python / ffmpeg，双击即用，离线运行，素材不出本机。

### macOS
1. 双击 `动态壁纸生成器.app`
2. 浏览器自动打开 `http://localhost:8000/`（没开就点程序窗口里的「打开网页」）
3. 填 name / author / description，拖入 mp4，点「生成并下载 ZIP」

> ⚠️ **首次打开被拦（「无法打开」「无法确认开发者」）**，选一种解除方式：
> - **方式 A**：右键 `动态壁纸生成器.app` → **打开**（或 系统设置 → 隐私与安全性 → 仍要打开）
> - **方式 B（命令行）**：终端执行
>   ```bash
>   xattr -cr "/Users/你的用户名/.../动态壁纸生成器.app"
>   ```
>   说明：在终端输入 `xattr -cr `（末尾有空格），把 `.app` 从 Finder **拖进终端**自动填路径，回车即可（无报错即成功）。把 app 放到哪，路径就用哪的。
> - 首次运行可能弹「允许传入连接」，**允许**即可（本地 8000 端口）。
>
> 想正式发给同事的 Mac，需用 Apple Developer ID 证书 `codesign` 签名后才能免拦截。

### Windows
1. 双击 `动态壁纸生成器.exe`
2. 浏览器自动打开 `http://localhost:8000/`
3. 同上填写并生成

> ⚠️ 首次运行若被 SmartScreen / Windows Defender 拦截，选「**仍要运行**」即可（内部工具未做代码签名）。若防火墙提示，允许「专用网络」访问。

### 程序窗口说明
启动后出现小控制窗口，可：
- **打开网页**：跳到操作页面
- **退出程序**：停止本地服务并退出

> 同一台电脑同时只能跑一个实例（占用 8000 端口）。重复双击会直接打开已运行的页面。

---

## 四、分发给同事（两种方式）

### 方式 A：甩 Release 链接（最省事，推荐）
直接把下面链接发给同事，让他们按需在 Release 页下载：
**https://github.com/jh-oops/dynamic_wallpaper_converter/releases/tag/v1.0**

Release 内含 3 个文件：
| 文件 | 用途 |
|------|------|
| `dynamic_wallpaper_zip_generator.html` | 网页版（零安装） |
| `dynamic-wallpaper-converter-mac.zip` | macOS 桌面版（解压得 `动态壁纸生成器.app`） |
| `dynamic-wallpaper-converter-win.zip` | Windows 桌面版（解压得 `动态壁纸生成器.exe`） |

### 方式 B：文件夹分发（让网页的下载按钮生效）
把下面 3 个文件**放在同一目录**一起发给同事，则网页内「下载桌面程序」按钮可点：
- `dynamic_wallpaper_zip_generator.html`
- `动态壁纸生成器-mac.zip`（注意：此处用**中文名**，按钮按此名查找）
- `动态壁纸生成器-win.zip`（注意：此处用**中文名**）

> 区别：Release 上的 zip 用 ASCII 名（`dynamic-wallpaper-converter-*-zip`）便于下载；文件夹分发用中文名以匹配网页按钮相对链接。两者内容一致，只是文件名不同。

---

## 五、规范要点（生成产物需满足）

- `manifest.json`：`{ id: UUID, type: 8, author, name, description }`
- `preview/wallpaper.jpg`：1080×2400、首帧、≤800K
- `preview/thumbnail.gif`：400×710、10–15fps、前 2 秒、≥128 色、≤1.5M
- `wallpapers/wallpaper.mp4`：1080×2400、H.264、≤5M（非 H.264 源自动转码）
- 可选动态预览图 540×1200、≤2M（不进包，仅本地预览用）
- zip 内**不得**含 `__MACOSX`

---

## 六、开发者：如何自己构建

依赖见 `requirements.txt`：`flask`、`imageio-ffmpeg`、`Pillow`、`pyinstaller`。

### macOS 本地构建
```bash
bash build_mac.sh
# 产物：dist/动态壁纸生成器.app
```

### Windows 本地构建（需 Windows 环境）
双击 `build_win.bat`，或 CMD 中：
```bat
build_win.bat
# 产物：dist\动态壁纸生成器.exe
```

### 跨平台 CI（GitHub Actions）
推到 GitHub 后，Actions 在 `macos-latest` 和 `windows-latest` 自动构建。触发方式：
- 手动：Actions → Build Desktop App → Run workflow
- 或打 `v*` 标签推送（如 `git tag v1.0 && git push origin v1.0`）

构建产物在 Actions 页面的 Artifacts 下载；也可在 CI 末尾加步骤自动上传到 Release。

> CI 注意点：Windows 打包用 `--onefile`（PyInstaller 默认 onedir 会产出目录，上传路径需对应调整）；工作流已加 `permissions: contents: read / actions: write` 保证 `upload-artifact` 不卡权限；推送工作流文件需 PAT 带 `workflow` scope。

### 无界面模式（服务器 / CI / 沙箱）
```bash
WP_NO_GUI=1 ./动态壁纸生成器   # 不弹窗口，直接跑本地后端
```

---

## 七、文件清单

| 文件 | 作用 |
|------|------|
| `main_app.py` | 打包入口：后端线程 + 自动开浏览器 + Tk 控制窗口 |
| `app.py` | Flask 服务（页面 + `/api/package` 接口），可单独 `python app.py` 运行 |
| `transcode_for_zip.py` | 转码 / 抽帧 / 缩略图 / manifest / 打包核心逻辑 |
| `web_ui.html` | 前端页面（暗色主题，桌面版用） |
| `dynamic_wallpaper_zip_generator.html` | 单文件网页版（纯浏览器，零依赖） |
| `builder/` | 单文件网页版的构建链（模板 + 内联 JSZip/gifenc） |
| `requirements.txt` | Python 依赖 |
| `build_mac.sh` / `build_win.bat` | 本地构建脚本 |
| `.github/workflows/build.yml` | 跨平台 CI |
| `spec/` | 内部规范原文与官方示例（参考，非运行必需） |
