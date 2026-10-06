# EffectCraft 独立技能

本领域 13 个技能逐个单独复制、从各自空运行时公开安装后，配套返工计划全部通过（145.856 秒，零跳过）。[返工证据](docs/evidence/complete-command-revision-first-use-20261007.json)。更新快照的真实固定宿主安装另设门禁。

完整命令入口补充了配套的创建／返工 JSON 示例、重新打开后的显式选择前置条件，以及原生保存重开、非目标对象与像素检查。每个独立技能均包含两个可执行计划。[调用指南](skills/effectcraft-use/references/command-usage.md#7-可执行局部返工--executable-targeted-revision)。全量逐命令及 GUI 验收保持开放。

当前固定 Codex 快照首用通过：五插件／58 技能发现、58 项安装技能分别空运行时公开安装、四领域完整命令代表样例、Art HD 返工／恢复／移动包、安装摘要保全与固定发行 CI。[证据](docs/evidence/codex-complete-command-first-use-20261007.json)。这是有范围的原生验收；通用 Skills CLI 安装和全命令／GUI 验收仍开放。

## 完整原生命令入口

全部 13 项独立技能分别从空运行时使用公开锁定 CLI 附件安装，随后完成创建、保存重开、领域参数及渲染检查（152.42 秒，零跳过）。[逐技能冷首用证据](docs/evidence/complete-commands-cold-first-use-20261007.json)。本轮覆盖每项技能的完整命令代表样例；全命令／GUI 和实际宿主安装另行验收。

已发布开发快照：skills dev.11 / plugin dev.12；固定宿主首用代表门禁通过。

640 条命令现在均有逐项参数说明、技能归属与同会话调用入口。运行 `commands.py list / describe / check / run`；原生状态按实时 enabled 校验。旧工作流的 21 项交付合同保留。GUI 命令需显式 bridge，命令目录覆盖不代表全量验收。

[架构与操作指南](docs/EffectCraft-Complete-Commands-Architecture.zh_CN.md) · [逐项参考](skills/effectcraft-use/references/command-reference.md) · [可运行示例](skills/effectcraft-use/examples/commands-advanced.json)

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

EffectCraft 独立技能源 dev.7 对效果／蒙版计划参数校验错误返回 unsupported_mapping；原生 CLI 仍为 0.2.0。真实新建／修订拒绝保留原交付，完整原生技能源回归 44 项通过、零跳过（182.083 秒）。固定新版插件安装后的限定范围复验见下文。[架构](docs/EffectCraft-Parameter-Errors-Architecture.zh_CN.md) · [证据](docs/evidence/parameter-mapping-repair-20261006.json)。

固定插件 dev.8／技能源 dev.7 的安装后验收通过：五插件 58 技能、零加载错误；独立效果／蒙版技能从空运行时核对有效创建及非法新建／修订 1 项通过（24.714 秒），13 技能分别公开冷启动全部通过，全部宿主安装摘要保留。[发行绑定证据](docs/evidence/codex-effectcraft8-parameter-first-use-20261006.json)。ArtCraft 的领域包升级及错误传播、完整首版等门禁仍开放。

动态 RGBA PNG 序列保留可编辑 ecproj，并通过 craft-image-sequence/v1 交付全部帧摘要、帧率和时长。源码冷安装及实际 Film 交接通过；新固定插件和 Art 验收仍待完成。[架构](docs/EffectCraft-Dynamic-Sequence-Architecture.zh_CN.md)。

固定 Effect dev.9 与 Film dev.10 安装后的动态交接已通过：三项真实原生测试、58 技能发现零错误、逐项执行后全部安装摘要保全。[证据](docs/evidence/codex-effectcraft9-filmcraft10-dynamic-first-use-20261006.json)。Art 动态集成仍待完成。

技能源 dev.9 增加整份效果／蒙版计划字段预检：读取源工程和安装原生 CLI 之前拒绝未知／缺失字段；反射合同绑定固定二进制，任何工程编辑前核对实际 schema。对象／属性／数值仍由原生检查。不可变发行与安装后验收分别记录。

固定插件 dev.10／技能源 dev.9 安装后验收通过：Codex 发现全部 58 技能且零加载错误；13 项 Effect 技能分别从空目录公开安装 CLI，非法计划在安装／编辑前拒绝；4 项动画／序列／Film 交接回归与 13 项领域矩阵通过，零跳过。全部安装技能摘要保持不变。[版本绑定证据](docs/evidence/codex-effectcraft10-preflight-first-use-20261006.json)。Art 领域包升级、真实 Skills CLI 安装及完整首版仍开放。

工作区分段生产器候选：有界原生帧范围、摘要绑定恢复及逐帧核验；固定插件与 Film／Art 消费仍待完成。[架构](docs/EffectCraft-Segmented-Render-Architecture.zh_CN.md)。

当前源码 HD 分段候选通过 1080p／24 fps／五秒及动态标题核验；固定安装版与 Art HD 仍待完成。[架构与证据](docs/EffectCraft-HD-Sequence-Architecture.zh_CN.md)。

技能源 0.1.0-dev.10 包含有界分段工作流与 HD RGBA 校验优化。原生 CLI 不变；对应固定插件及 Art 安装版验收另行记录。
