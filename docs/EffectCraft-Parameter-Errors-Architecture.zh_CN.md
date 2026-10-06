# EffectCraft 参数错误架构

## 范围与事实源

OpenSpec EC-DM-004-PARAM 管理本次增量。固定插件 dev.7／技能源 dev.6／原生 CLI 0.2.0 已拒绝未知效果与蒙版参数。真实公开冷启动的 effect.apply blurriness 和 mask.new feather 请求均被原生引擎拒绝且未交付目录；缺口是技能上报通用 RuntimeError command_failed，而非规范要求的 unsupported_mapping。本修复不修改原生引擎，不删除未知字段后继续执行。

```mermaid
sequenceDiagram
 participant S as 单独安装的技能
 participant W as 工作流
 participant E as 固定原生引擎
 S->>W: 新建或源工程修订计划
 W->>E: 完整字段执行效果/蒙版命令
 E-->>W: 与命令匹配的参数校验错误
 W-->>S: unsupported_mapping 与原生诊断
 Note over W: 撤销临时交付，保留源文件
```

## 分类与保全

限定六条计划命令：effect.apply、effect.remove、effect.toggle、mask.new、mask.setVertex、mask.remove。工具必须是 execute_command，原生错误须是单一文本，并以同一命令的固定参数校验前缀开头。其他命令、身份不匹配、渲染／素材故障及非匹配诊断保留 command_failed。cli.py 原始调用继续使用原生 CLI 的明确校验行为；本次领域错误分类针对 workflow.py 计划。

不省略字段、不二次重试。原生命令在应用该编辑前校验参数；计划较早的操作只存在于私有暂存工程。失败新建不发布目录，失败源修订保留原交付的全部文件。既有素材收集失败记录仍独立保留。有效创建仍保存并重开 .ecproj 后生成预览与导出。

## 验证与发布

旧固定技能实际产生两条原生拒绝，但技能错误分类不符。新增真实测试修复前出现两个子用例错误，新增两个单元用例也失败；修复后目标单元七项通过，独立复制效果／蒙版技能、公开空运行时的有效创建及非法新建／修订验收在 20.018 秒通过。[绑定证据](evidence/parameter-mapping-repair-20261006.json)。

十三项技能从独立技能源同步该助手。本源码阶段尚待完整回归、不可变技能源／插件发布及安装后复验。不据此宣布所有效果、羽化动画、模型、GUI 或创作质量完成；ArtCraft 的锁定包需要其自身的后续更新。
