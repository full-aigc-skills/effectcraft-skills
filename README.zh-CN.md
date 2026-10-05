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
