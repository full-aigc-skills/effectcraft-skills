# 原生合成计划 / Native composition plans

`workflow.py` 首次调用安装器，然后在持续 MCP 会话中创建或修改合成。它保存原生 `.ecproj`、重新打开检查属性，并调用原生渲染器输出透明 PNG 和可选 H.264 视频。需要 Python 3.11+；当前运行时锁仅支持 macOS arm64。

The helper bootstraps the pinned runtime, executes a bounded plan in a persistent MCP session, saves and reopens the native project, then renders transparent PNG frames and optional H.264 video. Runtime support currently covers macOS arm64 only.

```bash
python3 /mnt/skills/user/effectcraft-cli-layers/scripts/workflow.py \
  /mnt/skills/user/effectcraft-cli-layers/examples/brand-intro.json \
  --output /absolute/path/intro-v1
```

技能安装在其他位置时替换技能根路径。输出目录必须不存在；不含外部素材时原子发布新目录；有外部素材时原生收集器需要稳定的最终目录，失败目录包含 `failure.json` 且没有成功清单，不可作为完成交付。安装目录不存放工程。

Replace the skill root with its actual loaded location. The output directory must not exist. Asset-free work is published by atomic rename. Native media collection needs the final directory to remain stable; a failed collection leaves failure.json without a successful manifest and is not a completed delivery.

## 计划与修订 / Plans and revisions

- `document`：新合成的名称、宽高、帧率、时长；时长及采样时间单位为秒。
- `operations`：原生命令及参数；`as` 将返回值保存为别名，`{"$ref":"title.layer"}` 引用原生图层 ID。命令以运行时注册表为准。
- `frames`：透明 PNG 的采样时刻，不得超出合成范围。
- `exports`：可选 `[{"format":"mp4"}]`；MP4 为不带透明通道的 H.264，不能当作透明视频交付。

`document` creates a composition. `operations` contains native commands and parameters; aliases reference returned IDs. `frames` selects transparent PNG samples. Optional MP4 export uses H.264 without alpha.

修订时读取上次 `manifest.json`，将 `files["project.ecproj"]` 写入新计划的 `expectedProjectSha256`，通过 `--source /absolute/path/intro-v1` 和新的 `--output` 调用。省略 `document`，仅传目标修改。摘要不一致立即报 `revision_conflict`，不覆盖用户修改。禁止并发写入同一输出路径。

For revisions, copy the prior manifest's project digest into `expectedProjectSha256`, pass `--source`, omit `document`, and use a new output directory. A digest mismatch stops the revision. Do not run concurrent writers against the same output path.

当前 CLI 的 `--comp` 使用合成名称；MCP 使用数字 ID。视频导出前检查名称唯一，避免选错同名合成。时间线、效果和关键帧保存在原生工程中；`native.json` 用于核对，不替代原生工程。

The pinned CLI requires the composition name for `--comp`, whereas MCP accepts numeric IDs. Video export checks name uniqueness. The editable project remains authoritative; `native.json` is inspection evidence.

## 交付与验证 / Delivery and verification

交付包含工程、`plan.json`、`operations.json`、`native.json`、透明预览、可选 MP4，以及带文件摘要的 `manifest.json`。示例仅包含内建图形和系统字体。外部素材通过下述注册入口导入并由原生收集器打包，清单核对收集后文件摘要。

The delivery contains the project, plan, operation receipts, inspection snapshot, previews, optional MP4 and a hashed manifest. The example uses built-in shapes and a system font. Registered external media is packaged by the native collector and checked against its declared digest.

已验证：原生往返、两关键帧透明度动画、效果参数保留、PNG alpha、MP4 解码帧数，以及修改文字后其他图层与关键帧不变。真实品牌视觉验收、蒙版覆盖、完整 Harness、插件宿主安装仍需单独验收。

Verified coverage includes native round trips, two-key opacity animation, retained effect parameters, PNG alpha, decoded MP4 frame count, and text revisions preserving other layers and animation. Brand-level visual review, mask coverage, the full Harness and plugin-host installation still require separate acceptance.

## 外部素材与替换 / External media and replacement

用 `--asset logo=/absolute/path/logo.png` 注册文件；计划内 `asset.import` 参数为 `{"asset":"logo"}`，例如 `as: "logoItem"`；随后 `layer.addItem` 的 `item` 参数引用 `{"$ref":"logoItem.item"}`。禁止导入未注册的项目项。安装目录不参与素材交付。

Register a file with `--asset logo=/absolute/path/logo.png`. Use `asset.import` with `{"asset":"logo"}` and alias `logoItem`, then reference `{"$ref":"logoItem.item"}` from `layer.addItem`. Unregistered project dependencies are rejected.

收集后的 `.ecproj` 引用 `(Footage)` 内的绝对路径。移动整个交付目录后，通过 `--source` 修订会先核对继承素材摘要、复制到新工作目录并重新链接。直接在其他应用打开已移动的工程可能需要重新链接，不能宣称原生工程完全使用相对路径。

Collected projects contain absolute paths into `(Footage)`. Revising a moved delivery through `--source` verifies inherited hashes, copies media and relinks it. Opening a moved project directly in another application may require relinking.

替换素材时先导入新的注册素材，再用 `asset.replace` 参数 `{"asset":"logo","replacement":"newLogo"}`。该操作保留原项目项 ID，已有图层、时长和关键帧继续引用同一个项目项；新交付保留最新依赖摘要，原交付不覆盖。

Import the replacement first, then use `asset.replace` with `{"asset":"logo","replacement":"newLogo"}`. The existing project item ID and layer animation remain intact. A new delivery records the replacement digest and preserves the source delivery.

15 项完整测试通过，其中素材用例检查原生收集、移动后修订、PNG 替换像素、图层与关键帧保持以及错误摘要拒绝。素材样本为程序生成的 PNG，不构成品牌视觉验收。

All 15 tests passed, including native collection, moved-delivery revision, replacement PNG pixels, preserved layers and keyframes, and digest rejection. Procedural PNG fixtures do not establish brand-level visual acceptance.
