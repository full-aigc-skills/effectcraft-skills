# EffectCraft 独立技能

当前正在实现，尚未完成插件发布验收。

`effectcraft-use` 自带 Python 3.11+ 安装器，固定官方 macOS arm64 CLI 制品，校验压缩包和二进制，保留许可证，原子安装新版本，复用完整的已有版本。技能目录可独立复制，不依赖兄弟技能或插件私有路径。

运行测试：`python3 -m unittest discover -s tests -v`。完整创作流程和宿主验收仍待完成。

规范和任务：[EffectCraft 插件 OpenSpec](https://github.com/full-aigc-plugins/effectcraft-plugin/tree/main/openspec/changes/establish-v1-plugin)。

[English](README.md)

可执行工作流已覆盖原生工程往返、透明 PNG 预览、H.264 导出，以及保持其他图层和关键帧的文字修订。参见[工作流说明](skills/effectcraft-use/references/workflow.md)。真实测试使用 `CRAFT_LIVE_TEST=1 /opt/anaconda3/bin/python3 -m unittest discover -s tests -v`；测试需要 Pillow 与 ffprobe，助手本身不依赖这两个测试工具。

完整 15 项测试还覆盖原生素材收集、移动交付后修订以及保留图层动画的素材替换。收集后的原生引用为绝对路径；工作流修订已移动交付时会核验并重新链接素材。

开发版本 `0.1.0-dev.1` 修复并行首次安装/复用时的安装锁竞争：等待最多 120 秒，再核验复用；超时不覆盖安装或重放编辑任务。

开发版本 dev.2 的原生交付包含摘要绑定的 exchange-loss.json，区分格式损失、结构观察与未验证字体/效果保真；导出派生物不替代原生工程。

## CLI 与场景技能体系

[EffectCraft Skill Suite Architecture](docs/EffectCraft-Skill-Suite-Architecture.zh_CN.md)

| 技能 | 用途 |
| :--- | :--- |
| `effectcraft-use` | 组合多个本工具能力并保留可编辑原生交付 |
| `effectcraft-cli` | 查询实际命令参数和能力，调用公开 CLI、MCP 与诊断 |
| `effectcraft-cli-setup` | 首次安装、摘要校验、版本检查与缺失运行时排障 |
| `effectcraft-cli-project` | 建立、保存和重开 ecproj 工程，整理项目项目项 |
| `effectcraft-cli-footage` | 导入图像、视频、矢量或 PSD 素材并登记依赖 |
| `effectcraft-cli-composition` | 创建合成、设置画幅帧率时长和工作区 |
| `effectcraft-cli-layers` | 组织文本、形状、素材图层和层级合成 |
| `effectcraft-cli-animation` | 设置属性、关键帧、缓动和文字图形动画 |
| `effectcraft-cli-effects` | 查询并应用当前版本支持的效果，调整效果顺序与参数 |
| `effectcraft-cli-masks` | 创建和编辑蒙版路径、羽化及局部遮罩 |
| `effectcraft-cli-expressions` | 在用户指定属性上检查、设置和诊断表达式 |
| `effectcraft-cli-camera` | 设置已有合成中的摄像机、灯光和材质参数 |
| `effectcraft-cli-export` | 预览关键帧、渲染序列或视频和透明交接片段 |

`npx skills add full-aigc-skills/effectcraft-skills --skill <skill-name>`

## 场景技能的干净首次使用

0.1.0-dev.4 补齐相机创建与三维视角前置命令，并明确 RGB 预览与 RGBA 透明导出的已测路径。十类场景均只复制当前技能、使用新运行时目录完成首次安装及真实操作；完整回归 35 项、零跳过。[证据](docs/evidence/task-skill-first-use.json)。全部命令、高级三维画面、模型派发和创作最终验收仍未完成。

```bash
CRAFT_TASK_FIRST_USE=1 CRAFT_LIVE_TEST=1 CRAFT_LIVE_SUITE=1 python3 -B -m unittest discover -s tests -v
```

命令统一使用 `SKILL_DIR`，其值为宿主实际加载的 `SKILL.md` 所在绝对目录。支持用户级、项目级 `.agents/skills` 及插件内部或缓存目录；CLI 运行时另外安装到用户数据目录。每个技能单独复制到三种含空格的布局后，文档中的脚本入口均可运行 `--help`。[路径验证](docs/evidence/installed-skill-paths.json)。既有宿主缓存需更新后才会收到修正文档。

技能套件 dev.6 增加自包含可编辑蒙版示例，接通公开蒙版顶点修改/移除工作流。默认公开下载的原生回归 39 项全部通过、无跳过；场景技能各自从空运行时安装，蒙版修订保留原工程与非目标文字，RGBA 实际像素验证边界变化。[证据](docs/evidence/task-skill-first-use.json)。运行时保持 0.2.0；模型/GUI、创作及任意复杂蒙版保真仍需验收。

[透明素材到 FilmCraft 的实际交接](docs/EffectCraft-FilmCraft-Alpha-Handoff-Acceptance.zh_CN.md)：安装后双领域空运行时 1 项通过；修改片头文字保留动画，原生 RGBA PNG 在 FilmCraft 中露出底层并保留不透明前景像素。完整色彩／动画透明视频验收仍开放。

安装后的动画技能时序首次使用通过：4 个原生 RGBA 时刻与 12 帧视频解码核对淡入；文字返工保留徽标、关键帧属性及原交付。[时序验收](docs/EffectCraft-Temporal-Animation-Acceptance.zh_CN.md)。完整创作及动画透明视频验收仍开放。
