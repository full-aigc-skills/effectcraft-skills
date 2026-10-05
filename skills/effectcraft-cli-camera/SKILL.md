---
name: effectcraft-cli-camera
description: 当需要设置已有合成中的摄像机、灯光和材质参数时使用 EffectCraft；本技能自带首次安装与公开 CLI 入口。
license: Apache-2.0
---

# EffectCraft 三维图层与摄像机

本技能负责设置已有合成中的摄像机、灯光和材质参数。与同包技能按名称交接，单独安装即可使用，不读取兄弟目录。调用固定官方 effectcraft-cli，保留原生编辑工程。

## 输入与交付

输入为用户已确认的任务、素材、工程或对象、输出目录与修改范围；需要现有工程时先核对摘要。返回实际 CLI 结果、保存后的原生工程、需要的派生输出与核验记录。安装成功、命令目录存在与创作任务完成分别报告。

## 首次使用与公共入口

定位当前 SKILL.md 的真实目录。当前支持 macOS arm64、Python 3.11+；固定 CLI 安装到用户数据目录。已有任务授权覆盖必要依赖时直接执行本技能安装器，不另造批准流程。

```bash
python3 -I -B /mnt/skills/user/effectcraft-cli-camera/scripts/bootstrap.py
python3 -I -B /mnt/skills/user/effectcraft-cli-camera/scripts/cli.py -- --version
python3 -I -B /mnt/skills/user/effectcraft-cli-camera/scripts/cli.py -- commands --json
```

`/mnt/skills/user/effectcraft-cli-camera` 是挂载示例，替换为实际加载目录；CLI argv 在 `--` 后，原生子命令必须放首位。安装参数放分隔符前；`--runtime-home` 可隔离缓存。锁定制品摘要失败、损坏安装或不支持平台时停止；不改 PATH、不执行浮动升级。原生帮助入口是 `--help`；launcher 自身 `--help` 只说明启动参数。

## 场景操作

核对本场景输入、原生工程、目标对象、版本和输出边界。按 [场景指南](references/scenario.md) 选择当前命令，保存独立检查点后执行；完成后重开原生工程并检查实际输出与非目标内容。

`commands --filter <关键词> --json` 核对参数；属性读写用 props/get/set，命令用 `exec <id> --params <JSON>` 或成对的 `run <id> <JSON> ...`；用 --save-as 保留新工程。

先核对图层三维开关、视角及对应渲染支持；不能用参数存在证明视觉结果。

原生组合与源工程修订使用本技能自带 `scripts/workflow.py`；读取 [工作流合同](references/workflow.md)，模板在本技能 examples 内。只修改授权对象，原生工程和依赖素材保留，派生格式损失读取 [交换报告](references/exchange-loss.md)。

## 核验与恢复

命令非零退出不算完成；需要查看真实保存工程、导出、尺寸及媒体解码。超时结果标 unknown，先检查原任务/工程，不能自动重放编辑。现有原生工作流支持另存修订；对应项目摘要不符时拒绝覆盖。

## 按需参考与交接

- [实际命令证据](references/commands.json)：固定版本观察，仅作为路由与参数参考；实时结果优先，禁用项不执行。
- [工作流合同](references/workflow.md)：组合操作、原生保存、依赖收集与修订。
- 安装/诊断需要时交给 **effectcraft-cli-setup**，完整任务路由交给 **effectcraft-use**；缺少技能时使用 `npx skills add full-aigc-skills/effectcraft-skills --skill <skill-name>`。不通过相邻文件路径加载其他技能。

本技能不提供虚构的登录接口；本地 headless 不要求云账户。完整 GUI、跨编辑器保真与创作质量按实际证据陈述。
