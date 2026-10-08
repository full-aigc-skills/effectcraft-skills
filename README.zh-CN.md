# EffectCraft 独立技能

从文字、图形和素材创建可编辑 `.ecproj` 工程、依赖和媒体。当前为开发版，完整 V1 未完成；已发布版本与本地文档候选分别记录。

当前技能源：`0.1.0-dev.55`；消费插件：`0.1.0-dev.57`；15 个独立技能。

| Field | Value |
| --- | --- |
| Metadata version | 0.1.0-dev.55 |
| Skills source | effectcraft-skills / v0.1.0-dev.55 |
| Acceptance | Development; full V1 OPEN |


## 首次使用

在宿主中请求 **`effectcraft-use`**。直接调用时，将 `SKILL_DIR` 设为宿主实际加载的 `SKILL.md` 所在绝对目录。启动入口在用户数据目录准备并校验固定 Python 和 EffectCraft，不修改系统 Python、全局 PATH 或只读技能目录。离线运行须预备锁定官方制品或已有完整缓存。

<!-- CRAFT_FIRST_USE_START -->
```bash
: "${SKILL_DIR:?Set to the actual loaded skill directory}"
sh "$SKILL_DIR/scripts/launch.sh" doctor
sh "$SKILL_DIR/scripts/launch.sh" run --plan "$SKILL_DIR/examples/brand-intro.json" --output "$PWD/effectcraft-result"
```
<!-- CRAFT_FIRST_USE_END -->

```powershell
$env:SKILL_DIR = "<actual loaded skill directory>"
& (Join-Path $env:SKILL_DIR "scripts/launch.ps1") doctor
```

[工作流和交付说明](skills/effectcraft-use/references/workflow.md) · [安装与环境诊断](skills/effectcraft-cli-setup/SKILL.md)。通用 Skills CLI 安装、固定宿主自然语言自动派发仍须独立验收。


## 当前能力与证据

维护者生成的[当前矩阵](docs/current-capabilities.json)绑定完整技能载荷、Python／原生制品和原始报告摘要。已发布 source53 的 macOS arm64 技术样例通过。dev.54回执身份修复改变执行载荷，旧报告不再证明当前载荷，生成矩阵保持 NOT_RUN，直至绑定本次证据；其他架构、Web 浏览器、FreeBSD、创作评价和完整宿主验收未通过的格子继续保持 NOT_RUN。CI 的平台合同测试不替代目标平台创作。

source53／plugin55 的[15 技能报告](docs/evidence/native-smoke-source53-20261009.json)通过工程重开和每例 12 帧完整解码，全部使用已验证缓存（0 次冷安装），不是 15 个领域场景或模型派发验收。[取消恢复与父子屏障](docs/evidence/cancel-family-candidate-20261009.json)保留未知编辑，完整崩溃／GUI矩阵仍开放。


## 技能入口

| Skill | 用途 |
| --- | --- |
| [effectcraft-use](skills/effectcraft-use/SKILL.md) | 完整任务路由 |
| [effectcraft-cli](skills/effectcraft-cli/SKILL.md) | CLI 公共操作 |
| [effectcraft-cli-setup](skills/effectcraft-cli-setup/SKILL.md) | CLI 安装诊断 |
| [effectcraft-cli-project](skills/effectcraft-cli-project/SKILL.md) | 工程与素材管理 |
| [effectcraft-cli-footage](skills/effectcraft-cli-footage/SKILL.md) | 素材与预合成输入 |
| [effectcraft-cli-composition](skills/effectcraft-cli-composition/SKILL.md) | 合成与时间范围 |
| [effectcraft-cli-layers](skills/effectcraft-cli-layers/SKILL.md) | 文字形状与图层 |
| [effectcraft-cli-animation](skills/effectcraft-cli-animation/SKILL.md) | 属性与关键帧动画 |
| [effectcraft-cli-effects](skills/effectcraft-cli-effects/SKILL.md) | 视觉效果 |
| [effectcraft-cli-masks](skills/effectcraft-cli-masks/SKILL.md) | 蒙版与路径动画 |
| [effectcraft-cli-expressions](skills/effectcraft-cli-expressions/SKILL.md) | 属性表达式 |
| [effectcraft-cli-camera](skills/effectcraft-cli-camera/SKILL.md) | 三维图层与摄像机 |
| [effectcraft-cli-export](skills/effectcraft-cli-export/SKILL.md) | 渲染与透明输出 |
| [effectcraft-cli-tracking](skills/effectcraft-cli-tracking/SKILL.md) | 镜头跟踪 |
| [effectcraft-cli-puppet](skills/effectcraft-cli-puppet/SKILL.md) | 木偶与局部变形动画 |

各技能包含自己的运行资源，可独立安装，不依赖兄弟目录。655 条命令的参数、归属和模式见技能自带命令说明；目录覆盖不等于每条命令已执行验收。


## 检查、恢复与取消

使用 `inspect` 查看原任务，`reconcile` 核对原回执，`resume` 仅继续已证明可恢复的工作。`cancel` 先持久化停止意图；父任务等待后代停止，未知编辑保持 reconciling。不得换任务 ID／输出目录重做未知编辑。任务继续使用绑定的原运行时，损坏或缺失证据保留现场并拒绝续写。

[Managed execution](skills/effectcraft-use/references/managed-execution.md)


## 维护与版本历史

技能源维护执行代码，插件消费固定标签、提交及完整技能摘要。唯一增量规格为插件的 `openspec/changes/establish-v1-plugin`；未完成门禁不归档。公共 `craft-task/v1` 和 `craft-artifact/v1` 的所有者保持 ArtCraft，本仓仅消费。

[版本记录及整理前 README](RELEASE-HISTORY.zh-CN.md) · [Plugin specifications](https://github.com/full-aigc-plugins/effectcraft-plugin/tree/main/openspec/changes/establish-v1-plugin)

dev.54 的[统一管理接口验收](docs/evidence/managed-public-interface-candidate-20261009.json)完成9.3.5：严格回执身份／孤立材料保护及九个管理角色，含真实原生恢复与Codex实际观察后的局部修订。source54／plugin56分发本增量，source53／plugin55保留为历史版本；其他原生平台和固定宿主派发继续开放；后续本机三模式组合验收见下。[source52报告](docs/evidence/native-smoke-source52-20261009.json)保留为历史证据。

本机[三模式公开组合验收](docs/evidence/managed-three-mode-composition-20261009.json)完成9.3.6，使用未改变的已发布source54／plugin56载荷：workflow、命令计划和真实自有桌面会话贯通安装器、真实适配器、账本、回执和恢复，原计划换ID／目录重做被拒绝，旧CLI兼容。默认586项回归545通过、41条件跳过，另行启用的3个原生条件案例全部通过。本次新增测试与证据尚未发布；完整崩溃／GUI矩阵、其他原生目标、固定宿主派发及完整V1仍开放。


dev.55 技能源／dev.57 插件分发 [默认受管理派发验收](docs/evidence/managed-default-routing-20261009.json)：15个技能明确 workflow／commands／desktop 写入入口，45组只读预检与18组历史状态操作通过。源码589项回归548通过／41条件跳过。9.3.1与9.3.6已完成，70项仍开放；原生证据仅复用105份未变执行资源，三份指引已更新，未声明新宿主模型派发或完整平台通过。原始候选报告保留验证时点，发行绑定另见版本记录。
